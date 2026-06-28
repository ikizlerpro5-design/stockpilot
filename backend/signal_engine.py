"""
StockPilot — Signal Engine
Derinlik verisinden anlik al/sat sinyalleri uretir.
Surekli calisir, watchlist'teki hisseleri izler.
"""

import threading
import time
import json
import os
from datetime import datetime
from typing import Dict, List, Optional

# Telegram depth modulunden veri cek
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from telegram_depth import get_depth_data, get_depth_history, get_all_depth_symbols

# Dosya yollari
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WATCHLIST_FILE = os.path.join(BASE_DIR, 'watchlist.json')
SIGNALS_FILE = os.path.join(BASE_DIR, 'signals.json')

# Kilit
_lock = threading.Lock()

# Watchlist
_watchlist: List[str] = []
_signals: List[dict] = []
_snapshot: Dict[str, dict] = {}  # onceki depth snapshot
_live_signals: Dict[str, dict] = {}  # anlik sinyaller


def load_watchlist():
    """Watchlist'i dosyadan yukle."""
    global _watchlist
    try:
        if os.path.exists(WATCHLIST_FILE):
            with open(WATCHLIST_FILE, 'r') as f:
                _watchlist = json.load(f)
    except Exception:
        _watchlist = []


def save_watchlist():
    """Watchlist'i dosyaya kaydet."""
    try:
        with open(WATCHLIST_FILE, 'w') as f:
            json.dump(_watchlist, f)
    except Exception:
        pass


def load_signals():
    """Sinyal gecmisini yukle."""
    global _signals
    try:
        if os.path.exists(SIGNALS_FILE):
            with open(SIGNALS_FILE, 'r') as f:
                _signals = json.load(f)
    except Exception:
        _signals = []


def save_signals():
    """Sinyal gecmisini kaydet (son 200)."""
    try:
        with open(SIGNALS_FILE, 'w') as f:
            json.dump(_signals[-200:], f)
    except Exception:
        pass


# --- Watchlist API ---

def get_watchlist() -> List[str]:
    with _lock:
        return list(_watchlist)


def add_to_watchlist(symbol: str) -> bool:
    symbol = symbol.upper().replace('.IS', '')
    with _lock:
        if symbol not in _watchlist:
            _watchlist.append(symbol)
            save_watchlist()
            return True
    return False


def remove_from_watchlist(symbol: str) -> bool:
    symbol = symbol.upper().replace('.IS', '')
    with _lock:
        if symbol in _watchlist:
            _watchlist.remove(symbol)
            save_watchlist()
            return True
    return False


# --- Signal Engine ---

def _detect_anomalies(symbol: str, current: dict, history: list) -> dict:
    """
    Derinlik gecmisini kullanarak olagan disi hareketleri tespit et.
    Donus: {'alerts': [...], 'trend': '...', 'unusual': bool}
    """
    alerts = []
    
    if not history or len(history) < 3:
        return {'alerts': alerts, 'trend': 'yetersiz_veri', 'unusual': False}
    
    # Guncel metrikler
    cur_alis_lot = sum(r[1] for r in current.get('alis', [])[:5] if len(r) > 1 and r[1] > 0)
    cur_satis_lot = sum(r[1] for r in current.get('satis', [])[:5] if len(r) > 1 and r[1] > 0)
    cur_spread = 0
    if current.get('alis') and current.get('satis'):
        cur_spread = current['satis'][0][0] - current['alis'][0][0]
    cur_price = current.get('price', 0)
    cur_total_lot = cur_alis_lot + cur_satis_lot
    
    # Son 3-10 snapshot'un ortalamasi
    recent = history[-10:] if len(history) >= 10 else history[-3:]
    avg_alis_lot = sum(h.get('alis_lot', 0) for h in recent) / len(recent)
    avg_satis_lot = sum(h.get('satis_lot', 0) for h in recent) / len(recent)
    avg_total_lot = avg_alis_lot + avg_satis_lot
    
    # 1. ANI LOT ARTIŞI (duvar oluşumu)
    if avg_total_lot > 1000:  # yeterli veri varsa
        alis_change_pct = (cur_alis_lot - avg_alis_lot) / avg_alis_lot if avg_alis_lot > 0 else 0
        satis_change_pct = (cur_satis_lot - avg_satis_lot) / avg_satis_lot if avg_satis_lot > 0 else 0
        
        if alis_change_pct > 1.0:  # %100'den fazla artış
            alerts.append({
                'type': 'wall_buy', 'severity': 'high',
                'msg': f'🚨 OLAĞAN DIŞI: Alış lotu ortalamanın %{int(alis_change_pct*100)} üzerinde! '
                       f'{cur_alis_lot/1000:.0f}K lot (ort: {avg_alis_lot/1000:.0f}K) - BÜYÜK ALIŞ DUVARI',
                'pct': round(alis_change_pct * 100)
            })
        elif alis_change_pct > 0.5:
            alerts.append({
                'type': 'wall_buy', 'severity': 'medium',
                'msg': f'⚠️ Alış lotu %{int(alis_change_pct*100)} arttı: {cur_alis_lot/1000:.0f}K lot',
                'pct': round(alis_change_pct * 100)
            })
        
        if satis_change_pct > 1.0:
            alerts.append({
                'type': 'wall_sell', 'severity': 'high',
                'msg': f'🚨 OLAĞAN DIŞI: Satış lotu ortalamanın %{int(satis_change_pct*100)} üzerinde! '
                       f'{cur_satis_lot/1000:.0f}K lot (ort: {avg_satis_lot/1000:.0f}K) - BÜYÜK SATIŞ DUVARI',
                'pct': round(satis_change_pct * 100)
            })
        elif satis_change_pct > 0.5:
            alerts.append({
                'type': 'wall_sell', 'severity': 'medium',
                'msg': f'⚠️ Satış lotu %{int(satis_change_pct*100)} arttı: {cur_satis_lot/1000:.0f}K lot',
                'pct': round(satis_change_pct * 100)
            })
    
    # 2. SPREAD ANOMALISI
    if cur_price > 0:
        cur_spread_pct = (cur_spread / cur_price) * 100 if cur_spread else 0
        # Ortalama spread hesapla
        avg_spreads = []
        for h in recent[-5:]:
            ba = h.get('best_alis', 0)
            bs = h.get('best_satis', 0)
            hp = h.get('price', cur_price)
            if ba and bs and hp:
                avg_spreads.append((bs - ba) / hp * 100)
        if avg_spreads:
            avg_spread_pct = sum(avg_spreads) / len(avg_spreads)
            if cur_spread_pct > avg_spread_pct * 2.5 and cur_spread_pct > 0.3:
                alerts.append({
                    'type': 'spread_wide', 'severity': 'medium',
                    'msg': f'📏 Spread anormal genişledi: %{cur_spread_pct:.2f} (normal: %{avg_spread_pct:.2f})',
                    'pct': round(cur_spread_pct, 2)
                })
            elif cur_spread_pct < avg_spread_pct * 0.3 and avg_spread_pct > 0.1:
                alerts.append({
                    'type': 'spread_narrow', 'severity': 'low',
                    'msg': f'📏 Spread daraldı: %{cur_spread_pct:.2f} (normal: %{avg_spread_pct:.2f}) - likidite artıyor',
                    'pct': round(cur_spread_pct, 2)
                })
    
    # 3. ALIŞ/SATIŞ DENGESİ KAYMASI
    if avg_alis_lot > 0 and avg_satis_lot > 0:
        cur_ratio = cur_alis_lot / cur_satis_lot if cur_satis_lot > 0 else 999
        avg_ratio = avg_alis_lot / avg_satis_lot if avg_satis_lot > 0 else 999
        if avg_ratio > 0:
            ratio_change = abs(cur_ratio - avg_ratio) / avg_ratio
            if ratio_change > 0.6:  # %60'dan fazla kayma
                direction = 'ALIŞ AĞIRLIKLI' if cur_ratio > avg_ratio else 'SATIŞ AĞIRLIKLI'
                alerts.append({
                    'type': 'balance_shift', 'severity': 'high' if ratio_change > 1.0 else 'medium',
                    'msg': f'⚖️ Denge kaydı: {direction} (önceki: {avg_ratio:.2f}, şimdi: {cur_ratio:.2f})',
                    'pct': round(ratio_change * 100)
                })
    
    # Trend tespiti
    trend = 'notr'
    if len(history) >= 5:
        first_half = history[:len(history)//2]
        second_half = history[len(history)//2:]
        first_avg = sum(h.get('alis_lot', 0) - h.get('satis_lot', 0) for h in first_half) / len(first_half)
        second_avg = sum(h.get('alis_lot', 0) - h.get('satis_lot', 0) for h in second_half) / len(second_half)
        diff = second_avg - first_avg
        if diff > 50000:
            trend = 'alis_birikiyor'
        elif diff < -50000:
            trend = 'satis_birikiyor'
    
    return {
        'alerts': alerts,
        'trend': trend,
        'unusual': len(alerts) > 0,
        'history_count': len(history)
    }


def _analyze_full(symbol: str, current: dict, previous: dict, price_data: dict) -> Optional[dict]:
    """
    Cok faktorlu sinyal analizi:
    1. Derinlik degisimi (agirlik: %35)
    2. Derinlik mutlak durumu (agirlik: %25)
    3. Spread & likidite (agirlik: %15)
    4. Fiyat momentumu (agirlik: %25)
    
    Composite score 0-100 uretir.
    """
    if not current:
        return None
    
    alis = current.get('alis', [])
    satis = current.get('satis', [])
    price = current.get('price', 0) or price_data.get('price', 0)
    
    if not alis or not satis or price <= 0:
        return None
    
    reasons = []
    
    # === 1. DERINLIK MUTLAK DURUMU (%25) ===
    near_alis = sum(row[1] for row in alis[:5] if len(row) > 1)
    near_satis = sum(row[1] for row in satis[:5] if len(row) > 1)
    total_alis = sum(row[1] for row in alis[:10] if len(row) > 1)
    total_satis = sum(row[1] for row in satis[:10] if len(row) > 1)
    
    depth_ratio = near_alis / near_satis if near_satis > 0 else 1
    total_ratio = total_alis / total_satis if total_satis > 0 else 1
    
    depth_score = 50
    if depth_ratio > 1.5:
        depth_score = 70
        reasons.append(f"Alis lotu satisin {depth_ratio:.1f}x uzerinde (guclu)")
    elif depth_ratio > 1.15:
        depth_score = 60
        reasons.append(f"Alis lotu satisin {depth_ratio:.1f}x uzerinde")
    elif depth_ratio < 0.67:
        depth_score = 30
        reasons.append(f"Satis lotu alisin {1/depth_ratio:.1f}x uzerinde (zayif)")
    elif depth_ratio < 0.87:
        depth_score = 40
        reasons.append(f"Satis lotu alisin {1/depth_ratio:.1f}x uzerinde")
    else:
        reasons.append(f"Alis/Satis dengeli ({depth_ratio:.2f})")
    
    # En iyi fiyatlar ve spread
    best_alis = alis[0][0] if alis else 0
    best_satis = satis[0][0] if satis else 0
    spread = best_satis - best_alis if best_alis and best_satis else 0
    spread_pct = (spread / price * 100) if price else 0
    
    # === 2. DERINLIK DEGISIMI (%35) ===
    change_score = 50
    if previous:
        prev_alis = sum(row[1] for row in previous.get('alis', [])[:5] if len(row) > 1)
        prev_satis = sum(row[1] for row in previous.get('satis', [])[:5] if len(row) > 1)
        prev_ratio = prev_alis / prev_satis if prev_satis > 0 else 1
        
        if prev_ratio > 0:
            ratio_change = (depth_ratio - prev_ratio) / prev_ratio
        else:
            ratio_change = 0
        
        # Ilk kademe duvar degisimi
        first_alis_now = alis[0][1] if len(alis[0]) > 1 else 0
        first_satis_now = satis[0][1] if len(satis[0]) > 1 else 0
        first_alis_prev = previous['alis'][0][1] if previous.get('alis') and len(previous['alis'][0]) > 1 else 0
        first_satis_prev = previous['satis'][0][1] if previous.get('satis') and len(previous['satis'][0]) > 1 else 0
        
        wall_a_chg = (first_alis_now - first_alis_prev) / first_alis_prev if first_alis_prev > 0 else 0
        wall_s_chg = (first_satis_now - first_satis_prev) / first_satis_prev if first_satis_prev > 0 else 0
        
        if ratio_change > 0.2:
            change_score = 80
            reasons.append(f"Alis/Satis orani %{int(ratio_change*100)} yukseldi")
        elif ratio_change > 0.08:
            change_score = 65
            reasons.append(f"Alis/Satis orani %{int(ratio_change*100)} artti")
        elif ratio_change < -0.2:
            change_score = 20
            reasons.append(f"Alis/Satis orani %{int(abs(ratio_change)*100)} dustu")
        elif ratio_change < -0.08:
            change_score = 35
            reasons.append(f"Alis/Satis orani %{int(abs(ratio_change)*100)} azaldi")
        elif wall_a_chg > 0.5:
            change_score = 75
            reasons.append(f"En iyi alista {first_alis_now/1000:.0f}K lot duvar olustu")
        elif wall_s_chg > 0.5:
            change_score = 25
            reasons.append(f"En iyi satista {first_satis_now/1000:.0f}K lot duvar olustu")
    
    # === 3. SPREAD & LIKIDITE (%15) ===
    spread_score = 50
    if spread_pct > 1.0:
        spread_score = 40
        reasons.append(f"Spread genis (%{spread_pct:.2f}) - likidite dusuk")
    elif spread_pct < 0.15:
        spread_score = 60
        reasons.append(f"Spread dar (%{spread_pct:.2f}) - likit")
    
    # Buyuk duvar tespiti
    big_wall_alis = any(len(row) > 1 and row[1] > 500000 for row in alis[:5])
    big_wall_satis = any(len(row) > 1 and row[1] > 500000 for row in satis[:5])
    if big_wall_alis:
        spread_score += 5
        reasons.append(f"500K+ alis duvari tespit edildi")
    if big_wall_satis:
        spread_score -= 5
        reasons.append(f"500K+ satis duvari tespit edildi")
    spread_score = max(10, min(90, spread_score))
    
    # === 4. FIYAT MOMENTUMU (%25) ===
    momentum_score = 50
    prev_price = price_data.get('prev_price', price)
    open_price = price_data.get('open', price)
    high = price_data.get('high', price)
    low = price_data.get('low', price)
    
    if prev_price and prev_price > 0:
        pct_change = (price - prev_price) / prev_price * 100
        if pct_change > 2:
            momentum_score = 80
            reasons.append(f"Fiyat %{pct_change:.1f} yukseldi (momentumlu)")
        elif pct_change > 0.5:
            momentum_score = 65
            reasons.append(f"Fiyat %{pct_change:.1f} yukseldi")
        elif pct_change < -2:
            momentum_score = 20
            reasons.append(f"Fiyat %{abs(pct_change):.1f} dustu (zayif)")
        elif pct_change < -0.5:
            momentum_score = 35
            reasons.append(f"Fiyat %{abs(pct_change):.1f} dustu")
    
    # Gun ici konum
    if open_price and open_price > 0 and high > low:
        day_position = (price - low) / (high - low) * 100 if (high - low) > 0 else 50
        if day_position > 80:
            momentum_score = min(85, momentum_score + 5)
        elif day_position < 20:
            momentum_score = max(15, momentum_score - 5)
    
    # === KOMPOZIT SKOR ===
    composite = (
        depth_score * 0.25 +
        change_score * 0.35 +
        spread_score * 0.15 +
        momentum_score * 0.25
    )
    
    # Sinyal tipi
    if composite >= 65:
        signal_type = 'AL'
        confidence = min(95, int(composite))
    elif composite <= 35:
        signal_type = 'SAT'
        confidence = min(95, int(100 - composite))
    else:
        signal_type = 'TUT'
        confidence = 50
    
    # Gereksiz TUT sinyalini gosterme
    if signal_type == 'TUT' and composite > 40 and composite < 60:
        return None
    
    # Entry/Stop
    entry = best_satis if signal_type == 'AL' else best_alis
    stop = best_alis if signal_type == 'AL' else best_satis
    
    return {
        'symbol': symbol,
        'type': signal_type,
        'confidence': confidence,
        'composite': round(composite, 1),
        'price': price,
        'entry': round(entry, 2) if entry else None,
        'stop': round(stop, 2) if stop else None,
        'reasons': reasons[:4],
        'details': {
            'depth_score': round(depth_score),
            'change_score': round(change_score),
            'spread_score': round(spread_score),
            'momentum_score': round(momentum_score),
            'depth_ratio': round(depth_ratio, 3),
            'spread_pct': round(spread_pct, 3),
            'near_alis_lot': near_alis,
            'near_satis_lot': near_satis,
        },
        'timestamp': datetime.now().isoformat(),
    }


def _fetch_price_data(symbol: str) -> dict:
    """Yahoo Finance'den anlik fiyat verisi cek."""
    try:
        import yfinance as yf
        ticker = yf.Ticker(symbol + '.IS')
        info = ticker.fast_info
        hist = ticker.history(period='1d')
        if not hist.empty:
            last = hist.iloc[-1]
            return {
                'price': float(info.get('lastPrice', info.get('regularMarketPrice', 0)) or 0),
                'prev_price': float(info.get('previousClose', 0) or 0),
                'open': float(last.get('Open', 0) or 0),
                'high': float(last.get('High', 0) or 0),
                'low': float(last.get('Low', 0) or 0),
            }
    except Exception:
        pass
    return {}


# SocketIO referansi (app.py'den enjekte edilir)
_socketio = None

def set_socketio(sio):
    """SocketIO instance'ini enjekte et (app.py tarafindan cagrilir)."""
    global _socketio
    _socketio = sio


def _push_signal(signal: dict):
    """SocketIO uzerinden frontend'e anlik bildirim gonder."""
    if _socketio:
        try:
            _socketio.emit('signal_alert', signal)
        except Exception:
            pass


def _signal_loop():
    """Ana sinyal dongusu - cok faktorlu analiz + anomali tespiti + anlik bildirim."""
    global _snapshot, _live_signals, _signals
    
    print("[Signal] Motor baslatildi (derinlik gecmisi + anomali tespiti). Watchlist izleniyor...")
    
    last_price_fetch = {}  # {symbol: timestamp}
    last_anomaly_push = {}  # {symbol: timestamp} - anomali bildirimi throttling
    
    while True:
        try:
            watchlist = get_watchlist()
            if not watchlist:
                time.sleep(3)
                continue
            
            for symbol in watchlist:
                current = get_depth_data(symbol)
                if not current or not current.get('alis'):
                    continue
                
                # Fiyat verisi (her 60sn'de bir cek)
                now = time.time()
                price_data = _price_cache.get(symbol, {})
                if symbol not in last_price_fetch or (now - last_price_fetch.get(symbol, 0)) > 60:
                    price_data = _fetch_price_data(symbol)
                    _price_cache[symbol] = price_data
                    last_price_fetch[symbol] = now
                
                previous = _snapshot.get(symbol)
                _snapshot[symbol] = current
                
                # === Anomali tespiti (derinlik gecmisi kullanarak) ===
                history = get_depth_history(symbol, 20)
                anomaly = _detect_anomalies(symbol, current, history)
                
                signal = _analyze_full(symbol, current, previous, price_data)
                
                # Sinyal varsa veya anomali varsa bildirim yap
                pushed = False
                
                if signal:
                    last = _live_signals.get(symbol)
                    skip = False
                    if last:
                        last_ts = datetime.fromisoformat(last['timestamp'])
                        now_ts = datetime.fromisoformat(signal['timestamp'])
                        if last['type'] == signal['type'] and (now_ts - last_ts).total_seconds() < 60:
                            skip = True
                    
                    if not skip:
                        # Anomali alert'lerini sinyale ekle
                        if anomaly['alerts']:
                            signal['anomalies'] = anomaly['alerts']
                            signal['unusual'] = True
                        else:
                            signal['unusual'] = False
                        
                        with _lock:
                            _live_signals[symbol] = signal
                            _signals.append(signal)
                        
                        _push_signal(signal)
                        pushed = True
                        
                        emoji = '🟢' if signal['type'] == 'AL' else '🔴' if signal['type'] == 'SAT' else '⚪'
                        print(f"[Signal] {emoji} {symbol}: {signal['type']} "
                              f"(%{signal['confidence']}) | Kompozit: {signal['composite']} | "
                              f"D:{signal['details']['depth_score']} C:{signal['details']['change_score']} "
                              f"S:{signal['details']['spread_score']} M:{signal['details']['momentum_score']}")
                        if signal.get('reasons'):
                            print(f"         -> {' | '.join(signal['reasons'])}")
                
                # Anomali varsa ama sinyal uretilmediyse, ayrica anomali bildirimi gonder
                if anomaly['unusual'] and not pushed:
                    last_ap = last_anomaly_push.get(symbol, 0)
                    if now - last_ap > 120:  # 2 dakikada bir anomali push
                        anomaly_signal = {
                            'symbol': symbol,
                            'type': 'ANOMALI',
                            'confidence': 75,
                            'composite': 50,
                            'price': current.get('price', 0),
                            'reasons': [a['msg'] for a in anomaly['alerts']],
                            'anomalies': anomaly['alerts'],
                            'unusual': True,
                            'trend': anomaly['trend'],
                            'timestamp': datetime.now().isoformat(),
                        }
                        with _lock:
                            _live_signals[symbol] = anomaly_signal
                            _signals.append(anomaly_signal)
                        _push_signal(anomaly_signal)
                        last_anomaly_push[symbol] = now
                        print(f"[Anomali] ⚡ {symbol}: {len(anomaly['alerts'])} olagan disi hareket!")
                        for a in anomaly['alerts']:
                            print(f"          {a['msg']}")
                
                # Trend bilgisi varsa logla
                if anomaly['trend'] not in ('notr', 'yetersiz_veri'):
                    trend_emoji = '📈' if anomaly['trend'] == 'alis_birikiyor' else '📉'
                    print(f"[Trend] {trend_emoji} {symbol}: {anomaly['trend']} (gecmis: {anomaly['history_count']} snapshot)")
                
                time.sleep(1.5)
            
            if len(_signals) % 10 == 0:
                save_signals()
            
            time.sleep(3)
            
        except Exception as e:
            print(f"[Signal] Dongu hatasi: {e}")
            time.sleep(5)


_price_cache = {}


def get_live_signals() -> Dict[str, dict]:
    """Anlik sinyalleri dondur."""
    with _lock:
        return dict(_live_signals)


def get_signal_history(count: int = 50) -> List[dict]:
    """Sinyal gecmisini dondur."""
    with _lock:
        return _signals[-count:]


def start_signal_engine():
    """Signal engine'i arka planda baslat."""
    load_watchlist()
    load_signals()
    
    # Varsayilan hisseleri ekle (ilk kez)
    if not _watchlist:
        _watchlist = ['THYAO', 'ASELS', 'GARAN']
        save_watchlist()
    
    thread = threading.Thread(target=_signal_loop, daemon=True)
    thread.start()
    print(f"[Signal] Engine baslatildi. Watchlist: {_watchlist}")
    return thread
