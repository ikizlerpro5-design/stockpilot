"""
StockPilot - Teknik Analiz Modülü
BIST hisseleri için kapsamlı teknik analiz hesaplamaları.
yfinance OHLCV verileri üzerinde pandas/numpy kullanılarak hesaplanır.
"""

import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime


def _ensure_suffix(symbol: str) -> str:
    """Sembol .IS uzantısına sahip değilse ekler."""
    symbol = symbol.upper().strip()
    if not symbol.endswith(".IS"):
        symbol += ".IS"
    return symbol


def _calculate_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """RSI (Relative Strength Index) hesapla."""
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)

    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def _calculate_macd(close: pd.Series, fast: int = 12, slow: int = 26, signal_period: int = 9) -> tuple:
    """MACD (Moving Average Convergence Divergence) hesapla."""
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def _calculate_bollinger_bands(close: pd.Series, period: int = 20, std_dev: int = 2) -> tuple:
    """Bollinger Bantları hesapla."""
    middle = close.rolling(window=period).mean()
    std = close.rolling(window=period).std()
    upper = middle + (std * std_dev)
    lower = middle - (std * std_dev)
    return upper, middle, lower


def _calculate_stochastic(high: pd.Series, low: pd.Series, close: pd.Series,
                          k_period: int = 14, d_period: int = 3) -> tuple:
    """Stochastic Oscillator hesapla."""
    lowest_low = low.rolling(window=k_period).min()
    highest_high = high.rolling(window=k_period).max()

    k_percent = 100 * (close - lowest_low) / (highest_high - lowest_low)
    d_percent = k_percent.rolling(window=d_period).mean()
    return k_percent, d_percent


def _calculate_adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """ADX (Average Directional Index) hesapla."""
    plus_dm = high.diff()
    minus_dm = -low.diff()

    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)

    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    atr = true_range.ewm(span=period, adjust=False).mean()
    plus_di = 100 * (plus_dm.ewm(span=period, adjust=False).mean() / atr)
    minus_di = 100 * (minus_dm.ewm(span=period, adjust=False).mean() / atr)

    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    adx = dx.ewm(span=period, adjust=False).mean()
    return adx


def _get_rsi_signal(rsi_value: float) -> str:
    """RSI sinyali belirle."""
    if rsi_value >= 70:
        return "Aşırı Alım"
    elif rsi_value <= 30:
        return "Aşırı Satım"
    else:
        return "Nötr"


def _get_macd_signal(macd_val: float, signal_val: float, prev_macd: float, prev_signal: float) -> str:
    """MACD sinyali belirle."""
    if prev_macd <= prev_signal and macd_val > signal_val:
        return "AL"
    elif prev_macd >= prev_signal and macd_val < signal_val:
        return "SAT"
    else:
        return "Nötr"


def _get_bollinger_signal(close_val: float, upper: float, lower: float, middle: float) -> str:
    """Bollinger Bantları sinyali belirle."""
    band_width = upper - lower
    if band_width == 0:
        return "Nötr"

    position = (close_val - lower) / band_width

    if position >= 0.95:
        return "Aşırı Alım - Üst Bant Üzerinde"
    elif position >= 0.80:
        return "Üst Banta Yakın - Dikkat"
    elif position <= 0.05:
        return "Aşırı Satım - Alt Bant Altında"
    elif position <= 0.20:
        return "Alt Banta Yakın - Fırsat Olabilir"
    else:
        return "Nötr - Bantlar Arasında"


def _get_stochastic_signal(k_val: float, d_val: float) -> str:
    """Stochastic Oscillator sinyali belirle."""
    if k_val > 80 and d_val > 80:
        return "Aşırı Alım"
    elif k_val < 20 and d_val < 20:
        return "Aşırı Satım"
    elif k_val > d_val and k_val < 80:
        return "Yükseliş Sinyali"
    elif k_val < d_val and k_val > 20:
        return "Düşüş Sinyali"
    else:
        return "Nötr"


def _get_adx_signal(adx_value: float) -> str:
    """ADX trend gücü sinyali belirle."""
    if adx_value >= 50:
        return "Çok Güçlü Trend"
    elif adx_value >= 25:
        return "Güçlü Trend"
    elif adx_value >= 20:
        return "Zayıf Trend"
    else:
        return "Trendsiz / Yatay"


def _calculate_support_resistance(high: pd.Series, low: pd.Series, close: pd.Series) -> dict:
    """Destek ve direnç seviyelerini hesapla (son dönem min/max bazlı)."""
    recent_20 = close.tail(20)
    recent_50 = close.tail(50)
    recent_high_20 = high.tail(20)
    recent_low_20 = low.tail(20)
    recent_high_50 = high.tail(50)
    recent_low_50 = low.tail(50)

    current_price = float(close.iloc[-1])

    # Temel destek/direnç: son dönem min/max
    support_1 = float(recent_low_20.min())
    support_2 = float(recent_low_50.min())
    resistance_1 = float(recent_high_20.max())
    resistance_2 = float(recent_high_50.max())

    # Pivot noktaları (klasik)
    last_high = float(high.iloc[-1])
    last_low = float(low.iloc[-1])
    last_close = float(close.iloc[-1])
    pivot = (last_high + last_low + last_close) / 3
    pivot_s1 = (2 * pivot) - last_high
    pivot_s2 = pivot - (last_high - last_low)
    pivot_r1 = (2 * pivot) - last_low
    pivot_r2 = pivot + (last_high - last_low)

    return {
        "destek_1": round(support_1, 2),
        "destek_2": round(support_2, 2),
        "direnc_1": round(resistance_1, 2),
        "direnc_2": round(resistance_2, 2),
        "pivot": round(pivot, 2),
        "pivot_destek_1": round(pivot_s1, 2),
        "pivot_destek_2": round(pivot_s2, 2),
        "pivot_direnc_1": round(pivot_r1, 2),
        "pivot_direnc_2": round(pivot_r2, 2),
        "guncel_fiyat": round(current_price, 2)
    }


def _calculate_fibonacci_levels(high: pd.Series, low: pd.Series, close: pd.Series) -> dict:
    """Fibonacci retracement seviyelerini hesapla (son 60 günlük swing bazlı)."""
    lookback = min(60, len(close))
    recent_high = float(high.tail(lookback).max())
    recent_low = float(low.tail(lookback).min())
    current_price = float(close.iloc[-1])

    diff = recent_high - recent_low
    if diff <= 0:
        diff = 1  # sıfıra bölme koruması

    # Yükseliş trendinde (fiyat orta noktanın üzerindeyse) — geri çekilme seviyeleri
    # Düşüş trendinde (fiyat orta noktanın altındaysa) — toparlanma seviyeleri
    mid_point = (recent_high + recent_low) / 2
    is_uptrend = current_price >= mid_point

    fib_levels = {
        "swing_yuksek": round(recent_high, 2),
        "swing_dusuk": round(recent_low, 2),
        "trend_yonu": "Yükseliş" if is_uptrend else "Düşüş",
        "seviye_0": round(recent_high, 2),
        "seviye_0236": round(recent_high - diff * 0.236, 2),
        "seviye_0382": round(recent_high - diff * 0.382, 2),
        "seviye_0500": round(recent_high - diff * 0.500, 2),
        "seviye_0618": round(recent_high - diff * 0.618, 2),
        "seviye_0786": round(recent_high - diff * 0.786, 2),
        "seviye_1": round(recent_low, 2),
    }

    # Fiyatın bulunduğu Fibonacci bölgesi
    position = (current_price - recent_low) / diff
    if position >= 0.786:
        fib_levels["bolge"] = "Üst Bölge (0.786-1.0) — Direnç yakın"
    elif position >= 0.618:
        fib_levels["bolge"] = "Altın Oran Bölgesi (0.618-0.786)"
    elif position >= 0.500:
        fib_levels["bolge"] = "Orta Bölge (0.500-0.618)"
    elif position >= 0.382:
        fib_levels["bolge"] = "Geri Çekilme Bölgesi (0.382-0.500)"
    elif position >= 0.236:
        fib_levels["bolge"] = "Derin Geri Çekilme (0.236-0.382)"
    else:
        fib_levels["bolge"] = "Alt Bölge (0-0.236) — Destek yakın"

    return fib_levels


def _calculate_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> float:
    """ATR (Average True Range) hesapla — volatilite ve stop-loss mesafesi için."""
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = true_range.ewm(span=period, adjust=False).mean()
    return float(atr.iloc[-1]) if not pd.isna(atr.iloc[-1]) else 0.0


def analyze(symbol: str, period: str = "1y") -> dict:
    """
    Belirtilen BIST hissesi için kapsamlı teknik analiz yapar.

    Args:
        symbol: Hisse sembolü (örn: "THYAO" veya "THYAO.IS")
        period: Veri periyodu (varsayılan: "1y")

    Returns:
        dict: Tüm teknik göstergeleri içeren sözlük
    """
    symbol = _ensure_suffix(symbol)

    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period)

        if df.empty:
            return {
                "success": False,
                "error": f"{symbol} için veri bulunamadı. Lütfen geçerli bir BIST sembolü girin.",
                "symbol": symbol
            }

        # Minimum veri kontrolü
        if len(df) < 50:
            return {
                "success": False,
                "error": f"{symbol} için yeterli geçmiş veri yok (en az 50 gün gerekli).",
                "symbol": symbol
            }

        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        volume = df["Volume"]
        open_price = df["Open"]

        current_price = float(close.iloc[-1])
        prev_close = float(close.iloc[-2]) if len(close) >= 2 else current_price
        price_change = current_price - prev_close
        price_change_pct = (price_change / prev_close) * 100 if prev_close != 0 else 0

        # ==================== RSI ====================
        rsi_series = _calculate_rsi(close, 14)
        rsi_value = float(rsi_series.iloc[-1]) if not pd.isna(rsi_series.iloc[-1]) else 50.0
        rsi_signal = _get_rsi_signal(rsi_value)

        # ==================== MACD ====================
        macd_line, signal_line, histogram = _calculate_macd(close)
        macd_val = float(macd_line.iloc[-1]) if not pd.isna(macd_line.iloc[-1]) else 0.0
        signal_val = float(signal_line.iloc[-1]) if not pd.isna(signal_line.iloc[-1]) else 0.0
        hist_val = float(histogram.iloc[-1]) if not pd.isna(histogram.iloc[-1]) else 0.0

        prev_macd = float(macd_line.iloc[-2]) if len(macd_line) >= 2 and not pd.isna(macd_line.iloc[-2]) else 0.0
        prev_signal = float(signal_line.iloc[-2]) if len(signal_line) >= 2 and not pd.isna(signal_line.iloc[-2]) else 0.0
        macd_signal = _get_macd_signal(macd_val, signal_val, prev_macd, prev_signal)

        # ==================== Bollinger Bantları ====================
        bb_upper, bb_middle, bb_lower = _calculate_bollinger_bands(close)
        bb_upper_val = float(bb_upper.iloc[-1]) if not pd.isna(bb_upper.iloc[-1]) else current_price
        bb_middle_val = float(bb_middle.iloc[-1]) if not pd.isna(bb_middle.iloc[-1]) else current_price
        bb_lower_val = float(bb_lower.iloc[-1]) if not pd.isna(bb_lower.iloc[-1]) else current_price
        bb_signal = _get_bollinger_signal(current_price, bb_upper_val, bb_lower_val, bb_middle_val)

        # ==================== SMA 50 & SMA 200 ====================
        sma_50 = close.rolling(window=50).mean()
        sma_200 = close.rolling(window=200).mean()

        sma_50_val = float(sma_50.iloc[-1]) if not pd.isna(sma_50.iloc[-1]) else None
        sma_200_val = float(sma_200.iloc[-1]) if not pd.isna(sma_200.iloc[-1]) else None

        # Golden Cross / Death Cross tespiti
        sma_cross_signal = "Hesaplanamadı"
        if sma_50_val is not None and sma_200_val is not None and len(sma_50) >= 2 and len(sma_200) >= 2:
            prev_sma50 = float(sma_50.iloc[-2]) if not pd.isna(sma_50.iloc[-2]) else None
            prev_sma200 = float(sma_200.iloc[-2]) if not pd.isna(sma_200.iloc[-2]) else None

            if prev_sma50 is not None and prev_sma200 is not None:
                if prev_sma50 <= prev_sma200 and sma_50_val > sma_200_val:
                    sma_cross_signal = "Golden Cross (Altın Kesişim) - Güçlü AL"
                elif prev_sma50 >= prev_sma200 and sma_50_val < sma_200_val:
                    sma_cross_signal = "Death Cross (Ölüm Kesişimi) - Güçlü SAT"
                elif sma_50_val > sma_200_val:
                    sma_cross_signal = "SMA50 > SMA200 - Yükseliş Trendi"
                else:
                    sma_cross_signal = "SMA50 < SMA200 - Düşüş Trendi"

        # ==================== EMA 12 & EMA 26 ====================
        ema_12 = close.ewm(span=12, adjust=False).mean()
        ema_26 = close.ewm(span=26, adjust=False).mean()
        ema_12_val = float(ema_12.iloc[-1]) if not pd.isna(ema_12.iloc[-1]) else None
        ema_26_val = float(ema_26.iloc[-1]) if not pd.isna(ema_26.iloc[-1]) else None

        ema_signal = "Nötr"
        if ema_12_val is not None and ema_26_val is not None:
            if ema_12_val > ema_26_val:
                ema_signal = "Yükseliş (EMA12 > EMA26)"
            else:
                ema_signal = "Düşüş (EMA12 < EMA26)"

        # ==================== Stochastic Oscillator ====================
        k_percent, d_percent = _calculate_stochastic(high, low, close)
        k_val = float(k_percent.iloc[-1]) if not pd.isna(k_percent.iloc[-1]) else 50.0
        d_val = float(d_percent.iloc[-1]) if not pd.isna(d_percent.iloc[-1]) else 50.0
        stoch_signal = _get_stochastic_signal(k_val, d_val)

        # ==================== ADX ====================
        adx_series = _calculate_adx(high, low, close)
        adx_val = float(adx_series.iloc[-1]) if not pd.isna(adx_series.iloc[-1]) else 0.0
        adx_signal = _get_adx_signal(adx_val)

        # ==================== Hacim Analizi ====================
        vol_avg_20 = float(volume.tail(20).mean()) if len(volume) >= 20 else float(volume.mean())
        vol_current = float(volume.iloc[-1])
        vol_ratio = vol_current / vol_avg_20 if vol_avg_20 > 0 else 1.0

        if vol_ratio >= 2.0:
            vol_signal = "Çok Yüksek Hacim (Ortalamanın 2x üzerinde)"
        elif vol_ratio >= 1.5:
            vol_signal = "Yüksek Hacim (Ortalamanın üzerinde)"
        elif vol_ratio >= 0.8:
            vol_signal = "Normal Hacim"
        elif vol_ratio >= 0.5:
            vol_signal = "Düşük Hacim"
        else:
            vol_signal = "Çok Düşük Hacim"

        # ==================== Destek / Direnç ====================
        support_resistance = _calculate_support_resistance(high, low, close)

        # ==================== Fiyat Bilgileri ====================
        price_info = {
            "guncel_fiyat": round(current_price, 2),
            "onceki_kapanis": round(prev_close, 2),
            "degisim": round(price_change, 2),
            "degisim_yuzde": round(price_change_pct, 2),
            "gun_yuksek": round(float(high.iloc[-1]), 2),
            "gun_dusuk": round(float(low.iloc[-1]), 2),
            "acilis": round(float(open_price.iloc[-1]), 2),
            "yil_yuksek": round(float(high.max()), 2),
            "yil_dusuk": round(float(low.min()), 2),
        }

        return {
            "success": True,
            "symbol": symbol,
            "tarih": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "fiyat": price_info,
            "rsi": {
                "deger": round(rsi_value, 2),
                "sinyal": rsi_signal,
                "periyot": 14
            },
            "macd": {
                "macd": round(macd_val, 4),
                "sinyal": round(signal_val, 4),
                "histogram": round(hist_val, 4),
                "yorum": macd_signal
            },
            "bollinger": {
                "ust_bant": round(bb_upper_val, 2),
                "orta_bant": round(bb_middle_val, 2),
                "alt_bant": round(bb_lower_val, 2),
                "sinyal": bb_signal
            },
            "sma": {
                "sma_50": round(sma_50_val, 2) if sma_50_val else None,
                "sma_200": round(sma_200_val, 2) if sma_200_val else None,
                "sinyal": sma_cross_signal
            },
            "ema": {
                "ema_12": round(ema_12_val, 2) if ema_12_val else None,
                "ema_26": round(ema_26_val, 2) if ema_26_val else None,
                "sinyal": ema_signal
            },
            "stochastic": {
                "k": round(k_val, 2),
                "d": round(d_val, 2),
                "sinyal": stoch_signal
            },
            "adx": {
                "deger": round(adx_val, 2),
                "sinyal": adx_signal
            },
            "hacim": {
                "guncel": int(vol_current),
                "ortalama_20": int(vol_avg_20),
                "oran": round(vol_ratio, 2),
                "sinyal": vol_signal
            },
            "destek_direnc": support_resistance,
            "fibonacci": _calculate_fibonacci_levels(high, low, close),
            "atr": round(_calculate_atr(high, low, close), 2)
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"{symbol} analiz edilirken hata oluştu: {str(e)}",
            "symbol": symbol
        }
