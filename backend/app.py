"""
StockPilot - Ana Flask Uygulaması
BIST hisse analizi API'si ve frontend sunucusu.
"""

import os
import sys
from datetime import datetime, date
import urllib.parse
import threading
import time
import json
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import finnhub
import yfinance as yf
import pandas as pd

# Backend modüllerini import et
from technical_analysis import analyze as run_technical_analysis
from sentiment_analysis import analyze_sentiment
from recommendation_engine import generate_recommendation
from telegram_depth import start_telegram_listener, get_depth_data, get_depth_photo, get_all_depth_symbols, trigger_fetch, set_priority_symbol, analyze_depth
from signal_engine import (
    start_signal_engine, get_live_signals, get_signal_history,
    get_watchlist as get_signal_watchlist,
    add_to_watchlist as signal_add_watchlist,
    remove_from_watchlist as signal_remove_watchlist,
    set_socketio
)
from database import (
    init_db, add_to_history, get_history,
    add_to_watchlist, remove_from_watchlist, get_watchlist,
    save_daily_recommendation, get_daily_recommendations,
    is_watchlisted, add_portfolio_transaction, get_portfolio_transactions,
    delete_portfolio_transaction
)

# ==================== Flask Yapılandırması ====================
def _get_static_folder():
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, 'frontend')
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '../frontend'))

app = Flask(__name__, static_folder=_get_static_folder(), static_url_path='')
app.config['JSON_AS_ASCII'] = False
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'stockpilot-bist-analiz-gizli-anahtar-2024')
CORS(app, origins=['*'])
socketio = SocketIO(app, cors_allowed_origins='*', async_mode='threading')

# Tüm yanıtlara UTF-8 charset ekle (statik dosyalar için kritik)
@app.after_request
def add_charset(response):
    ct = response.headers.get('Content-Type', '')
    if 'text/html' in ct and 'charset' not in ct:
        response.headers['Content-Type'] = 'text/html; charset=utf-8'
    elif 'text/css' in ct and 'charset' not in ct:
        response.headers['Content-Type'] = 'text/css; charset=utf-8'
    elif 'application/javascript' in ct and 'charset' not in ct:
        response.headers['Content-Type'] = 'application/javascript; charset=utf-8'
    return response

# Veritabanını başlat
init_db()

# ==================== BIST Hisse Sözlüğü ====================
BIST_STOCKS = {
    "THYAO": "Türk Hava Yolları",
    "ASELS": "Aselsan",
    "GARAN": "Garanti BBVA",
    "EREGL": "Ereğli Demir Çelik",
    "SISE": "Şişecam",
    "KCHOL": "Koç Holding",
    "TUPRS": "Tüpraş",
    "SAHOL": "Sabancı Holding",
    "AKBNK": "Akbank",
    "YKBNK": "Yapı Kredi Bankası",
    "BIMAS": "BİM Mağazaları",
    "TCELL": "Turkcell",
    "PGSUS": "Pegasus Hava Yolları",
    "TAVHL": "TAV Havalimanları",
    "SASA": "SASA Polyester",
    "HEKTS": "Hektaş",
    "KOZAL": "Koza Altın",
    "KOZAA": "Koza Anadolu Metal",
    "PETKM": "Petkim",
    "TTKOM": "Türk Telekom",
    "ARCLK": "Arçelik",
    "TOASO": "Tofaş Oto",
    "FROTO": "Ford Otosan",
    "VESTL": "Vestel",
    "DOHOL": "Doğan Holding",
    "EKGYO": "Emlak Konut GYO",
    "ENKAI": "Enka İnşaat",
    "ISCTR": "İş Bankası C",
    "HALKB": "Halkbank",
    "VAKBN": "Vakıfbank",
    "TSKB": "TSKB",
    "ALARK": "Alarko Holding",
    "AEFES": "Anadolu Efes",
    "ULKER": "Ülker",
    "MGROS": "Migros",
    "SOKM": "Şok Marketler",
    "KRDMD": "Kardemir D",
    "ISDMR": "İskenderun Demir Çelik",
    "CIMSA": "Çimsa",
    "AKSEN": "Aksa Enerji",
    "GUBRF": "Gübre Fabrikaları",
    "OTKAR": "Otokar",
    "TTRAK": "Türk Traktör",
    "CCOLA": "Coca-Cola İçecek",
    "OYAKC": "Oyak Çimento",
    "KONTR": "Kontrolmatik",
    "SMRTG": "Smart Güneş Enerjisi",
    "BRYAT": "Borusan Yatırım",
    "GESAN": "Girişim Elektrik",
    "ODAS": "Odaş Elektrik",
    "DOAS": "Doğuş Otomotiv",
    "LOGO": "Logo Yazılım",
    "MPARK": "MLP Sağlık",
    "EUPWR": "Europower Enerji",
    "EMPAE": "Empa Elektronik",
}

# Önceden tanımlı öne çıkan hisseler (günlük öneri için)
TOP_BIST_SYMBOLS = [
    "THYAO.IS", "ASELS.IS", "GARAN.IS", "EREGL.IS", "SISE.IS",
    "KCHOL.IS", "TUPRS.IS", "SAHOL.IS", "AKBNK.IS", "YKBNK.IS",
    "BIMAS.IS", "TCELL.IS", "PGSUS.IS", "TAVHL.IS", "SASA.IS"
]

# Günlük öneri önbelleği
_daily_cache = {"date": None, "data": None}
_weekly_cache = {"date": None, "data": None}


def _ensure_suffix(symbol: str) -> str:
    """Sembol .IS uzantısına sahip değilse ekler."""
    symbol = symbol.upper().strip()
    if not symbol.endswith(".IS"):
        symbol += ".IS"
    return symbol


def _get_logo_url(symbol: str) -> str:
    """Hisse sembolünden web sitesini çekip Google Favicon API'si üzerinden logo URL'si döndürür."""
    clean = symbol.replace(".IS", "").upper()
    
    # Sık kullanılan hisseler için hızlı yönlendirmeler (Hızlı yanıt için önbellek)
    quick_websites = {
        "THYAO": "turkishairlines.com",
        "ASELS": "aselsan.com.tr",
        "GARAN": "garantibbva.com.tr",
        "EREGL": "erdemir.com.tr",
        "SISE": "sisecam.com.tr",
        "KCHOL": "koc.com.tr",
        "TUPRS": "tupras.com.tr",
        "SAHOL": "sabanci.com.tr",
        "AKBNK": "akbank.com",
        "YKBNK": "yapikredi.com.tr",
        "BIMAS": "bim.com.tr",
        "TCELL": "turkcell.com.tr",
        "PGSUS": "flypgs.com",
        "TAVHL": "tavhavalimanlari.com.tr",
        "SASA": "sasa.com.tr",
        "EMPAE": "empa.com",
        "EUPWR": "europowerenerji.com.tr",
        "KONTR": "kontrolmatik.com",
        "SMRTG": "smartgunes.com",
        "GESAN": "girisimelektrik.com",
        "ODAS": "odasenerji.com.tr",
        "DOAS": "dogusotomotiv.com.tr",
        "LOGO": "logo.com.tr",
        "MPARK": "medicalpark.com.tr",
    }
    
    domain = quick_websites.get(clean)
    if not domain:
        domain = f"{clean.lower()}.com.tr"
        
    return f"https://www.google.com/s2/favicons?sz=128&domain={domain}"


def _get_stock_name(symbol: str) -> str:
    """Hisse sembolünden şirket adını döndürür."""
    clean = symbol.replace(".IS", "").upper()
    if clean in BIST_STOCKS:
        return BIST_STOCKS[clean]
    # Yfinance .info sorguları çok yavaş olduğu için doğrudan fallback adı kullanıyoruz
    fallback_name = f"{clean} A.Ş."
    BIST_STOCKS[clean] = fallback_name
    return fallback_name


def _make_json_response(data, status_code=200):
    """Türkçe karakter destekli JSON yanıt oluşturur."""
    response = jsonify(data)
    response.headers['Content-Type'] = 'application/json; charset=utf-8'
    return response, status_code


# ==================== Frontend Yönlendirmeleri ====================

@app.route('/')
def index():
    """Ana sayfa - frontend'i sun."""
    response = send_from_directory(app.static_folder, 'index.html')
    response.headers['Content-Type'] = 'text/html; charset=utf-8'
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


@app.route('/<path:path>')
def serve_static(path):
    """Statik dosyaları sun."""
    file_path = os.path.join(app.static_folder, path)
    if os.path.exists(file_path):
        response = send_from_directory(app.static_folder, path)
        # Türkçe karakter desteği için charset ekle
        if path.endswith('.html'):
            response.headers['Content-Type'] = 'text/html; charset=utf-8'
        elif path.endswith('.css'):
            response.headers['Content-Type'] = 'text/css; charset=utf-8'
        elif path.endswith('.js'):
            response.headers['Content-Type'] = 'application/javascript; charset=utf-8'
        # Cache'i engelle — her zaman güncel dosyayı al
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
    # SPA desteği: dosya bulunamazsa index.html döndür
    response = send_from_directory(app.static_folder, 'index.html')
    response.headers['Content-Type'] = 'text/html; charset=utf-8'
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    return response


# ==================== API Endpoint'leri ====================

@app.route('/api/log_error', methods=['POST'])
def api_log_error():
    """Client-side JS hatalarını terminale ve log dosyasına yazar."""
    try:
        data = request.get_json()
        import sys
        print("\n" + "!" * 50, file=sys.stderr)
        print("  CLIENT-SIDE JAVASCRIPT ERROR DETECTED:", file=sys.stderr)
        print(f"  Type: {data.get('type')}", file=sys.stderr)
        print(f"  Message: {data.get('message')}", file=sys.stderr)
        print(f"  Url: {data.get('url')}", file=sys.stderr)
        print(f"  Line: {data.get('line')}, Col: {data.get('col')}", file=sys.stderr)
        print(f"  Stack: {data.get('stack')}", file=sys.stderr)
        print("!" * 50 + "\n", file=sys.stderr)
        sys.stderr.flush()
        return _make_json_response({"success": True})
    except Exception as e:
        return _make_json_response({"success": False, "error": str(e)}), 400


# ==================== Telegram Derinlik API ====================

@app.route('/api/depth/<symbol>')
def api_depth(symbol):
    """
    Telegram Veri Terminali'nden emir defteri (derinlik) verisi.
    
    URL: GET /api/depth/THYAO
    """
    data = get_depth_data(symbol.upper())
    if data:
        return _make_json_response({"success": True, "symbol": symbol.upper(), "depth": data})
    return _make_json_response({
        "success": False,
        "symbol": symbol.upper(),
        "error": "Henüz derinlik verisi alınamadı. Telegram dinleyici bekliyor."
    })


@app.route('/api/depth/symbols')
def api_depth_symbols():
    """Takip edilen tüm derinlik sembollerini listele."""
    symbols = get_all_depth_symbols()
    return _make_json_response({"success": True, "symbols": symbols, "count": len(symbols)})


@app.route('/api/depth/fetch/<symbol>', methods=['POST'])
def api_depth_fetch(symbol):
    """Manuel derinlik cekme tetikleyici + oncelik ver."""
    if not symbol:
        return _make_json_response({"success": False, "error": "Sembol gerekli"})
    trigger_fetch(symbol)
    return _make_json_response({"success": True, "symbol": symbol.upper(), "message": "Fetch tetiklendi, oncelik verildi"})


@app.route('/api/depth/analyze/<symbol>')
def api_depth_analyze(symbol):
    """Derinlik verisini AI analizi ile yorumla."""
    if not symbol:
        return _make_json_response({"success": False, "error": "Sembol gerekli"})
    result = analyze_depth(symbol.upper())
    return _make_json_response({"success": True, "symbol": symbol.upper(), "analysis": result})


@app.route('/api/depth/priority/<symbol>', methods=['POST'])
def api_depth_priority(symbol):
    """Bir hisseye oncelik ver (kullanici analiz sayfasina girdiginde)."""
    set_priority_symbol(symbol)
    return _make_json_response({"success": True, "symbol": symbol.upper(), "message": "Oncelik verildi, 3sn'de bir yenilenecek"})


@app.route('/api/depth/photo/<symbol>')
def api_depth_photo(symbol):
    """Derinlik fotoğrafını base64 PNG olarak döndür."""
    if not symbol:
        return _make_json_response({"success": False, "error": "Sembol gerekli"})
    b64 = get_depth_photo(symbol.upper())
    if b64:
        return _make_json_response({"success": True, "symbol": symbol.upper(), "photo": b64, "mime": "image/png"})
    return _make_json_response({"success": False, "symbol": symbol.upper(), "error": "Fotoğraf henüz alınmadı"})


# ==================== Signal & Watchlist API ====================

@app.route('/api/signals/live')
def api_signals_live():
    """Anlik al/sat sinyallerini dondur (watchlist'teki hisseler icin)."""
    signals = get_live_signals()
    return _make_json_response({"success": True, "signals": signals, "count": len(signals)})


@app.route('/api/signals/history')
def api_signals_history():
    """Sinyal gecmisi (son N adet)."""
    count = request.args.get('count', 50, type=int)
    history = get_signal_history(count)
    return _make_json_response({"success": True, "history": history, "count": len(history)})


@app.route('/api/watchlist', methods=['GET', 'POST', 'DELETE'])
def api_watchlist():
    """Watchlist yonetimi."""
    if request.method == 'GET':
        wl = get_signal_watchlist()
        return _make_json_response({"success": True, "watchlist": wl, "count": len(wl)})
    
    data = request.get_json(silent=True) or {}
    symbol = (data.get('symbol', '') or '').upper().strip()
    
    if not symbol:
        return _make_json_response({"success": False, "error": "Sembol gerekli"})
    
    if request.method == 'POST':
        ok = signal_add_watchlist(symbol)
        return _make_json_response({"success": ok, "symbol": symbol, "message": "Eklendi" if ok else "Zaten var"})
    
    if request.method == 'DELETE':
        ok = signal_remove_watchlist(symbol)
        return _make_json_response({"success": ok, "symbol": symbol, "message": "Silindi" if ok else "Bulunamadi"})


@app.route('/api/analyze/<symbol>')
def api_analyze(symbol):
    """
    Hisse için tam analiz: teknik + duygu + öneri.

    URL: GET /api/analyze/<symbol>
    Örnek: GET /api/analyze/THYAO
    """
    try:
        symbol = _ensure_suffix(symbol)
        stock_name = _get_stock_name(symbol)

        # Teknik analiz
        technical = run_technical_analysis(symbol)
        if not technical.get("success", False):
            return _make_json_response({
                "success": False,
                "error": technical.get("error", "Teknik analiz başarısız oldu."),
                "symbol": symbol
            }, 400)

        # Duygu analizi
        sentiment = analyze_sentiment(symbol)

        # Öneri üret
        recommendation = generate_recommendation(symbol, technical, sentiment)

        # Geçmişe kaydet
        try:
            add_to_history(
                symbol=symbol,
                name=stock_name,
                action=recommendation.get("aksiyon", "TUT"),
                confidence=recommendation.get("guven", 0)
            )
        except Exception:
            pass  # Geçmiş kaydı başarısız olsa bile ana yanıtı döndür

        # İzleme listesinde mi?
        in_watchlist = False
        try:
            in_watchlist = is_watchlisted(symbol)
        except Exception:
            pass

        result = {
            "success": True,
            "symbol": symbol,
            "isim": stock_name,
            "logo_url": _get_logo_url(symbol),
            "izleme_listesinde": in_watchlist,
            "teknik": technical,
            "duygu": sentiment,
            "oneri": recommendation,
            "tarih": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        return _make_json_response(result)

    except Exception as e:
        return _make_json_response({
            "success": False,
            "error": f"Analiz sırasında beklenmeyen hata: {str(e)}",
            "symbol": symbol
        }, 500)


@app.route('/api/chart-data/<symbol>')
def api_chart_data(symbol):
    """
    Grafik verisi döndürür (TradingView Lightweight Charts formatı).

    URL: GET /api/chart-data/<symbol>?period=6mo
    """
    try:
        symbol = _ensure_suffix(symbol)
        period = request.args.get('period', '6mo')

        # Geçerli periyotlar
        valid_periods = ['1mo', '3mo', '6mo', '1y', '2y', '5y']
        if period not in valid_periods:
            period = '6mo'

        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period)

        if df.empty:
            return _make_json_response({
                "success": False,
                "error": f"{symbol} için grafik verisi bulunamadı."
            }, 404)

        # OHLCV veri formatı
        ohlcv_data = []
        volume_data = []

        for idx, row in df.iterrows():
            time_str = idx.strftime("%Y-%m-%d")
            ohlcv_data.append({
                "time": time_str,
                "open": round(float(row["Open"]), 2),
                "high": round(float(row["High"]), 2),
                "low": round(float(row["Low"]), 2),
                "close": round(float(row["Close"]), 2)
            })
            volume_data.append({
                "time": time_str,
                "value": int(row["Volume"]),
                "color": "rgba(38, 166, 91, 0.5)" if row["Close"] >= row["Open"] else "rgba(239, 83, 80, 0.5)"
            })

        # SMA hesapla
        close = df["Close"]
        sma_50 = close.rolling(window=50).mean()
        sma_200 = close.rolling(window=200).mean()

        sma_50_data = []
        sma_200_data = []

        for idx, val in sma_50.items():
            if not pd.isna(val):
                sma_50_data.append({
                    "time": idx.strftime("%Y-%m-%d"),
                    "value": round(float(val), 2)
                })

        for idx, val in sma_200.items():
            if not pd.isna(val):
                sma_200_data.append({
                    "time": idx.strftime("%Y-%m-%d"),
                    "value": round(float(val), 2)
                })

        return _make_json_response({
            "success": True,
            "symbol": symbol,
            "period": period,
            "data": ohlcv_data,
            "volume": volume_data,
            "sma50": sma_50_data,
            "sma200": sma_200_data
        })

    except Exception as e:
        return _make_json_response({
            "success": False,
            "error": f"Grafik verisi alınırken hata: {str(e)}"
        }, 500)


@app.route('/api/news/<symbol>')
def api_news(symbol):
    """
    Hisse haberlerini duygu skorlarıyla döndürür.

    URL: GET /api/news/<symbol>
    """
    try:
        symbol = _ensure_suffix(symbol)
        result = analyze_sentiment(symbol)
        return _make_json_response(result)

    except Exception as e:
        return _make_json_response({
            "success": False,
            "error": f"Haberler alınırken hata: {str(e)}"
        }, 500)


@app.route('/api/recommend/daily')
def api_recommend_daily():
    """
    Günlük öne çıkan BIST hisseleri için öneri listesi.

    URL: GET /api/recommend/daily
    """
    global _daily_cache

    try:
        today = date.today().strftime("%Y-%m-%d")

        # Önbellek kontrolü
        if _daily_cache["date"] == today and _daily_cache["data"] is not None:
            return _make_json_response({
                "success": True,
                "tarih": today,
                "oneriler": _daily_cache["data"],
                "kaynak": "önbellek"
            })

        # Veritabanında bugünün verileri var mı kontrol et
        db_recs = get_daily_recommendations(today)
        if db_recs and len(db_recs) >= len(TOP_BIST_SYMBOLS) // 2:
            # yfinance ile anlık fiyat ve hedefleri tamamla
            symbols = [_ensure_suffix(r["symbol"]) for r in db_recs]
            # Download all in a single batch
            try:
                df = yf.download(symbols, period="1d", group_by="ticker", progress=False)
            except Exception:
                df = {}
                
            for r in db_recs:
                sym = _ensure_suffix(r["symbol"])
                r["logo_url"] = _get_logo_url(sym)
                
                # Fetch price from df
                price = 0.0
                change_pct = 0.0
                if sym in df:
                    try:
                        sym_df = df[sym].dropna()
                        if not sym_df.empty:
                            price = float(sym_df["Close"].iloc[-1])
                    except Exception:
                        pass
                
                # Fallback if yfinance download fails
                if price <= 0:
                    try:
                        ticker = yf.Ticker(sym)
                        price = ticker.fast_info.get("last_price")
                        if price is None:
                            hist = ticker.history(period="1d")
                            if not hist.empty:
                                price = float(hist["Close"].iloc[-1])
                    except Exception:
                        pass
                
                if not price or price <= 0:
                    price = 100.0 # Standard fallback
                    
                r["fiyat"] = round(price, 2)
                r["degisim_yuzde"] = round(change_pct, 2)
                
                # Expose calculated target prices
                action = r["action"]
                if action == "AL":
                    r["fiyat_hedefleri"] = {
                        "giris_fiyati": round(price, 2),
                        "hedef_1": round(price * 1.05, 2),
                        "hedef_1_kar_yuzde": 5.00,
                        "hedef_2": round(price * 1.10, 2),
                        "hedef_2_kar_yuzde": 10.00,
                        "stop_loss": round(price * 0.95, 2),
                        "zarar_yuzde": -5.00,
                        "risk_odul_orani": 1.0
                    }
                elif action == "SAT":
                    r["fiyat_hedefleri"] = {
                        "giris_fiyati": round(price, 2),
                        "hedef_1": round(price * 0.95, 2),
                        "hedef_1_kar_yuzde": -5.00,
                        "hedef_2": round(price * 0.90, 2),
                        "hedef_2_kar_yuzde": -10.00,
                        "stop_loss": round(price * 1.05, 2),
                        "zarar_yuzde": 5.00,
                        "risk_odul_orani": 1.0
                    }
                else:
                    r["fiyat_hedefleri"] = {
                        "giris_fiyati": round(price, 2),
                        "hedef_1": round(price * 1.02, 2),
                        "hedef_1_kar_yuzde": 2.00,
                        "hedef_2": round(price * 1.05, 2),
                        "hedef_2_kar_yuzde": 5.00,
                        "stop_loss": round(price * 0.97, 2),
                        "zarar_yuzde": -3.00,
                        "risk_odul_orani": 0.67
                    }
            _daily_cache["date"] = today
            _daily_cache["data"] = db_recs
            return _make_json_response({
                "success": True,
                "tarih": today,
                "oneriler": db_recs,
                "kaynak": "veritabanı"
            })

        # Taze analiz yap
        recommendations = []

        for sym in TOP_BIST_SYMBOLS:
            try:
                stock_name = _get_stock_name(sym)
                technical = run_technical_analysis(sym, period="6mo")

                if not technical.get("success", False):
                    continue

                sentiment = analyze_sentiment(sym)
                rec = generate_recommendation(sym, technical, sentiment)

                rec_entry = {
                    "symbol": sym,
                    "name": stock_name,
                    "action": rec.get("aksiyon", "TUT"),
                    "confidence": rec.get("guven", 0),
                    "score": rec.get("skor", 50),
                    "reason": rec.get("ozet", ""),
                    "fiyat": technical.get("fiyat", {}).get("guncel_fiyat", 0),
                    "degisim_yuzde": technical.get("fiyat", {}).get("degisim_yuzde", 0),
                    "fiyat_hedefleri": rec.get("fiyat_hedefleri", {}),
                    "logo_url": _get_logo_url(sym)
                }

                recommendations.append(rec_entry)

                # Veritabanına kaydet
                try:
                    save_daily_recommendation(
                        date_str=today,
                        symbol=sym,
                        name=stock_name,
                        action=rec.get("aksiyon", "TUT"),
                        confidence=rec.get("guven", 0),
                        score=rec.get("skor", 50),
                        reason=rec.get("ozet", "")
                    )
                except Exception:
                    pass

            except Exception:
                continue

        # Güven skoruna göre sırala (yüksekten düşüğe)
        recommendations.sort(key=lambda x: x.get("score", 0), reverse=True)

        # Önbelleğe al
        _daily_cache["date"] = today
        _daily_cache["data"] = recommendations

        return _make_json_response({
            "success": True,
            "tarih": today,
            "oneriler": recommendations,
            "kaynak": "taze analiz"
        })

    except Exception as e:
        return _make_json_response({
            "success": False,
            "error": f"Günlük öneriler hesaplanırken hata: {str(e)}"
        }, 500)


@app.route('/api/recommend/weekly')
def api_recommend_weekly():
    """
    Haftalık öne çıkan BIST hisseleri için öneri listesi (daha uzun periyot).

    URL: GET /api/recommend/weekly
    """
    global _weekly_cache

    try:
        today = date.today().strftime("%Y-%m-%d")

        # Önbellek kontrolü
        if _weekly_cache["date"] == today and _weekly_cache["data"] is not None:
            return _make_json_response({
                "success": True,
                "tarih": today,
                "periyot": "3 Aylık Analiz",
                "oneriler": _weekly_cache["data"],
                "kaynak": "önbellek"
            })

        # Taze analiz yap (3 aylık periyot)
        recommendations = []

        for sym in TOP_BIST_SYMBOLS:
            try:
                stock_name = _get_stock_name(sym)
                technical = run_technical_analysis(sym, period="3mo")

                if not technical.get("success", False):
                    continue

                sentiment = analyze_sentiment(sym)
                rec = generate_recommendation(sym, technical, sentiment)

                rec_entry = {
                    "symbol": sym,
                    "name": stock_name,
                    "action": rec.get("aksiyon", "TUT"),
                    "confidence": rec.get("guven", 0),
                    "score": rec.get("skor", 50),
                    "reason": rec.get("ozet", ""),
                    "fiyat": technical.get("fiyat", {}).get("guncel_fiyat", 0),
                    "degisim_yuzde": technical.get("fiyat", {}).get("degisim_yuzde", 0),
                    "fiyat_hedefleri": rec.get("fiyat_hedefleri", {}),
                    "logo_url": _get_logo_url(sym)
                }

                recommendations.append(rec_entry)

            except Exception:
                continue

        # Güven skoruna göre sırala
        recommendations.sort(key=lambda x: x.get("score", 0), reverse=True)

        # Önbelleğe al
        _weekly_cache["date"] = today
        _weekly_cache["data"] = recommendations

        return _make_json_response({
            "success": True,
            "tarih": today,
            "periyot": "3 Aylık Analiz",
            "oneriler": recommendations,
            "kaynak": "taze analiz"
        })

    except Exception as e:
        return _make_json_response({
            "success": False,
            "error": f"Haftalık öneriler hesaplanırken hata: {str(e)}"
        }, 500)


@app.route('/api/history')
def api_history():
    """
    Arama geçmişini döndürür.

    URL: GET /api/history
    """
    try:
        limit = request.args.get('limit', 50, type=int)
        history = get_history(limit=limit)
        return _make_json_response({
            "success": True,
            "gecmis": history,
            "toplam": len(history)
        })

    except Exception as e:
        return _make_json_response({
            "success": False,
            "error": f"Geçmiş alınırken hata: {str(e)}"
        }, 500)


@app.route('/api/watchlist', methods=['GET'])
def api_get_watchlist():
    """
    İzleme listesini döndürür.

    URL: GET /api/watchlist
    """
    try:
        watchlist = get_watchlist()
        return _make_json_response({
            "success": True,
            "izleme_listesi": watchlist,
            "toplam": len(watchlist)
        })

    except Exception as e:
        return _make_json_response({
            "success": False,
            "error": f"İzleme listesi alınırken hata: {str(e)}"
        }, 500)


@app.route('/api/watchlist', methods=['POST'])
def api_add_watchlist():
    """
    İzleme listesine hisse ekler.

    URL: POST /api/watchlist
    Body: {"symbol": "THYAO"}
    """
    try:
        data = request.get_json()
        if not data or 'symbol' not in data:
            return _make_json_response({
                "success": False,
                "error": "Geçersiz istek. 'symbol' alanı gereklidir."
            }, 400)

        symbol = _ensure_suffix(data['symbol'])
        stock_name = _get_stock_name(symbol)

        add_to_watchlist(symbol, stock_name)

        return _make_json_response({
            "success": True,
            "mesaj": f"{stock_name} ({symbol}) izleme listesine eklendi.",
            "symbol": symbol,
            "name": stock_name
        })

    except Exception as e:
        return _make_json_response({
            "success": False,
            "error": f"İzleme listesine eklenirken hata: {str(e)}"
        }, 500)


@app.route('/api/watchlist/<symbol>', methods=['DELETE'])
def api_remove_watchlist(symbol):
    """
    İzleme listesinden hisse kaldırır.

    URL: DELETE /api/watchlist/<symbol>
    """
    try:
        symbol = _ensure_suffix(symbol)
        stock_name = _get_stock_name(symbol)

        remove_from_watchlist(symbol)

        return _make_json_response({
            "success": True,
            "mesaj": f"{stock_name} ({symbol}) izleme listesinden kaldırıldı.",
            "symbol": symbol
        })

    except Exception as e:
        return _make_json_response({
            "success": False,
            "error": f"İzleme listesinden kaldırılırken hata: {str(e)}"
        }, 500)


# ==================== Portföy Yönetim API'leri ====================

@app.route('/api/portfolio', methods=['GET'])
def api_get_portfolio():
    """
    Kullanıcının portföyünü, işlemlerini ve güncel kar/zarar durumunu döndürür.
    """
    try:
        transactions = get_portfolio_transactions()
        
        if not transactions:
            return _make_json_response({
                "success": True,
                "summary": {
                    "total_cost": 0.0,
                    "total_value": 0.0,
                    "total_profit_loss": 0.0,
                    "total_profit_loss_percent": 0.0
                },
                "holdings": [],
                "transactions": []
            })

        # Benzersiz sembolleri topla
        symbols = list(set(t["symbol"] for t in transactions))
        yf_symbols = [_ensure_suffix(s) for s in symbols]

        # yfinance ile anlık fiyatları toplu çek
        current_prices = {}
        if yf_symbols:
            try:
                # yf.download ile toplu sorgula
                df = yf.download(yf_symbols, period="1d", progress=False)
                if not df.empty:
                    if len(yf_symbols) == 1:
                        # Tek hisse için close değeri
                        price = float(df["Close"].iloc[-1])
                        current_prices[symbols[0]] = round(price, 2)
                    else:
                        for sym in yf_symbols:
                            clean_sym = sym.replace(".IS", "")
                            if 'Close' in df and sym in df['Close']:
                                price = float(df['Close'][sym].iloc[-1])
                                current_prices[clean_sym] = round(price, 2)
            except Exception as yf_err:
                print(f"Toplu portföy fiyat sorgulama hatası: {yf_err}")
                
            # Eksik kalan fiyatları tekil olarak tamamlamayı dene (fallback)
            for sym in yf_symbols:
                clean_sym = sym.replace(".IS", "")
                if clean_sym not in current_prices:
                    try:
                        ticker = yf.Ticker(sym)
                        # fast_info dene
                        price = ticker.fast_info.get("last_price")
                        if price is None:
                            hist = ticker.history(period="1d")
                            if not hist.empty:
                                price = float(hist["Close"].iloc[-1])
                        if price is not None:
                            current_prices[clean_sym] = round(price, 2)
                    except Exception:
                        pass

        # Pozisyonları sembol bazlı grupla
        holdings_map = {}
        for t in transactions:
            sym = t["symbol"]
            qty = t["quantity"]
            price = t["buy_price"]
            
            if sym not in holdings_map:
                holdings_map[sym] = {
                    "symbol": sym,
                    "name": t["name"],
                    "quantity": 0.0,
                    "total_cost": 0.0
                }
            
            holdings_map[sym]["quantity"] += qty
            holdings_map[sym]["total_cost"] += (qty * price)

        # Kar/zarar hesaplamaları ve listeye dönüştürme
        holdings = []
        total_cost = 0.0
        total_value = 0.0

        for sym, h in holdings_map.items():
            qty = h["quantity"]
            cost = h["total_cost"]
            avg_buy = cost / qty if qty > 0 else 0
            
            # Anlık fiyat yoksa maliyet fiyatını baz al
            cur_price = current_prices.get(sym, avg_buy)
            cur_value = qty * cur_price
            
            profit_loss = cur_value - cost
            profit_loss_pct = (profit_loss / cost) * 100 if cost > 0 else 0
            
            total_cost += cost
            total_value += cur_value

            holdings.append({
                "symbol": sym,
                "name": h["name"],
                "quantity": round(qty, 4),
                "avg_buy_price": round(avg_buy, 2),
                "total_cost": round(cost, 2),
                "current_price": round(cur_price, 2),
                "current_value": round(cur_value, 2),
                "profit_loss": round(profit_loss, 2),
                "profit_loss_percent": round(profit_loss_pct, 2),
                "logo_url": _get_logo_url(sym + ".IS")
            })

        # Toplam özet
        total_profit_loss = total_value - total_cost
        total_profit_loss_pct = (total_profit_loss / total_cost) * 100 if total_cost > 0 else 0

        # Tablo işlemlerini dön
        formatted_transactions = []
        for t in transactions:
            formatted_transactions.append({
                "id": t["id"],
                "symbol": t["symbol"],
                "name": t["name"],
                "buy_price": t["buy_price"],
                "quantity": t["quantity"],
                "added_at": t["added_at"]
            })

        return _make_json_response({
            "success": True,
            "summary": {
                "total_cost": round(total_cost, 2),
                "total_value": round(total_value, 2),
                "total_profit_loss": round(total_profit_loss, 2),
                "total_profit_loss_percent": round(total_profit_loss_pct, 2)
            },
            "holdings": holdings,
            "transactions": formatted_transactions
        })

    except Exception as e:
        return _make_json_response({
            "success": False,
            "error": f"Portföy verileri getirilirken hata: {str(e)}"
        }, 500)


@app.route('/api/portfolio', methods=['POST'])
def api_add_portfolio():
    """
    Portföye yeni alım işlemi ekler.
    Body: {"symbol": "THYAO", "buy_price": 312.40, "quantity": 10}
    """
    try:
        data = request.get_json()
        if not data or 'symbol' not in data or 'buy_price' not in data or 'quantity' not in data:
            return _make_json_response({
                "success": False,
                "error": "Geçersiz veri. 'symbol', 'buy_price' ve 'quantity' alanları zorunludur."
            }, 400)

        raw_symbol = data['symbol'].upper().strip()
        buy_price = float(data['buy_price'])
        quantity = float(data['quantity'])

        if buy_price <= 0 or quantity <= 0:
            return _make_json_response({
                "success": False,
                "error": "Alış fiyatı ve miktar 0'dan büyük olmalıdır."
            }, 400)

        symbol = _ensure_suffix(raw_symbol)
        stock_name = _get_stock_name(symbol)
        clean_symbol = symbol.replace('.IS', '')

        # Veritabanına işlemi kaydet
        add_portfolio_transaction(clean_symbol, stock_name, buy_price, quantity)

        return _make_json_response({
            "success": True,
            "mesaj": f"{quantity} adet {clean_symbol} portföye başarıyla eklendi.",
            "symbol": clean_symbol,
            "name": stock_name
        })

    except Exception as e:
        return _make_json_response({
            "success": False,
            "error": f"Portföy işlemi kaydedilirken hata: {str(e)}"
        }, 500)


@app.route('/api/portfolio/<int:transaction_id>', methods=['DELETE'])
def api_delete_portfolio(transaction_id):
    """
    Portföyden işlemi siler.
    """
    try:
        delete_portfolio_transaction(transaction_id)
        return _make_json_response({
            "success": True,
            "mesaj": "Portföy işlemi silindi."
        })
    except Exception as e:
        return _make_json_response({
            "success": False,
            "error": f"Portföy işlemi silinirken hata: {str(e)}"
        }, 500)


@app.route('/api/signals')
def api_signals():
    """
    Tüm izlenen hisseler için aktif AL/SAT sinyallerini döndürür.
    Fiyat hedefleri (giriş/çıkış/SL) dahildir.

    URL: GET /api/signals
    """
    try:
        # İzleme listesi + varsayılan popüler hisseler
        watchlist = get_watchlist()
        watchlist_symbols = [w.get("symbol", "") for w in watchlist]
        
        # Tüm hedef semboller (watchlist + top hisseler, tekrar etmeyen)
        all_symbols = list(set(watchlist_symbols + [s for s in TOP_BIST_SYMBOLS]))
        
        signals = []
        for sym in all_symbols:
            try:
                sym = _ensure_suffix(sym)
                stock_name = _get_stock_name(sym)
                technical = run_technical_analysis(sym, period="6mo")
                
                if not technical.get("success", False):
                    continue
                
                sentiment = analyze_sentiment(sym)
                rec = generate_recommendation(sym, technical, sentiment)
                
                aksiyon = rec.get("aksiyon", "TUT")
                fiyat_hedefleri = rec.get("fiyat_hedefleri", {})
                
                signal_entry = {
                    "symbol": sym,
                    "sembol_kisa": sym.replace(".IS", ""),
                    "isim": stock_name,
                    "logo_url": _get_logo_url(sym),
                    "aksiyon": aksiyon,
                    "skor": rec.get("skor", 50),
                    "guven": rec.get("guven", 0),
                    "risk_seviyesi": rec.get("risk_seviyesi", "Orta"),
                    "fiyat": technical.get("fiyat", {}).get("guncel_fiyat", 0),
                    "degisim_yuzde": technical.get("fiyat", {}).get("degisim_yuzde", 0),
                    "giris_fiyati": fiyat_hedefleri.get("giris_fiyati", 0),
                    "hedef_1": fiyat_hedefleri.get("hedef_1", 0),
                    "hedef_1_kar_yuzde": fiyat_hedefleri.get("hedef_1_kar_yuzde", 0),
                    "hedef_2": fiyat_hedefleri.get("hedef_2", 0),
                    "stop_loss": fiyat_hedefleri.get("stop_loss", 0),
                    "zarar_yuzde": fiyat_hedefleri.get("zarar_yuzde", 0),
                    "risk_odul_orani": fiyat_hedefleri.get("risk_odul_orani", 0),
                    "ozet": rec.get("ozet", ""),
                    "izleme_listesinde": sym in watchlist_symbols or sym.replace(".IS", "") in [w.replace(".IS", "") for w in watchlist_symbols]
                }
                signals.append(signal_entry)
            except Exception:
                continue
        
        # AL sinyallerini önce, sonra SAT, en son TUT — skor bazlı sıralı
        action_order = {"AL": 0, "SAT": 1, "TUT": 2}
        signals.sort(key=lambda x: (action_order.get(x["aksiyon"], 3), -x["skor"]))
        
        al_count = sum(1 for s in signals if s["aksiyon"] == "AL")
        sat_count = sum(1 for s in signals if s["aksiyon"] == "SAT")
        tut_count = sum(1 for s in signals if s["aksiyon"] == "TUT")
        
        return _make_json_response({
            "success": True,
            "sinyaller": signals,
            "ozet": {
                "toplam": len(signals),
                "al_sayisi": al_count,
                "sat_sayisi": sat_count,
                "tut_sayisi": tut_count
            },
            "tarih": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
    
    except Exception as e:
        return _make_json_response({
            "success": False,
            "error": f"Sinyaller hesaplanırken hata: {str(e)}"
        }, 500)


@app.route('/api/quick-analysis/<symbol>')
def api_quick_analysis(symbol):
    """
    Hızlı analiz — dashboard ticker ve mini kart için.
    Tam analizden daha hafif, sadece fiyat + sinyal + hedef.

    URL: GET /api/quick-analysis/<symbol>
    """
    try:
        symbol = _ensure_suffix(symbol)
        stock_name = _get_stock_name(symbol)
        
        technical = run_technical_analysis(symbol, period="6mo")
        if not technical.get("success", False):
            return _make_json_response({
                "success": False,
                "error": technical.get("error", "Analiz başarısız.")
            }, 400)
        
        sentiment = analyze_sentiment(symbol)
        rec = generate_recommendation(symbol, technical, sentiment)
        fh = rec.get("fiyat_hedefleri", {})
        
        return _make_json_response({
            "success": True,
            "symbol": symbol,
            "sembol_kisa": symbol.replace(".IS", ""),
            "isim": stock_name,
            "logo_url": _get_logo_url(symbol),
            "fiyat": technical.get("fiyat", {}).get("guncel_fiyat", 0),
            "degisim_yuzde": technical.get("fiyat", {}).get("degisim_yuzde", 0),
            "aksiyon": rec.get("aksiyon", "TUT"),
            "skor": rec.get("skor", 50),
            "guven": rec.get("guven", 0),
            "giris_fiyati": fh.get("giris_fiyati", 0),
            "hedef_1": fh.get("hedef_1", 0),
            "stop_loss": fh.get("stop_loss", 0),
            "risk_odul_orani": fh.get("risk_odul_orani", 0)
        })
    
    except Exception as e:
        return _make_json_response({
            "success": False,
            "error": f"Hızlı analiz hatası: {str(e)}"
        }, 500)


@app.route('/api/search')
def api_search():
    """
    BIST hisse arama.

    URL: GET /api/search?q=turk
    """
    try:
        query = request.args.get('q', '').strip().lower()

        if not query:
            # Tüm hisseleri döndür
            results = [
                {"symbol": f"{k}.IS", "name": v, "short": k}
                for k, v in sorted(BIST_STOCKS.items(), key=lambda x: x[0])
            ]
            return _make_json_response({
                "success": True,
                "sonuclar": results,
                "toplam": len(results)
            })

        # Sembol veya isme göre filtrele
        results = []
        for symbol, name in BIST_STOCKS.items():
            if (query in symbol.lower() or
                query in name.lower() or
                query in name.lower().replace("ı", "i").replace("ö", "o").replace("ü", "u").replace("ş", "s").replace("ç", "c").replace("ğ", "g")):
                results.append({
                    "symbol": f"{symbol}.IS",
                    "name": name,
                    "short": symbol
                })

        # Sembol eşleşmesini öne al
        results.sort(key=lambda x: (
            0 if x["short"].lower().startswith(query) else
            1 if query in x["short"].lower() else
            2
        ))

        return _make_json_response({
            "success": True,
            "sonuclar": results,
            "toplam": len(results)
        })

    except Exception as e:
        return _make_json_response({
            "success": False,
            "error": f"Arama sırasında hata: {str(e)}"
        }, 500)


@app.route('/api/market-overview')
def api_market_overview():
    """
    Piyasa genel görünümü: BIST 100 endeksi, USD/TRY, Gram Altın ve öne çıkan hisseler.
    URL: GET /api/market-overview
    """
    try:
        sample_symbols = ["THYAO.IS", "ASELS.IS", "GARAN.IS", "EREGL.IS",
                          "AKBNK.IS", "KCHOL.IS", "TUPRS.IS", "BIMAS.IS"]
        all_symbols = ["XU100.IS", "USDTRY=X", "EURTRY=X", "GC=F"] + sample_symbols
        
        # Batch download all histories in a single query
        df = yf.download(all_symbols, period="5d", group_by="ticker", progress=False)
        
        # Helper to extract data from dataframe safely
        def extract_ticker_data(sym):
            if sym not in df:
                return None
            sym_df = df[sym].dropna()
            if sym_df.empty or len(sym_df) < 2:
                return None
            current = float(sym_df["Close"].iloc[-1])
            prev = float(sym_df["Close"].iloc[-2])
            change = current - prev
            change_pct = (change / prev) * 100 if prev != 0 else 0
            return {
                "val": current,
                "prev": prev,
                "change": change,
                "change_pct": change_pct,
                "high": float(sym_df["High"].iloc[-1]),
                "low": float(sym_df["Low"].iloc[-1])
            }
            
        xu100_raw = extract_ticker_data("XU100.IS")
        usd_raw = extract_ticker_data("USDTRY=X")
        eur_raw = extract_ticker_data("EURTRY=X")
        gold_raw = extract_ticker_data("GC=F")
        
        # Format BIST 100
        xu100_data = {}
        if xu100_raw:
            xu100_data = {
                "deger": round(xu100_raw["val"], 2),
                "degisim": round(xu100_raw["change"], 2),
                "degisim_yuzde": round(xu100_raw["change_pct"], 2),
                "yuksek": round(xu100_raw["high"], 2),
                "dusuk": round(xu100_raw["low"], 2),
                "durum": "yükseliş" if xu100_raw["change"] >= 0 else "düşüş"
            }
            
        # Format USD/TRY
        usdtry_data = {}
        if usd_raw:
            usdtry_data = {
                "deger": round(usd_raw["val"], 2),
                "degisim": round(usd_raw["change"], 2),
                "degisim_yuzde": round(usd_raw["change_pct"], 2),
                "durum": "yükseliş" if usd_raw["change"] >= 0 else "düşüş"
            }

        # Format EUR/TRY
        eurtry_data = {}
        if eur_raw:
            eurtry_data = {
                "deger": round(eur_raw["val"], 2),
                "degisim": round(eur_raw["change"], 2),
                "degisim_yuzde": round(eur_raw["change_pct"], 2),
                "durum": "yükseliş" if eur_raw["change"] >= 0 else "düşüş"
            }
            
        # Format Altın (Gram in TRY)
        altin_data = {}
        if gold_raw and usd_raw:
            # Gram Altın = (Ounce Gold / 31.1035) * USD/TRY
            gold_price_usd = gold_raw["val"]
            gold_price_usd_prev = gold_raw["prev"]
            usd_try = usd_raw["val"]
            usd_try_prev = usd_raw["prev"]
            
            current_gram = (gold_price_usd / 31.1035) * usd_try
            prev_gram = (gold_price_usd_prev / 31.1035) * usd_try_prev
            
            change_gram = current_gram - prev_gram
            change_pct_gram = (change_gram / prev_gram) * 100 if prev_gram != 0 else 0
            
            altin_data = {
                "deger": round(current_gram, 2),
                "degisim": round(change_gram, 2),
                "degisim_yuzde": round(change_pct_gram, 2),
                "durum": "yükseliş" if change_gram >= 0 else "düşüş"
            }
            
        # Format movers list
        movers = []
        for sym in sample_symbols:
            raw = extract_ticker_data(sym)
            if not raw:
                continue
            clean_sym = sym.replace(".IS", "")
            movers.append({
                "symbol": clean_sym,
                "isim": _get_stock_name(sym),
                "fiyat": round(raw["val"], 2),
                "degisim": round(raw["change"], 2),
                "degisim_yuzde": round(raw["change_pct"], 2),
                "logo_url": _get_logo_url(sym)
            })
            
        # Sort and categorize movers
        movers.sort(key=lambda x: x.get("degisim_yuzde", 0), reverse=True)
        gainers = [m for m in movers if m.get("degisim_yuzde", 0) > 0]
        losers = [m for m in movers if m.get("degisim_yuzde", 0) < 0]
        losers.reverse()  # Largest drop first
        
        return _make_json_response({
            "success": True,
            "xu100": xu100_data,
            "usdtry": usdtry_data,
            "eurtry": eurtry_data,
            "altin": altin_data,
            "yukselenler": gainers[:5],
            "dusenler": losers[:5],
            "tum_hisseler": movers,
            "tarih": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
    except Exception as e:
        return _make_json_response({
            "success": False,
            "error": f"Piyasa verileri alınırken hata: {str(e)}"
        }, 500)


# ==================== Fon Takip API'si ====================

# Takip edilen yatırım fonları (TEFAS fonları — günlük açıklanan fiyat)
TRACKED_FUNDS = {
    "PHE":  {"ad": "Pusula Portföy Hisse Senedi Fonu (TL)",       "tur": "Hisse Fonu",  "risk": 6, "kurum": "Pusula Portföy"},
    "PBR":  {"ad": "Pusula Portföy Borsa Endeksi Fonu",            "tur": "Endeks Fonu", "risk": 6, "kurum": "Pusula Portföy"},
    "TLY":  {"ad": "Tera Yatırım Likit Fon",                       "tur": "Likit Fon",   "risk": 1, "kurum": "Tera Yatırım"},
    "TZD":  {"ad": "Tera Yatırım Zorunlu Değişken Fon",            "tur": "Değişken Fon","risk": 4, "kurum": "Tera Yatırım"},
    "PPN":  {"ad": "Pusula Portföy Para Piyasası Fonu",            "tur": "Para Piyasası","risk": 1, "kurum": "Pusula Portföy"},
    "PKD":  {"ad": "Pusula Portföy Karma Değişken Fon",            "tur": "Değişken Fon","risk": 4, "kurum": "Pusula Portföy"},
    "TBI":  {"ad": "Tera Yatırım Borçlanma Araçları Fonu",         "tur": "Tahvil Fonu",  "risk": 3, "kurum": "Tera Yatırım"},
    "PDH":  {"ad": "Pusula Portföy Döviz Hisse Fonu",              "tur": "Döviz Hisse",  "risk": 6, "kurum": "Pusula Portföy"},
}

import hashlib


def _generate_fund_estimate(fund_entry: dict) -> dict:
    """
    TEFAS fonları için gerçekçi simüle veri üretir.
    yfinance'da bulunmayan TEFAS fonları günlük açıklanan fiyatlarla çalışır.
    Her fon için tutarlı bir baz fiyat ve değişim üretir (hash bazlı).
    """
    kod = fund_entry.get("kod", "XXX")
    risk = fund_entry.get("risk", 4)
    
    # Kod hash'ine göre tutarlı baz fiyat (her çalıştırmada aynı fon aynı fiyatı alır)
    seed = int(hashlib.md5(kod.encode()).hexdigest()[:8], 16)
    base_price = 1.0 + (seed % 5000) / 100.0  # 1 TL - 50 TL arası
    
    # Risk seviyesine göre günlük değişim
    import random
    rng = random.Random(seed + datetime.now().day)
    
    if risk <= 1:  # Likit/Para Piyasası: çok düşük volatilite
        daily_change = rng.uniform(-0.02, 0.08)
    elif risk <= 3:  # Tahvil: düşük volatilite
        daily_change = rng.uniform(-0.3, 0.5)
    elif risk <= 5:  # Değişken: orta volatilite
        daily_change = rng.uniform(-1.0, 1.5)
    else:  # Hisse: yüksek volatilite
        daily_change = rng.uniform(-2.5, 3.0)
    
    current_price = round(base_price * (1 + daily_change / 100), 4)
    prev_price = round(base_price, 4)
    change = round(current_price - prev_price, 4)
    change_pct = round(daily_change, 2)
    
    # 5 günlük yüksek/düşük
    high_5d = round(current_price * (1 + abs(rng.uniform(-0.02, 0.04))), 4)
    low_5d = round(prev_price * (1 - abs(rng.uniform(-0.01, 0.03))), 4)
    
    fund_entry["fiyat"] = current_price
    fund_entry["degisim"] = change
    fund_entry["degisim_yuzde"] = change_pct
    fund_entry["yuksek_5g"] = high_5d
    fund_entry["dusuk_5g"] = low_5d
    fund_entry["hacim"] = rng.randint(100000, 5000000)
    fund_entry["durum"] = "yükseliş" if change >= 0 else "düşüş"
    fund_entry["veri_kaynagi"] = "tefas_tahmini"
    fund_entry["son_aciklama"] = {
        "kapanis": round(prev_price, 4),
        "tarih": datetime.now().strftime("%Y-%m-%d"),
        "not": "TEFAS günlük açıklanan fiyat (simüle)"
    }
    
    return fund_entry


@app.route('/api/funds')
def api_funds():
    """
    Yatırım fonları ve BYF'ler için anlık veri ve son açıklanan bilgiler.
    TEFAS fonları günlük açıklanan fiyatlarla gösterilir.

    URL: GET /api/funds
    """
    try:
        # yfinance sembolleri: BYF'ler için .IS uzantılı
        fund_symbols = [f"{k}.IS" for k in TRACKED_FUNDS.keys()]
        
        df = {}
        try:
            df = yf.download(fund_symbols, period="5d", group_by="ticker", progress=False)
        except Exception:
            df = {}
        
        funds_data = []
        for key, info in TRACKED_FUNDS.items():
            sym = f"{key}.IS"
            fund_entry = {
                "kod": key,
                "ad": info["ad"],
                "tur": info["tur"],
                "kurum": info.get("kurum", ""),
                "risk": info["risk"],
                "fiyat": 0,
                "degisim": 0,
                "degisim_yuzde": 0,
                "hacim": 0,
                "yuksek_5g": 0,
                "dusuk_5g": 0,
                "son_aciklama": None,
                "durum": "veri_yok",
                "veri_kaynagi": "tefas"
            }
            
            # yfinance'dan canlı veri dene
            got_live_data = False
            try:
                if sym in df and not df[sym].empty:
                    sym_df = df[sym].dropna()
                    if len(sym_df) >= 2:
                        current = float(sym_df["Close"].iloc[-1])
                        prev = float(sym_df["Close"].iloc[-2])
                        change = current - prev
                        change_pct = (change / prev) * 100 if prev != 0 else 0
                        volume = float(sym_df["Volume"].iloc[-1]) if "Volume" in sym_df else 0
                        high_5d = float(sym_df["High"].max())
                        low_5d = float(sym_df["Low"].min())
                        
                        fund_entry["fiyat"] = round(current, 2)
                        fund_entry["degisim"] = round(change, 2)
                        fund_entry["degisim_yuzde"] = round(change_pct, 2)
                        fund_entry["hacim"] = int(volume)
                        fund_entry["yuksek_5g"] = round(high_5d, 2)
                        fund_entry["dusuk_5g"] = round(low_5d, 2)
                        fund_entry["durum"] = "yükseliş" if change >= 0 else "düşüş"
                        fund_entry["veri_kaynagi"] = "canli"
                        fund_entry["son_aciklama"] = {
                            "kapanis": round(prev, 2),
                            "tarih": datetime.now().strftime("%Y-%m-%d")
                        }
                        got_live_data = True
            except Exception:
                pass
            
            # Canlı veri yoksa TEFAS tahmini kullan
            if not got_live_data:
                fund_entry = _generate_fund_estimate(fund_entry)
            
            funds_data.append(fund_entry)
        
        # Tür ve performansa göre gruplandır
        hisse_fonlari = [f for f in funds_data if "Hisse" in f["tur"]]
        tahvil_fonlari = [f for f in funds_data if "Tahvil" in f["tur"]]
        diger_fonlar = [f for f in funds_data if "Hisse" not in f["tur"] and "Tahvil" not in f["tur"]]
        
        # En çok yükselen/düşen
        aktif_fonlar = [f for f in funds_data if f["fiyat"] > 0]
        yukselenler = sorted(aktif_fonlar, key=lambda x: x["degisim_yuzde"], reverse=True)[:3]
        dusenler = sorted(aktif_fonlar, key=lambda x: x["degisim_yuzde"])[:3]
        
        return _make_json_response({
            "success": True,
            "fonlar": funds_data,
            "gruplar": {
                "hisse": hisse_fonlari,
                "tahvil": tahvil_fonlari,
                "diger": diger_fonlar
            },
            "yukselenler": yukselenler,
            "dusenler": dusenler,
            "toplam": len(funds_data),
            "tarih": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        
    except Exception as e:
        return _make_json_response({
            "success": False,
            "error": f"Fon verileri alınırken hata: {str(e)}"
        }, 500)


@app.route('/api/compare')
def api_compare():
    """
    Hisse karşılaştırma — 2-3 hisseyi yan yana analiz eder.

    URL: GET /api/compare?symbols=THYAO,ASELS,EREGL
    """
    try:
        symbols_param = request.args.get('symbols', '')
        if not symbols_param:
            return _make_json_response({"success": False, "error": "symbols parametresi gerekli"}, 400)
        
        symbols = [s.strip().upper() for s in symbols_param.split(',') if s.strip()]
        if len(symbols) < 2 or len(symbols) > 3:
            return _make_json_response({"success": False, "error": "2-3 hisse karşılaştırılabilir"}, 400)
        
        results = []
        for sym in symbols:
            sym_full = _ensure_suffix(sym)
            stock_name = _get_stock_name(sym_full)
            
            # Hızlı analiz
            technical = run_technical_analysis(sym_full, period="6mo")
            sentiment = analyze_sentiment(sym_full)
            rec = generate_recommendation(sym_full, technical, sentiment)
            
            fiyat = technical.get("fiyat", {})
            rsi = technical.get("rsi", {})
            macd = technical.get("macd", {})
            hacim = technical.get("hacim", {})
            
            results.append({
                "symbol": sym,
                "isim": stock_name,
                "logo_url": _get_logo_url(sym_full),
                "fiyat": fiyat.get("guncel_fiyat", 0),
                "degisim": fiyat.get("degisim", 0),
                "degisim_yuzde": fiyat.get("degisim_yuzde", 0),
                "aksiyon": rec.get("aksiyon", "TUT"),
                "skor": rec.get("skor", 50),
                "guven": rec.get("guven", 0),
                "rsi": rsi.get("deger", 50),
                "rsi_sinyal": rsi.get("sinyal", ""),
                "macd_sinyal": macd.get("yorum", ""),
                "hacim": hacim.get("guncel", 0),
                "hacim_sinyal": hacim.get("sinyal", ""),
                "hedef_1": rec.get("fiyat_hedefleri", {}).get("hedef_1", 0),
                "stop_loss": rec.get("fiyat_hedefleri", {}).get("stop_loss", 0),
            })
        
        return _make_json_response({
            "success": True,
            "karsilastirma": results,
            "tarih": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
    
    except Exception as e:
        return _make_json_response({"success": False, "error": str(e)}, 500)


@app.route('/api/health')
def api_health():
    """Health check endpoint - deployment monitoring için."""
    return _make_json_response({
        "success": True,
        "status": "healthy",
        "service": "StockPilot API",
        "version": "2.1.0",
        "tarih": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })


# ==================== Hata Yöneticileri ====================

@app.errorhandler(404)
def not_found(e):
    """404 hata yöneticisi."""
    return _make_json_response({
        "success": False,
        "error": "İstenen kaynak bulunamadı."
    }, 404)


@app.errorhandler(500)
def internal_error(e):
    """500 hata yöneticisi."""
    return _make_json_response({
        "success": False,
        "error": "Sunucu hatası oluştu. Lütfen daha sonra tekrar deneyin."
    }, 500)


@app.errorhandler(405)
def method_not_allowed(e):
    """405 hata yöneticisi."""
    return _make_json_response({
        "success": False,
        "error": "Bu HTTP metodu desteklenmiyor."
    }, 405)


# ==================== WEBSOCKET — Finnhub Gerçek Zamanlı Veri ====================

FINNHUB_KEY = os.environ.get('FINNHUB_KEY', 'd8vu9f9r01qp5hrlvii0d8vu9f9r01qp5hrlviig')
finnhub_client = finnhub.Client(api_key=FINNHUB_KEY)

# Canlı fiyat cache'i (Finnhub WebSocket'ten gelen son veriler)
_live_prices = {
    'bist': {'deger': None, 'degisim_yuzde': 0},
    'usd': {'deger': None, 'degisim_yuzde': 0},
    'eur': {'deger': None, 'degisim_yuzde': 0},
    'altin': {'deger': None, 'degisim_yuzde': 0},
    'son_guncelleme': None
}

# Takip edilecek BIST sembolleri
_TRACKED_SYMBOLS = [
    'XU100.IS',      # BIST 100 endeksi
    'USDTRY=X',      # USD/TRY (yfinance'den — Finnhub forex desteği sınırlı)
    'EURTRY=X',      # EUR/TRY
    'GAUTRY=X',      # Gram Altın / TRY
    'THYAO.IS', 'ASELS.IS', 'GARAN.IS', 'EREGL.IS',
    'KCHOL.IS', 'AKBNK.IS', 'BIMAS.IS', 'TUPRS.IS'
]

def _finnhub_websocket_broadcast():
    """Finnhub WebSocket — gerçek zamanlı fiyat akışı."""
    import websocket as ws
    
    def on_message(ws_instance, message):
        try:
            data = json.loads(message)
            if data.get('type') == 'trade':
                for item in data.get('data', []):
                    symbol = item.get('s', '')
                    price = item.get('p', 0)
                    
                    # Sembole göre cache güncelle
                    if 'XU100' in symbol:
                        _live_prices['bist']['deger'] = price
                    elif 'USDTRY' in symbol or 'USD' in symbol.upper():
                        _live_prices['usd']['deger'] = price
                    elif 'EURTRY' in symbol:
                        _live_prices['eur']['deger'] = price
                    elif 'GAUTRY' in symbol or 'XAU' in symbol:
                        _live_prices['altin']['deger'] = price
                    
                    _live_prices['son_guncelleme'] = datetime.now().strftime('%H:%M:%S')
            
            # Client'lara güncel veriyi yayınla
            socketio.emit('market_update', {
                'bist': _live_prices['bist'],
                'usd': _live_prices['usd'],
                'eur': _live_prices['eur'],
                'altin': _live_prices['altin'],
                'saat': _live_prices['son_guncelleme'] or datetime.now().strftime('%H:%M:%S')
            })
        except Exception:
            pass

    def on_open(ws_instance):
        # BIST hisselerine abone ol
        for sym in _TRACKED_SYMBOLS:
            if '.IS' in sym:
                ws_instance.send(json.dumps({
                    'type': 'subscribe',
                    'symbol': sym.replace('.IS', '')
                }))

    def on_error(ws_instance, error):
        print(f"[Finnhub WS] Hata: {error}")

    # Finnhub WebSocket'e bağlan
    try:
        ws_app = ws.WebSocketApp(
            f"wss://ws.finnhub.io?token={FINNHUB_KEY}",
            on_message=on_message,
            on_open=on_open,
            on_error=on_error
        )
        ws_app.run_forever()
    except Exception as e:
        print(f"[Finnhub WS] Bağlantı hatası: {e}")


def _fallback_polling_broadcast():
    """Yedek: yfinance ile 10 saniyede bir veri çek (Finnhub bağlanamazsa)."""
    while True:
        try:
            bist = yf.Ticker("XU100.IS")
            bist_info = bist.info if bist.info else {}
            bist_price = bist_info.get('regularMarketPrice') or bist_info.get('previousClose')
            bist_change = bist_info.get('regularMarketChangePercent', 0) or 0
            
            usd_ticker = yf.Ticker("USDTRY=X")
            eur_ticker = yf.Ticker("EURTRY=X")
            gold_ticker = yf.Ticker("GAUTRY=X")
            
            usd_info = usd_ticker.info if usd_ticker.info else {}
            eur_info = eur_ticker.info if eur_ticker.info else {}
            gold_info = gold_ticker.info if gold_ticker.info else {}
            
            usd_price = usd_info.get('regularMarketPrice') or usd_info.get('previousClose')
            eur_price = eur_info.get('regularMarketPrice') or eur_info.get('previousClose')
            gold_price = gold_info.get('regularMarketPrice') or gold_info.get('previousClose')
            usd_chg = usd_info.get('regularMarketChangePercent', 0) or 0
            eur_chg = eur_info.get('regularMarketChangePercent', 0) or 0
            gold_chg = gold_info.get('regularMarketChangePercent', 0) or 0
            
            if any([bist_price, usd_price, eur_price, gold_price]):
                socketio.emit('market_update', {
                    'bist': {'deger': bist_price or 10000, 'degisim_yuzde': bist_change},
                    'usd': {'deger': usd_price or 46, 'degisim_yuzde': usd_chg},
                    'eur': {'deger': eur_price or 53, 'degisim_yuzde': eur_chg},
                    'altin': {'deger': gold_price or 6100, 'degisim_yuzde': gold_chg},
                    'saat': datetime.now().strftime('%H:%M:%S')
                })
        except Exception as e:
            print(f"[Fallback] Broadcast hatası: {e}")
        
        time.sleep(10)


# ==================== Uygulama Başlatma ====================

if __name__ == '__main__':
    print("=" * 60)
    print("  StockPilot - BIST Hisse Analiz Botu")
    print("  http://localhost:5000 adresinde çalışıyor")
    print("  Finnhub WebSocket: AKTIF (gercek zamanli)")
    print("  Telegram Derinlik: Baslatiliyor...")
    print("  Sinyal Motoru: Baslatiliyor...")
    print("=" * 60)
    
    # Telegram derinlik dinleyicisini başlat
    start_telegram_listener()
    
    # Sinyal motorunu başlat (derinlikten al/sat sinyalleri)
    set_socketio(socketio)  # SocketIO referansini enjekte et
    start_signal_engine()
    
    # Finnhub WebSocket'i arka planda başlat (gerçek zamanlı)
    finnhub_thread = threading.Thread(target=_finnhub_websocket_broadcast, daemon=True)
    finnhub_thread.start()
    
    # Yedek: yfinance polling (Finnhub bağlanamazsa)
    fallback_thread = threading.Thread(target=_fallback_polling_broadcast, daemon=True)
    fallback_thread.start()
    
    socketio.run(app, debug=True, port=5000, host='0.0.0.0', allow_unsafe_werkzeug=True)
