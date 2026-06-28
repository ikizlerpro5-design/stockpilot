"""
StockPilot — Telegram Derinlik Verisi Modülü
@ucretsizderinlikbot API'si ile BIST emir defteri verisi çeker.
Fotoğraf yanıtları OCR (Tesseract) ile metne çevrilir.
"""

import os
import re
import io
import asyncio
import threading
import time
import tempfile
from datetime import datetime

from telethon import TelegramClient

# OCR
try:
    import pytesseract
    from PIL import Image
    HAS_OCR = True
except ImportError:
    HAS_OCR = False

# Windows'ta Tesseract yolu (Linux'ta otomatik PATH'ta)
if os.name == 'nt' and HAS_OCR:
    _tesseract_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    if os.path.exists(_tesseract_path):
        pytesseract.pytesseract.tesseract_cmd = _tesseract_path


# Telegram API bilgileri (ortam degiskenlerinden)
API_ID = int(os.environ.get('TG_API_ID', '0'))
API_HASH = os.environ.get('TG_API_HASH', '')
SESSION_NAME = os.environ.get('TG_SESSION', 'stockpilot_session')

# Derinlik botu
DEPTH_BOT = os.environ.get('TG_DEPTH_BOT', '@ucretsizderinlikbot')

# Varsayilan takip edilecek semboller
DEFAULT_SYMBOLS = os.environ.get('DEPTH_SYMBOLS', 'THYAO,GARAN,ASELS,SISE,EREGL,KCHOL,TUPRS,BIMAS,AKBNK,PGSUS').split(',')

# Son alınan derinlik verisi (thread-safe cache)
_depth_cache = {}
_cache_lock = threading.Lock()

# Fotoğraf cache'i (base64) - her sembol için son fotoğraf
_photo_cache = {}
_photo_lock = threading.Lock()

# Derinlik geçmişi (her sembol için son 50 snapshot)
_depth_history: dict[str, list] = {}
_history_lock = threading.Lock()
_MAX_HISTORY = 50

# Öncelikli sembol (kullanıcının baktığı hisse)
_priority_symbol = None
_priority_lock = threading.Lock()

# Client referansı (thread'ler arası paylaşım için)
_client = None
_client_lock = threading.Lock()


def _get_yf_price(symbol: str) -> float | None:
    """Yahoo Finance'den hisse fiyatini al (referans icin)."""
    try:
        import yfinance as yf
        t = yf.Ticker(symbol + '.IS')
        info = t.fast_info
        price = info.get('lastPrice') or info.get('regularMarketPrice') or info.get('previousClose')
        if price and price > 0:
            return float(price)
    except Exception:
        pass
    return None


def _parse_turkish_number(raw: str) -> float:
    """
    Türkçe sayı formatını parse et.
    OCR çıktısında: 330.50 = 330.50 (fiyat), 69.720 = 69720 (adet)
    Kural: . veya , sonrası 3 basamak ise binlik ayraç, 2 basamak ise ondalık.
    """
    raw = raw.strip()
    # Virgülü noktaya çevir (Türkçe ondalık)
    # Önce hangi ayracın ondalık olduğunu bul
    if ',' in raw and '.' not in raw:
        return float(raw.replace(',', '.'))
    if '.' in raw and ',' not in raw:
        # 3 basamak kontrolü
        parts = raw.split('.')
        if len(parts) == 2 and len(parts[1]) == 3:
            # Binlik ayraç: 69.720 -> 69720
            return float(raw.replace('.', ''))
        elif len(parts) >= 3:
            # Birden fazla nokta: 11.603.168.244 -> 11603168244
            return float(raw.replace('.', ''))
        else:
            # 2 basamak ondalık: 330.50 -> 330.50
            return float(raw)
    if ',' in raw and '.' in raw:
        # Hangisi önce?
        if raw.index(',') < raw.index('.'):
            # Virgül ondalık: 330,50
            return float(raw.replace('.', '').replace(',', '.'))
        else:
            # Nokta ondalık: 330.50
            return float(raw.replace(',', ''))
    return float(raw)


def parse_depth_ocr_text(text: str, symbol: str, ref_price_hint=None) -> dict:
    """OCR metninden derinlik verisini parse et — akilli fiyat tespiti (kumeleme)."""
    result = {
        'symbol': symbol,
        'alis': [],
        'satis': [],
        'price': None,
        'timestamp': datetime.now().isoformat()
    }
    if not text:
        return result
    
    lines = [l.strip() for l in text.strip().split('\n') if l.strip()]
    
    # Sembol tespiti
    for line in lines[:3]:
        sym_match = re.search(r'([A-Z]{4,5})', line.upper())
        if sym_match and sym_match.group(1) not in ('AKD', 'TME', 'ICIN', 'BOTU', 'TAKAS', 'HISSE', 'KADEM', 'KANAL', 'DEGIL'):
            result['symbol'] = sym_match.group(1)
            break
    
    # === Tum anlamli sayilari topla ===
    all_numbers = []
    for line in lines:
        upper = line.upper().strip()
        if any(kw in upper for kw in ['KADEME', 'DERINLIK', 'DERİNLİK', 'TME/',
                'ICIN T', 'ANALIZ', 'UCRETSIZ', 'BOTU', 'TAKAS', 'EGSIZ',
                'HISSE', 'KANAL', 'KATIL', 'DEGIL', 'ADET', 'LOT', 'MIKTAR', 'HACIM']):
            continue
        for m in re.findall(r'(\d+[.,]\d+)', line):
            try:
                v = _parse_turkish_number(m)
                if 0.01 < v < 100000:
                    all_numbers.append(v)
            except:
                pass
    
    if not all_numbers:
        return result
    
    sorted_nums = sorted(set(all_numbers))
    
    # === Akilli fiyat tespiti: Kumeleme ile alis/satis ayrim noktasi ===
    
    # Yontem 1: Ilk satirdan fiyat adayi (genelde "SEMBOL FIYAT" formatinda)
    first_line = lines[0] if lines else ''
    first_line_candidates = []
    for m in re.findall(r'(\d{1,6}[.,]\d{2})', first_line):
        try:
            first_line_candidates.append(_parse_turkish_number(m))
        except:
            pass
    
    # Yontem 2: En buyuk oransal boslugu bul (alis/satis kumelerini dogal ayirir)
    best_gap_val = None
    max_gap_pct = 0
    for i in range(len(sorted_nums) - 1):
        gap = sorted_nums[i+1] - sorted_nums[i]
        gap_pct = gap / sorted_nums[i] if sorted_nums[i] > 0 else 0
        if gap_pct > max_gap_pct and 0.002 < gap_pct < 0.5:
            max_gap_pct = gap_pct
            best_gap_val = round((sorted_nums[i] + sorted_nums[i+1]) / 2, 2)
    
    # Yontem 3: yfinance hint
    hint = ref_price_hint if ref_price_hint and ref_price_hint > 0 else None
    
    # === En iyi fiyati sec ===
    best_price = None
    
    # STRATEJI 1: yfinance hint varsa ve makul veri siniflandirabiliyorsa DIREKT kullan
    if hint and hint > 0:
        alis_h = sum(1 for v in sorted_nums if v < hint * 0.995)
        satis_h = sum(1 for v in sorted_nums if v > hint * 1.005)
        if alis_h + satis_h >= 3:
            best_price = hint
    
    # STRATEJI 2: Hint yetersizse, adaylar arasindan en dengeli boleni sec
    if best_price is None:
        candidates = []
        for c in first_line_candidates:
            candidates.append(('ocr_first', c))
        if best_gap_val:
            candidates.append(('gap', best_gap_val))
        
        best_score = -1
        for src, candidate in candidates:
            if candidate <= 0:
                continue
            alis_cnt = sum(1 for v in sorted_nums if v < candidate * 0.995)
            satis_cnt = sum(1 for v in sorted_nums if v > candidate * 1.005)
            total = alis_cnt + satis_cnt
            
            if total == 0:
                continue
            
            ratio = min(alis_cnt, satis_cnt) / max(alis_cnt, satis_cnt) if max(alis_cnt, satis_cnt) > 0 else 0
            score = ratio * total
            if score > best_score:
                best_score = score
                best_price = candidate
        
        # Hicbiri ise yaramadiysa hint veya gap veya ortanca
        if best_price is None:
            best_price = hint or best_gap_val or sorted_nums[len(sorted_nums)//2]
    
    result['price'] = round(best_price, 2)
    ref_price = best_price
    
    print(f"  [OCR-Parse] {symbol}: fiyat={ref_price:.2f}, toplam_sayi={len(sorted_nums)}, "
          f"ilk_satir={first_line_candidates[:2]}, gap={best_gap_val}, hint={hint}")
    
    # === Siniflandir ===
    alis_raw = []
    satis_raw = []
    
    for v in sorted_nums:
        if v < ref_price * 0.995:
            alis_raw.append(v)
        elif v > ref_price * 1.005:
            satis_raw.append(v)
    
    for p in alis_raw:
        result['alis'].append((p, 0))
    for p in satis_raw:
        result['satis'].append((p, 0))
    
    result['alis'].sort(key=lambda x: x[0], reverse=True)
    result['satis'].sort(key=lambda x: x[0])
    
    print(f"  [OCR-Parse] {symbol}: alis={len(result['alis'])}, satis={len(result['satis'])}")
    return result


async def _get_client() -> TelegramClient:
    """Telegram client'ı singleton olarak döndür."""
    global _client
    
    with _client_lock:
        if _client is not None and _client.is_connected():
            return _client
    
    session_path = SESSION_NAME
    if not os.path.isabs(session_path):
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        session_path = os.path.join(base, SESSION_NAME)
    
    client = TelegramClient(session_path, API_ID, API_HASH)
    await client.connect()
    
    if not await client.is_user_authorized():
        print(f"[Telegram] Session gecersiz: {session_path}.session")
        await client.disconnect()
        raise RuntimeError("Telegram session gecersiz")
    
    with _client_lock:
        _client = client
    
    return client


async def fetch_depth_for_symbol(symbol: str) -> dict:
    """
    Bir sembol icin @ucretsizderinlikbot'tan derinlik verisi cek.
    image_to_data ile sutunlu OCR yapip parse eder.
    """
    global _depth_cache
    
    symbol = symbol.upper().replace('.IS', '')
    
    try:
        client = await _get_client()
        bot = await client.get_entity(DEPTH_BOT)
        
        await client.send_message(bot, f'/derinlik {symbol}')
        await asyncio.sleep(4)
        
        messages = await client.get_messages(bot, limit=2)
        
        for msg in messages:
            if msg.photo:
                img_data = await client.download_media(msg, file=bytes)
                
                # === Fotoğrafı cache'le (base64 olarak) ===
                if img_data:
                    import base64
                    try:
                        b64 = base64.b64encode(img_data).decode('utf-8')
                        with _photo_lock:
                            _photo_cache[symbol] = b64
                    except Exception:
                        pass
                
                if HAS_OCR and img_data:
                    image = Image.open(io.BytesIO(img_data))
                    
                    # === YONTEM 1: Row-based OCR ile tablo rekonstrüksiyonu ===
                    data = pytesseract.image_to_data(image, lang='eng', output_type=pytesseract.Output.DICT)
                    
                    # Token'lari satir (y) ve sutun (x) bazinda topla
                    rows = {}  # {y_key: [(x, text, conf), ...]}
                    
                    for i, text in enumerate(data['text']):
                        txt = text.strip()
                        if not txt or data['conf'][i] < 20:
                            continue
                        x = data['left'][i]
                        y = data['top'][i]
                        conf = data['conf'][i]
                        y_key = (y // 15) * 15  # 15px satir toleransi
                        if y_key not in rows:
                            rows[y_key] = []
                        rows[y_key].append((x, txt, conf))
                    
                    # Satirlari y koordinatina gore sirala
                    sorted_rows = sorted(rows.keys())
                    
                    # Her satirdaki token'lari x'e gore sirala ve birlestir
                    row_texts = []
                    row_data = []  # Her satir icin (sol_tokenlar, sag_tokenlar)
                    
                    for y_key in sorted_rows:
                        tokens = sorted(rows[y_key], key=lambda t: t[0])
                        line_text = ' '.join(t for _, t, _ in tokens)
                        
                        # Sayilari ayikla (noktali + noktasiz tam sayilar)
                        nums_in_row = []
                        for _, txt, conf in tokens:
                            # Once noktali/virgullu sayilar
                            for m in re.findall(r'(\d+[.,]\d+)', txt):
                                try:
                                    v = _parse_turkish_number(m)
                                    nums_in_row.append((v, conf))
                                except:
                                    pass
                            # Sonra 3+ basamakli tam sayilar (lot olabilir)
                            for m in re.findall(r'\b(\d{3,7})\b', txt):
                                try:
                                    v = int(m)
                                    if v > 1 and v not in [nv for nv, _ in nums_in_row]:
                                        nums_in_row.append((float(v), conf))
                                except:
                                    pass
                        
                        row_texts.append(line_text)
                        if nums_in_row:
                            row_data.append({'y': y_key, 'numbers': nums_in_row, 'text': line_text})
                    
                    # Satir bazli metin (parse_depth_ocr_text icin)
                    ocr_text = '\n'.join(row_texts)
                    
                    # === YONTEM 2: image_to_string (yedek) ===
                    ocr_text2 = pytesseract.image_to_string(image, lang='eng')
                    
                    # yfinance'den gercek fiyati referans olarak al
                    yf_price = _get_yf_price(symbol)
                    
                    # Temel parse (fiyat seviyeleri)
                    parsed1 = parse_depth_ocr_text(ocr_text, symbol, yf_price)
                    parsed2 = parse_depth_ocr_text(ocr_text2, symbol, yf_price)
                    
                    total1 = len(parsed1.get('alis', [])) + len(parsed1.get('satis', []))
                    total2 = len(parsed2.get('alis', [])) + len(parsed2.get('satis', []))
                    
                    parsed = parsed1 if total1 >= total2 else parsed2
                    ref_price = parsed.get('price') or yf_price or 100
                    
                    # === Lot sayilarini row_data'dan cikar ===
                    lot_map = {}  # {price: lot_count}
                    for row in row_data:
                        nums = row['numbers']
                        if len(nums) >= 2:
                            # En az 2 sayi varsa: biri fiyat, digeri lot olabilir
                            for i, (v1, _) in enumerate(nums):
                                for j, (v2, _) in enumerate(nums):
                                    if i >= j:
                                        continue
                                    # Biri fiyata yakin, digeri daha buyukse (lot)
                                    d1 = abs(v1 - ref_price) / ref_price if ref_price else 999
                                    d2 = abs(v2 - ref_price) / ref_price if ref_price else 999
                                    if d1 < 0.15 and v2 > ref_price * 1.5 and v2 < ref_price * 100:
                                        lot_map.setdefault(round(v1, 2), 0)
                                        lot_map[round(v1, 2)] = max(lot_map[round(v1, 2)], int(v2))
                                    elif d2 < 0.15 and v1 > ref_price * 1.5 and v1 < ref_price * 100:
                                        lot_map.setdefault(round(v2, 2), 0)
                                        lot_map[round(v2, 2)] = max(lot_map[round(v2, 2)], int(v1))
                    
                    # Lot sayilarini parse sonucuna ekle
                    if lot_map:
                        new_alis = []
                        for p, lot in parsed.get('alis', []):
                            key = round(p, 2)
                            new_lot = lot_map.get(key, lot)
                            new_alis.append((p, new_lot))
                        new_satis = []
                        for p, lot in parsed.get('satis', []):
                            key = round(p, 2)
                            new_lot = lot_map.get(key, lot)
                            new_satis.append((p, new_lot))
                        parsed['alis'] = new_alis
                        parsed['satis'] = new_satis
                        print(f"  [OCR-Lot] {symbol}: {len(lot_map)} fiyat seviyesine lot eklendi")
                    
                    # En azindan alis VEYA satis varsa kabul et
                    if parsed['alis'] or parsed['satis']:
                        with _cache_lock:
                            _depth_cache[symbol] = parsed
                        
                        # === Derinlik gecmisine ekle ===
                        snapshot = {
                            'ts': datetime.now().isoformat(),
                            'price': parsed.get('price', 0),
                            'alis_count': len(parsed.get('alis', [])),
                            'satis_count': len(parsed.get('satis', [])),
                            'alis_lot': sum(r[1] for r in parsed.get('alis', []) if len(r) > 1 and r[1] > 0),
                            'satis_lot': sum(r[1] for r in parsed.get('satis', []) if len(r) > 1 and r[1] > 0),
                            'best_alis': parsed['alis'][0][0] if parsed.get('alis') else 0,
                            'best_satis': parsed['satis'][0][0] if parsed.get('satis') else 0,
                            'alis_top5': [(r[0], r[1] if len(r) > 1 else 0) for r in parsed.get('alis', [])[:5]],
                            'satis_top5': [(r[0], r[1] if len(r) > 1 else 0) for r in parsed.get('satis', [])[:5]],
                        }
                        with _history_lock:
                            if symbol not in _depth_history:
                                _depth_history[symbol] = []
                            _depth_history[symbol].append(snapshot)
                            if len(_depth_history[symbol]) > _MAX_HISTORY:
                                _depth_history[symbol] = _depth_history[symbol][-_MAX_HISTORY:]
                        
                        # Lot toplamlarini hesapla
                        total_alis_lot = sum(r[1] for r in parsed['alis'] if r[1] > 0)
                        total_satis_lot = sum(r[1] for r in parsed['satis'] if r[1] > 0)
                        print(f"[Telegram] {symbol} derinlik OCR ile cekildi "
                              f"(Alis: {len(parsed['alis'])}/{total_alis_lot}lot, "
                              f"Satis: {len(parsed['satis'])}/{total_satis_lot}lot)")
                        return parsed
                    else:
                        print(f"[Telegram] {symbol} OCR parse edilemedi.")
                        print(f"  data-ocr (ilk 300): {ocr_text[:300]}")
                        print(f"  string-ocr (ilk 300): {ocr_text2[:300]}")
                
                print(f"[Telegram] {symbol} fotografi alindi ama OCR yapilamadi.")
                break
            
            if msg.text:
                txt = msg.text.upper()
                if 'BEKLEMENIZ' in txt or 'BEKLEMENİZ' in txt:
                    print(f"[Telegram] Rate limit: {msg.text[:100]}")
                elif 'BULUNAMADI' in txt:
                    print(f"[Telegram] {symbol} bulunamadi: {msg.text[:100]}")
        
        return {}
        
    except Exception as e:
        print(f"[Telegram] {symbol} fetch hatasi: {e}")
        return {}


def _resolve_session_path():
    """Session dosyasının tam yolunu bul."""
    if os.path.isabs(SESSION_NAME):
        return SESSION_NAME
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, SESSION_NAME)


def start_telegram_listener():
    """Telegram bağlantısını başlat ve test fetch'i yap."""
    if not API_ID or not API_HASH:
        print("[Telegram] API bilgileri eksik.")
        return None
    
    session_file = f"{_resolve_session_path()}.session"
    if not os.path.exists(session_file):
        print(f"[Telegram] Session bulunamadi: {session_file}")
        print("[Telegram] Once 'python setup_telegram.py' calistirin.")
        return None
    
    print(f"[Telegram] Session bulundu, baglaniliyor...")
    
    def run_async():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            # Bağlantıyı test et
            client = loop.run_until_complete(_get_client())
            me = loop.run_until_complete(client.get_me())
            print(f"[Telegram] Baglandi! Kullanici: {me.first_name}")
            print(f"[Telegram] Derinlik botu: {DEPTH_BOT}")
            
            if HAS_OCR:
                print("[Telegram] OCR aktif (Tesseract).")
            else:
                print("[Telegram] OCR PASIF! pip install pytesseract Pillow")
            
            # Test: bir sembol çek
            print(f"[Telegram] Test fetch: THYAO...")
            loop.run_until_complete(fetch_depth_for_symbol('THYAO'))
            
            # Periyodik fetch döngüsü
            _periodic_fetch_loop(loop)
            
        except Exception as e:
            print(f"[Telegram] Dinleyici hatasi: {e}")
    
    thread = threading.Thread(target=run_async, daemon=True)
    thread.start()
    return thread


def _periodic_fetch_loop(loop):
    """Öncelikli + periyodik derinlik çekme döngüsü."""
    symbols = DEFAULT_SYMBOLS[:]
    idx = 0
    last_priority_fetch = 0
    
    while True:
        try:
            # Öncelikli sembol var mı?
            with _priority_lock:
                prio = _priority_symbol
            
            now = time.time()
            
            if prio and (now - last_priority_fetch >= 3):
                # Öncelikli sembolü 3 saniyede bir çek
                print(f"[Telegram] ⚡ Öncelikli fetch: {prio}")
                loop.run_until_complete(fetch_depth_for_symbol(prio))
                last_priority_fetch = now
                time.sleep(3)
            else:
                # Normal döngü
                symbol = symbols[idx % len(symbols)]
                if symbol != prio:  # öncelikli sembolse atla, zaten çekiliyor
                    loop.run_until_complete(fetch_depth_for_symbol(symbol))
                idx += 1
                time.sleep(3)  # rate limit sınırında
                
        except Exception as e:
            print(f"[Telegram] Periyodik fetch hatasi: {e}")
            time.sleep(5)


def set_priority_symbol(symbol: str | None):
    """Kullanıcının baktığı hisseyi öncelikli olarak işaretle."""
    global _priority_symbol
    with _priority_lock:
        _priority_symbol = symbol.upper().replace('.IS', '') if symbol else None
        if _priority_symbol:
            print(f"[Telegram] 🎯 Öncelikli sembol: {_priority_symbol}")
        else:
            print(f"[Telegram] Öncelik kaldırıldı.")


def get_depth_data(symbol: str) -> dict:
    """Son derinlik verisini döndür (cache'den)."""
    symbol = symbol.upper().replace('.IS', '')
    with _cache_lock:
        return _depth_cache.get(symbol, {})


def get_depth_photo(symbol: str) -> str | None:
    """Son derinlik fotoğrafını base64 olarak döndür."""
    symbol = symbol.upper().replace('.IS', '')
    with _photo_lock:
        return _photo_cache.get(symbol)


def get_depth_history(symbol: str, count: int = 20) -> list:
    """Derinlik geçmişini döndür (son N snapshot)."""
    symbol = symbol.upper().replace('.IS', '')
    with _history_lock:
        history = _depth_history.get(symbol, [])
        return history[-count:] if count > 0 else history


def get_all_depth_symbols() -> list:
    """Takip edilen tüm sembolleri döndür."""
    with _cache_lock:
        return list(_depth_cache.keys())


def analyze_depth(symbol: str) -> dict:
    """
    Derinlik verisini analiz et: destek/direnc seviyeleri, duvar tespiti,
    dusecegi/cikacagi yerler, spread analizi.
    """
    data = get_depth_data(symbol)
    if not data or (not data.get('alis') and not data.get('satis')):
        return {'verdict': 'notr', 'score': 50, 'comment': 'Henuz yeterli derinlik verisi yok.'}
    
    alis = data.get('alis', [])
    satis = data.get('satis', [])
    price = data.get('price') or 0
    
    total_alis_lot = sum(row[1] for row in alis if len(row) > 1 and row[1] > 100)
    total_satis_lot = sum(row[1] for row in satis if len(row) > 1 and row[1] > 100)
    near_alis = sum(row[1] for row in alis[:5] if len(row) > 1)
    near_satis = sum(row[1] for row in satis[:5] if len(row) > 1)
    
    alis_walls = [(row[0], row[1]) for row in alis if len(row) > 1 and row[1] >= 500000]
    satis_walls = [(row[0], row[1]) for row in satis if len(row) > 1 and row[1] >= 500000]
    
    best_alis = alis[0][0] if alis else 0
    best_satis = satis[0][0] if satis else 0
    spread = best_satis - best_alis if best_alis and best_satis else 0
    spread_pct = (spread / price * 100) if price else 0
    
    # === Derinlikten Destek/Direnc Cikarma ===
    # Alis duvarlari = potansiyel destek (fiyat buraya dusebilir)
    # Satis duvarlari = potansiyel direnc (fiyat buraya cikabilir)
    
    # Destek: en guclu alis seviyeleri (fiyat < current price)
    support_levels = []
    for p, qty in alis:
        if p < price and qty > 0:
            strength = min(100, int((qty / 100000) * 10))  # normalize
            support_levels.append({
                'price': round(p, 2),
                'lot': qty,
                'strength': strength,
                'distance_pct': round((price - p) / price * 100, 2)
            })
    support_levels.sort(key=lambda x: x['lot'], reverse=True)
    top_supports = support_levels[:3]
    
    # Direnc: en guclu satis seviyeleri (fiyat > current price)
    resistance_levels = []
    for p, qty in satis:
        if p > price and qty > 0:
            strength = min(100, int((qty / 100000) * 10))
            resistance_levels.append({
                'price': round(p, 2),
                'lot': qty,
                'strength': strength,
                'distance_pct': round((p - price) / price * 100, 2)
            })
    resistance_levels.sort(key=lambda x: x['lot'], reverse=True)
    top_resistances = resistance_levels[:3]
    
    # En guclu tek destek ve direnc
    strongest_support = top_supports[0] if top_supports else None
    strongest_resistance = top_resistances[0] if top_resistances else None
    
    # === Yorum ===
    total = total_alis_lot + total_satis_lot
    if total > 0:
        alis_ratio = total_alis_lot / total
        score = int(alis_ratio * 100)
    else:
        alis_ratio = 0.5
        score = 50
    
    comments = []
    
    # Denge
    if alis_ratio > 0.65:
        comments.append(f"Alis tarafi baskin (%{int(alis_ratio*100)}). Alicili seyir.")
        verdict = 'al'
    elif alis_ratio < 0.35:
        comments.append(f"Satis tarafi baskin (%{int((1-alis_ratio)*100)}). Saticili seyir.")
        verdict = 'sat'
    else:
        comments.append(f"Alis-Satis dengeli (%{int(alis_ratio*100)}/%{int(100-alis_ratio*100)}).")
        verdict = 'tut'
    
    # Dusecegi/Cikacagi yerler
    if strongest_support:
        comments.append(
            f"Kademeye gore en guclu destek {strongest_support['price']:.2f} "
            f"(%{strongest_support['distance_pct']:.1f} asagida, {strongest_support['lot']/1000:.0f}K lot)."
        )
    if strongest_resistance:
        comments.append(
            f"En guclu direnc {strongest_resistance['price']:.2f} "
            f"(%{strongest_resistance['distance_pct']:.1f} yukarida, {strongest_resistance['lot']/1000:.0f}K lot)."
        )
    
    # Duvarlar
    for wall_price, wall_lot in alis_walls[:2]:
        comments.append(f"{wall_price:.2f}'de {wall_lot/1000:.0f}K alis duvari var - guclu destek.")
    for wall_price, wall_lot in satis_walls[:2]:
        comments.append(f"{wall_price:.2f}'de {wall_lot/1000:.0f}K satis duvari var - guclu direnc.")
    
    if spread_pct > 0.5:
        comments.append(f"Spread genis: %{spread_pct:.2f} - likidite dusuk.")
    elif spread > 0 and spread_pct < 0.1:
        comments.append(f"Spread dar: %{spread_pct:.2f} - likit hisse.")
    
    # === Trading Sinyalleri: Giris / Stop / Hedef ===
    # Giriş: en iyi satış fiyatı (piyasa alışı) veya fiyatın kendisi
    entry_price = best_satis if best_satis > 0 else price
    
    # Hedef: en güçlü direnç (veya en iyi satış + spread * 5)
    if strongest_resistance:
        target_price = strongest_resistance['price']
    elif len(satis) >= 3:
        target_price = satis[2][0]  # 3. kademe satış
    else:
        target_price = price * 1.01  # %1 yukarı
    
    # Stop: en güçlü desteğin bir altı (veya girişin %2 altı)
    if strongest_support:
        # Desteğin hemen altı
        stop_price = round(strongest_support['price'] - spread, 2)
        if stop_price <= 0 or stop_price >= entry_price:
            stop_price = round(strongest_support['price'] * 0.995, 2)  # %0.5 altı
    elif len(alis) >= 3:
        stop_price = alis[2][0]  # 3. kademe alış
    else:
        stop_price = round(price * 0.98, 2)  # %2 aşağı
    
    # Risk/Ödül hesabı
    risk = entry_price - stop_price
    reward = target_price - entry_price
    rr_ratio = round(reward / risk, 2) if risk > 0 else 0
    
    # Lot önerisi (basit: toplam lot / 10, maks 1000)
    suggested_lot = min(1000, max(10, int(near_satis / 10))) if near_satis > 0 else 100
    
    signal = {
        'entry': round(entry_price, 2),
        'stop': stop_price,
        'target': round(target_price, 2),
        'risk_tl': round(risk, 2),
        'reward_tl': round(reward, 2),
        'rr_ratio': rr_ratio,
        'suggested_lot': suggested_lot,
    }
    
    # Sinyal yorumu
    if rr_ratio >= 2:
        comments.append(f"Sinyal: Giris {entry_price:.2f}, Stop {stop_price:.2f}, Hedef {target_price:.2f} (R/R: {rr_ratio})")
    elif rr_ratio >= 1:
        comments.append(f"Sinyal: Giris {entry_price:.2f}, Stop {stop_price:.2f}, Hedef {target_price:.2f} (R/R: {rr_ratio} - sinirda)")
    else:
        comments.append(f"Sinyal: Giris {entry_price:.2f}, Stop {stop_price:.2f}, Hedef {target_price:.2f} (R/R: {rr_ratio} - riskli)")
    
    return {
        'verdict': verdict,
        'score': score,
        'comment': ' '.join(comments),
        'signal': signal,
        'details': {
            'total_alis_lot': total_alis_lot,
            'total_satis_lot': total_satis_lot,
            'near_alis_lot': near_alis,
            'near_satis_lot': near_satis,
            'alis_walls': alis_walls[:3],
            'satis_walls': satis_walls[:3],
            'spread': round(spread, 2),
            'spread_pct': round(spread_pct, 3),
            'best_alis': best_alis,
            'best_satis': best_satis,
            'alis_ratio': round(alis_ratio, 3),
            'depth_support': support_levels[:5],
            'depth_resistance': resistance_levels[:5],
            'strongest_support': strongest_support,
            'strongest_resistance': strongest_resistance,
        }
    }


def trigger_fetch(symbol: str):
    """Manuel fetch tetikle ve oncelikli yap (API'den cagrilir)."""
    symbol = symbol.upper().replace('.IS', '')
    set_priority_symbol(symbol)
    # Yeni event loop acma - zaten periyodik dongu var, 3sn icinde cekecek
    return True
