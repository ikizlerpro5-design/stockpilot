"""
StockPilot - Öneri Motoru V2.0
Teknik analiz ve duygu analizi sonuçlarını birleştirerek
AL/SAT/TUT önerisi ve spesifik fiyat hedefleri üretir.
"""

from datetime import datetime


def calculate_price_targets(technical: dict, action: str, score: float) -> dict:
    """
    Teknik verilere göre spesifik giriş/çıkış/stop-loss fiyat hedefleri hesaplar.

    Kullanılan yöntemler:
    - Pivot noktaları (S1/S2/R1/R2)
    - Fibonacci retracement seviyeleri
    - ATR bazlı stop-loss mesafesi
    - Destek/direnç seviyeleri
    """
    price_data = technical.get("fiyat", {})
    current_price = price_data.get("guncel_fiyat", 0)
    if current_price <= 0:
        return {"basarili": False, "neden": "Fiyat verisi mevcut değil"}

    sr_data = technical.get("destek_direnc", {})
    fib_data = technical.get("fibonacci", {})
    atr_value = technical.get("atr", 0)

    # ATR yoksa fiyatın %2'sini varsayılan volatilite olarak kullan
    if atr_value <= 0:
        atr_value = current_price * 0.02

    # Pivot seviyeleri
    pivot = sr_data.get("pivot", current_price)
    pivot_s1 = sr_data.get("pivot_destek_1", current_price * 0.97)
    pivot_s2 = sr_data.get("pivot_destek_2", current_price * 0.94)
    pivot_r1 = sr_data.get("pivot_direnc_1", current_price * 1.03)
    pivot_r2 = sr_data.get("pivot_direnc_2", current_price * 1.06)

    # Destek/direnç seviyeleri
    support_1 = sr_data.get("destek_1", current_price * 0.95)
    support_2 = sr_data.get("destek_2", current_price * 0.90)
    resistance_1 = sr_data.get("direnc_1", current_price * 1.05)
    resistance_2 = sr_data.get("direnc_2", current_price * 1.10)

    # Fibonacci seviyeleri
    fib_0382 = fib_data.get("seviye_0382", current_price)
    fib_0500 = fib_data.get("seviye_0500", current_price)
    fib_0618 = fib_data.get("seviye_0618", current_price)
    swing_high = fib_data.get("swing_yuksek", resistance_1)
    swing_low = fib_data.get("swing_dusuk", support_1)

    if action == "AL":
        # Giriş: Mevcut fiyat civarı veya pivot S1'e yakın (düşüş beklentisi ile)
        # Eğer fiyat pivot altındaysa direkt giriş, üzerindeyse biraz geri çekilme bekle
        if current_price <= pivot:
            giris = round(current_price, 2)
        else:
            # Pivot ile mevcut fiyat arasında optimum giriş
            giris = round(max(pivot, current_price - atr_value * 0.5), 2)

        # Hedef 1 (Kısa vadeli): Pivot R1 veya en yakın direnç
        hedef_1 = round(max(pivot_r1, current_price * 1.03), 2)
        # Hedef 2 (Orta vadeli): Pivot R2 veya üst direnç veya swing yüksek
        hedef_2 = round(max(pivot_r2, resistance_1, swing_high * 0.98), 2)
        # Stop Loss: ATR bazlı — 1.5x ATR altı veya Pivot S1
        stop_loss = round(min(pivot_s1, current_price - atr_value * 1.5), 2)
        # Stop Loss'un fiyattan en az %1.5 altında olmasını garanti et
        min_sl = round(current_price * 0.985, 2)
        stop_loss = min(stop_loss, min_sl)

    elif action == "SAT":
        # SAT sinyalinde giriş = mevcut fiyat (satış pozisyonu)
        giris = round(current_price, 2)
        # Hedef 1: Pivot S1'e kadar düşüş
        hedef_1 = round(min(pivot_s1, current_price * 0.97), 2)
        # Hedef 2: Pivot S2 veya destek seviyesine kadar düşüş
        hedef_2 = round(min(pivot_s2, support_1, swing_low * 1.02), 2)
        # Stop Loss: Pivot R1 üzeri (fiyat yükselirse kayıp sınırla)
        stop_loss = round(max(pivot_r1, current_price + atr_value * 1.5), 2)
        # SL fiyattan en az %1.5 yukarıda olsun
        min_sl_up = round(current_price * 1.015, 2)
        stop_loss = max(stop_loss, min_sl_up)

    else:  # TUT
        giris = round(current_price, 2)
        hedef_1 = round(pivot_r1, 2)
        hedef_2 = round(resistance_1, 2)
        stop_loss = round(max(pivot_s1, current_price - atr_value * 1.5), 2)

    # Risk/Ödül oranı hesapla
    if action == "SAT":
        risk = abs(stop_loss - giris)
        reward = abs(giris - hedef_1)
    else:
        risk = abs(giris - stop_loss)
        reward = abs(hedef_1 - giris)

    risk_reward = round(reward / risk, 2) if risk > 0 else 0

    # Kar potansiyeli yüzdeleri
    kar_pot_1 = round(((hedef_1 - giris) / giris) * 100, 2) if giris > 0 else 0
    kar_pot_2 = round(((hedef_2 - giris) / giris) * 100, 2) if giris > 0 else 0
    zarar_pot = round(((stop_loss - giris) / giris) * 100, 2) if giris > 0 else 0

    return {
        "basarili": True,
        "giris_fiyati": giris,
        "hedef_1": hedef_1,
        "hedef_1_kar_yuzde": kar_pot_1,
        "hedef_2": hedef_2,
        "hedef_2_kar_yuzde": kar_pot_2,
        "stop_loss": stop_loss,
        "zarar_yuzde": zarar_pot,
        "risk_odul_orani": risk_reward,
        "atr": round(atr_value, 2),
        "fibonacci": {
            "0.236": fib_data.get("seviye_0236", 0),
            "0.382": fib_0382,
            "0.500": fib_0500,
            "0.618": fib_0618,
            "0.786": fib_data.get("seviye_0786", 0),
            "swing_yuksek": swing_high,
            "swing_dusuk": swing_low,
            "bolge": fib_data.get("bolge", ""),
            "trend_yonu": fib_data.get("trend_yonu", "Belirsiz")
        },
        "pivot_seviyeleri": {
            "pivot": pivot,
            "s1": pivot_s1,
            "s2": pivot_s2,
            "r1": pivot_r1,
            "r2": pivot_r2
        }
    }


def generate_recommendation(symbol: str, technical: dict, sentiment: dict) -> dict:
    """
    Teknik analiz ve duygu analizi sonuçlarını birleştirerek yatırım önerisi üretir.

    Args:
        symbol: Hisse sembolü
        technical: Teknik analiz sonuçları (technical_analysis.analyze çıktısı)
        sentiment: Duygu analizi sonuçları (sentiment_analysis.analyze_sentiment çıktısı)

    Returns:
        dict: Öneri, güven skoru, nedenler ve risk seviyesi
    """
    if not technical.get("success", False):
        return {
            "success": False,
            "symbol": symbol,
            "error": technical.get("error", "Teknik analiz başarısız oldu."),
            "aksiyon": "TUT",
            "guven": 0,
            "skor": 50,
            "nedenler_al": [],
            "nedenler_sat": [],
            "risk_seviyesi": "Yüksek",
            "tarih": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    buy_points = 0
    sell_points = 0
    reasons_buy = []
    reasons_sell = []

    current_price = technical.get("fiyat", {}).get("guncel_fiyat", 0)

    # ==================== RSI Analizi ====================
    rsi_data = technical.get("rsi", {})
    rsi_value = rsi_data.get("deger", 50)

    if rsi_value < 30:
        buy_points += 15
        reasons_buy.append(f"RSI ({rsi_value:.1f}) aşırı satım bölgesinde — geri dönüş potansiyeli yüksek")
    elif rsi_value < 40:
        buy_points += 7
        reasons_buy.append(f"RSI ({rsi_value:.1f}) düşük seviyede — alım fırsatı olabilir")
    elif rsi_value > 70:
        sell_points += 15
        reasons_sell.append(f"RSI ({rsi_value:.1f}) aşırı alım bölgesinde — düzeltme riski var")
    elif rsi_value > 60:
        sell_points += 5
        reasons_sell.append(f"RSI ({rsi_value:.1f}) yüksek seviyede — dikkatli olunmalı")

    # ==================== MACD Analizi ====================
    macd_data = technical.get("macd", {})
    macd_signal = macd_data.get("yorum", "Nötr")
    macd_histogram = macd_data.get("histogram", 0)

    if macd_signal == "AL":
        buy_points += 15
        reasons_buy.append("MACD yükseliş kesişimi (bullish crossover) gerçekleşti")
    elif macd_signal == "SAT":
        sell_points += 15
        reasons_sell.append("MACD düşüş kesişimi (bearish crossover) gerçekleşti")
    else:
        if macd_histogram > 0:
            buy_points += 5
            reasons_buy.append("MACD histogram pozitif bölgede")
        elif macd_histogram < 0:
            sell_points += 5
            reasons_sell.append("MACD histogram negatif bölgede")

    # ==================== SMA 50/200 Analizi ====================
    sma_data = technical.get("sma", {})
    sma_50 = sma_data.get("sma_50")
    sma_200 = sma_data.get("sma_200")
    sma_signal = sma_data.get("sinyal", "")

    if sma_200 is not None and current_price > 0:
        if current_price > sma_200:
            buy_points += 10
            reasons_buy.append(f"Fiyat ({current_price:.2f}) 200 günlük ortalamanın ({sma_200:.2f}) üzerinde — uzun vadeli yükseliş trendi")
        else:
            sell_points += 10
            reasons_sell.append(f"Fiyat ({current_price:.2f}) 200 günlük ortalamanın ({sma_200:.2f}) altında — uzun vadeli düşüş trendi")

    if sma_50 is not None and current_price > 0:
        if current_price > sma_50:
            buy_points += 5
            reasons_buy.append(f"Fiyat 50 günlük ortalamanın ({sma_50:.2f}) üzerinde — kısa vadeli yükseliş")
        else:
            sell_points += 5
            reasons_sell.append(f"Fiyat 50 günlük ortalamanın ({sma_50:.2f}) altında — kısa vadeli düşüş")

    # Golden Cross / Death Cross
    if "Golden Cross" in sma_signal or "Altın Kesişim" in sma_signal:
        buy_points += 10
        reasons_buy.append("Golden Cross (Altın Kesişim) oluştu — güçlü alım sinyali")
    elif "Death Cross" in sma_signal or "Ölüm Kesişimi" in sma_signal:
        sell_points += 10
        reasons_sell.append("Death Cross (Ölüm Kesişimi) oluştu — güçlü satış sinyali")

    # ==================== Bollinger Bantları ====================
    bb_data = technical.get("bollinger", {})
    bb_signal = bb_data.get("sinyal", "")
    bb_lower = bb_data.get("alt_bant", 0)
    bb_upper = bb_data.get("ust_bant", 0)

    if "Alt Bant" in bb_signal or "Aşırı Satım" in bb_signal:
        if "Aşırı Satım" in bb_signal:
            buy_points += 10
            reasons_buy.append(f"Fiyat Bollinger alt bandının ({bb_lower:.2f}) altında — aşırı satım, geri dönüş beklenir")
        else:
            buy_points += 7
            reasons_buy.append(f"Fiyat Bollinger alt bandına ({bb_lower:.2f}) yakın — alım fırsatı")
    elif "Üst Bant" in bb_signal or "Aşırı Alım" in bb_signal:
        if "Aşırı Alım" in bb_signal:
            sell_points += 10
            reasons_sell.append(f"Fiyat Bollinger üst bandının ({bb_upper:.2f}) üzerinde — aşırı alım, düzeltme beklenir")
        else:
            sell_points += 7
            reasons_sell.append(f"Fiyat Bollinger üst bandına ({bb_upper:.2f}) yakın — dikkatli olunmalı")

    # ==================== Stochastic Oscillator ====================
    stoch_data = technical.get("stochastic", {})
    stoch_signal = stoch_data.get("sinyal", "Nötr")
    stoch_k = stoch_data.get("k", 50)

    if stoch_signal == "Aşırı Satım":
        buy_points += 7
        reasons_buy.append(f"Stochastic (%K: {stoch_k:.1f}) aşırı satım bölgesinde")
    elif stoch_signal == "Aşırı Alım":
        sell_points += 7
        reasons_sell.append(f"Stochastic (%K: {stoch_k:.1f}) aşırı alım bölgesinde")
    elif stoch_signal == "Yükseliş Sinyali":
        buy_points += 3
    elif stoch_signal == "Düşüş Sinyali":
        sell_points += 3

    # ==================== ADX Analizi ====================
    adx_data = technical.get("adx", {})
    adx_value = adx_data.get("deger", 0)
    adx_signal = adx_data.get("sinyal", "")

    # ADX güçlü trend gösteriyorsa mevcut sinyalleri güçlendir
    trend_multiplier = 1.0
    if adx_value > 25:
        trend_multiplier = 1.2
        if adx_value > 40:
            trend_multiplier = 1.3

    # ==================== Duygu Analizi ====================
    sentiment_score = sentiment.get("genel_skor", 0)
    sentiment_label = sentiment.get("genel_etiket", "Nötr")

    if sentiment_score >= 0.05:
        sentiment_points = min(int(sentiment_score * 20), 10)
        buy_points += sentiment_points
        reasons_buy.append(f"Haber duygu analizi pozitif ({sentiment_label}, skor: {sentiment_score:.2f})")
    elif sentiment_score <= -0.05:
        sentiment_points = min(int(abs(sentiment_score) * 20), 10)
        sell_points += sentiment_points
        reasons_sell.append(f"Haber duygu analizi negatif ({sentiment_label}, skor: {sentiment_score:.2f})")

    # ==================== Hacim Analizi ====================
    vol_data = technical.get("hacim", {})
    vol_ratio = vol_data.get("oran", 1.0)

    if vol_ratio > 1.2:
        # Yüksek hacim mevcut trendi doğrular
        if buy_points > sell_points:
            buy_points += 5
            reasons_buy.append(f"Hacim ortalamanın {vol_ratio:.1f}x üzerinde — yükseliş trendi destekleniyor")
        elif sell_points > buy_points:
            sell_points += 5
            reasons_sell.append(f"Hacim ortalamanın {vol_ratio:.1f}x üzerinde — düşüş trendi destekleniyor")

    # ==================== ADX ile Sinyal Güçlendirme ====================
    if trend_multiplier > 1.0 and adx_value > 25:
        if buy_points > sell_points:
            buy_points = int(buy_points * trend_multiplier)
            reasons_buy.append(f"ADX ({adx_value:.1f}) güçlü trend gösteriyor — sinyaller güçlendirildi")
        elif sell_points > buy_points:
            sell_points = int(sell_points * trend_multiplier)
            reasons_sell.append(f"ADX ({adx_value:.1f}) güçlü trend gösteriyor — sinyaller güçlendirildi")

    # ==================== Skor Hesaplama ====================
    total_points = buy_points + sell_points
    if total_points == 0:
        score = 50
    else:
        # Skor: 0 (güçlü sat) - 50 (nötr) - 100 (güçlü al)
        score = 50 + ((buy_points - sell_points) / max(total_points, 1)) * 50

    score = max(0, min(100, score))

    # ==================== Aksiyon Belirleme ====================
    if score >= 65:
        action = "AL"
    elif score <= 35:
        action = "SAT"
    else:
        action = "TUT"

    # ==================== Güven Skoru ====================
    # Güven: ne kadar çok sinyal aynı yönü gösteriyorsa güven o kadar yüksek
    signal_agreement = abs(buy_points - sell_points)
    confidence = min(100, int((signal_agreement / max(total_points, 1)) * 100))

    # Minimum güven seviyesi
    if total_points < 10:
        confidence = max(confidence - 20, 10)

    confidence = max(10, min(100, confidence))

    # ==================== Risk Seviyesi ====================
    risk_factors = 0

    # Volatilite (Bollinger bant genişliği)
    bb_upper_val = bb_data.get("ust_bant", 0)
    bb_lower_val = bb_data.get("alt_bant", 0)
    bb_middle_val = bb_data.get("orta_bant", 1)
    if bb_middle_val > 0:
        band_width_pct = ((bb_upper_val - bb_lower_val) / bb_middle_val) * 100
        if band_width_pct > 15:
            risk_factors += 2
        elif band_width_pct > 10:
            risk_factors += 1

    # ADX zayıf trend = daha riskli
    if adx_value < 20:
        risk_factors += 1

    # RSI aşırı bölgelerde = daha riskli
    if rsi_value > 75 or rsi_value < 25:
        risk_factors += 1

    # Hacim düşük = daha riskli
    if vol_ratio < 0.5:
        risk_factors += 1

    # Düşük güven = daha riskli
    if confidence < 40:
        risk_factors += 1

    if risk_factors >= 4:
        risk_level = "Yüksek"
    elif risk_factors >= 2:
        risk_level = "Orta"
    else:
        risk_level = "Düşük"

    # ==================== Fiyat Hedefleri ====================
    price_targets = calculate_price_targets(technical, action, score)

    # ==================== Özet Oluştur ====================
    clean_symbol = symbol.replace(".IS", "") if ".IS" in symbol else symbol
    price_info = technical.get("fiyat", {})
    change_pct = price_info.get("degisim_yuzde", 0)
    current_price = price_info.get("guncel_fiyat", 0)

    if action == "AL" and price_targets.get("basarili"):
        pt = price_targets
        ozet = (
            f"{clean_symbol} hissesi için teknik göstergeler ve piyasa duyarlılığı "
            f"alım yönünde sinyal veriyor. "
            f"Giriş: ₺{pt['giris_fiyati']}, Hedef: ₺{pt['hedef_1']} (%{pt['hedef_1_kar_yuzde']:+.1f}), "
            f"Stop Loss: ₺{pt['stop_loss']}. "
            f"Risk/Ödül: {pt['risk_odul_orani']}x. "
            f"Güven: %{confidence}, Risk: {risk_level}."
        )
    elif action == "SAT" and price_targets.get("basarili"):
        pt = price_targets
        ozet = (
            f"{clean_symbol} hissesi için teknik göstergeler ve piyasa duyarlılığı "
            f"satış yönünde sinyal veriyor. "
            f"Mevcut: ₺{current_price}, Hedef: ₺{pt['hedef_1']} (%{pt['hedef_1_kar_yuzde']:+.1f}), "
            f"Stop Loss: ₺{pt['stop_loss']}. "
            f"Risk/Ödül: {pt['risk_odul_orani']}x. "
            f"Güven: %{confidence}, Risk: {risk_level}."
        )
    else:
        ozet = (
            f"{clean_symbol} hissesi için teknik göstergeler karışık sinyal veriyor. "
            f"Pozisyon tutmak veya beklemek önerilir. Güven skoru: %{confidence}. "
            f"Risk seviyesi: {risk_level}."
        )

    return {
        "success": True,
        "symbol": symbol,
        "sembol_kisa": clean_symbol,
        "aksiyon": action,
        "guven": confidence,
        "skor": round(score, 1),
        "nedenler_al": reasons_buy,
        "nedenler_sat": reasons_sell,
        "risk_seviyesi": risk_level,
        "puan_detay": {
            "al_puani": buy_points,
            "sat_puani": sell_points,
            "toplam": total_points
        },
        "fiyat_hedefleri": price_targets,
        "ozet": ozet,
        "tarih": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "uyari": "Bu analiz yatırım tavsiyesi niteliği taşımaz. Yatırım kararlarınızı kendi araştırmanıza dayanarak verin."
    }

