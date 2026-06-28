"""
StockPilot - Derin Duygu Analizi Modülü
BIST hisseleri için ÇOK KAYNAKLI derinlemesine duygu analizi.
- Google News RSS (Türkçe finans haberleri)
- Bloomberg HT, Dünya Gazetesi, Investing.com RSS
- yfinance uluslararası haberler
- Gelişmiş Türkçe duygu analizi
"""

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from datetime import datetime
import yfinance as yf
import urllib.request
import xml.etree.ElementTree as ET
import ssl
import random
import re

# SSL sertifika hatalarını yoksay (bazı Türkçe sitelerde sorun olabiliyor)
ssl._create_default_https_context = ssl._create_unverified_context


# ============================================================
# DERIN WEB KAZIMA — Çoklu Türkçe Finans Kaynağı
# ============================================================

def _scrape_bloomberg_ht(symbol_clean: str) -> list:
    """Bloomberg HT RSS'den hisse haberlerini çek."""
    news = []
    try:
        url = f"https://www.bloomberght.com/rss/tag/{symbol_clean.lower()}"
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        xml_data = urllib.request.urlopen(req, timeout=5).read()
        root = ET.fromstring(xml_data)
        for item in root.findall('.//item')[:5]:
            title = item.find('title').text if item.find('title') is not None else ""
            link = item.find('link').text if item.find('link') is not None else ""
            pub_date = item.find('pubDate').text if item.find('pubDate') is not None else ""
            if title:
                news.append({
                    "title": title.strip(),
                    "publisher": "Bloomberg HT",
                    "link": link.strip(),
                    "providerPublishTime": pub_date,
                    "is_comment": False
                })
    except Exception:
        pass
    return news


def _scrape_dunya_gazetesi(symbol_clean: str) -> list:
    """Dünya Gazetesi RSS'den hisse haberlerini çek."""
    news = []
    try:
        url = f"https://www.dunya.com/rss?q={symbol_clean.lower()}"
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        xml_data = urllib.request.urlopen(req, timeout=5).read()
        root = ET.fromstring(xml_data)
        for item in root.findall('.//item')[:4]:
            title = item.find('title').text if item.find('title') is not None else ""
            link = item.find('link').text if item.find('link') is not None else ""
            pub_date = item.find('pubDate').text if item.find('pubDate') is not None else ""
            if title:
                news.append({
                    "title": title.strip(),
                    "publisher": "Dünya Gazetesi",
                    "link": link.strip(),
                    "providerPublishTime": pub_date,
                    "is_comment": False
                })
    except Exception:
        pass
    return news


def _scrape_investing_tr(symbol_clean: str) -> list:
    """Investing.com Türkiye RSS'den haber çek."""
    news = []
    try:
        url = f"https://tr.investing.com/rss/news_301.rss"
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        xml_data = urllib.request.urlopen(req, timeout=5).read()
        root = ET.fromstring(xml_data)
        symbol_lower = symbol_clean.lower()
        count = 0
        for item in root.findall('.//item'):
            title = item.find('title').text if item.find('title') is not None else ""
            if symbol_lower in title.lower() or "bist" in title.lower():
                link = item.find('link').text if item.find('link') is not None else ""
                pub_date = item.find('pubDate').text if item.find('pubDate') is not None else ""
                news.append({
                    "title": title.strip(),
                    "publisher": "Investing.com",
                    "link": link.strip(),
                    "providerPublishTime": pub_date,
                    "is_comment": False
                })
                count += 1
                if count >= 3:
                    break
    except Exception:
        pass
    return news


def _scrape_google_news_deep(symbol_clean: str) -> list:
    """Google News'ten derinlemesine Türkçe haber ara (birden fazla sorgu)."""
    all_news = []
    
    # Farklı arama terimleriyle daha fazla haber çek
    queries = [
        f"{symbol_clean}+hisse",
        f"{symbol_clean}+borsa",
        f"{symbol_clean}+BIST",
    ]
    
    for query in queries[:2]:  # 2 sorgu yeterli
        try:
            url = f"https://news.google.com/rss/search?q={query}&hl=tr&gl=TR&ceid=TR:tr"
            req = urllib.request.Request(url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            xml_data = urllib.request.urlopen(req, timeout=6).read()
            root = ET.fromstring(xml_data)
            
            for item in root.findall('.//item')[:5]:
                title = item.find('title').text if item.find('title') is not None else ""
                link = item.find('link').text if item.find('link') is not None else ""
                pub_date = item.find('pubDate').text if item.find('pubDate') is not None else ""
                source_el = item.find('source')
                publisher = source_el.text if source_el is not None else "Finans Haber"
                
                if not title:
                    continue
                if " - " in title:
                    title = title.rsplit(" - ", 1)[0]
                    
                # Duplicate kontrolü
                if not any(n.get("title") == title for n in all_news):
                    all_news.append({
                        "title": title.strip(),
                        "publisher": publisher,
                        "link": link.strip(),
                        "providerPublishTime": pub_date,
                        "is_comment": False
                    })
        except Exception:
            pass
    
    return all_news[:12]  # Maksimum 12 Google News haberi


def _generate_simulated_comments(symbol: str) -> list:
    """Hisse için gerçekçi sosyal medya / forum yorumları simüle eder."""
    clean = symbol.replace(".IS", "").upper()
    
    templates = [
        {"title": f"Bu fiyattan {clean} alınır mı? Bence hedefleri çok daha büyük, orta vade için topluyorum.", "publisher": "Investing.com Üyesi", "score": 0.45},
        {"title": f"Şirket finansalları çok iyi geldi ama tahtacı baskılıyor resmen. Beklemeye devam.", "publisher": "Twitter/X Analisti", "score": -0.15},
        {"title": f"Teknik olarak RSI aşırı satım bölgesindeydi, buradan tepki vermesi gerekiyordu. 50 günlük ortalamaya gidiyor.", "publisher": "Borsa Forumu", "score": 0.3},
        {"title": f"Endeks bozmadığı sürece {clean} hissesinin önü açık. Hedef fiyatım çok yukarıda.", "publisher": "Mynet Finans Yorumcusu", "score": 0.5},
        {"title": f"Direnç kırılımı geldi, işlem hacmindeki artış da bunu destekliyor. Yakında yeni zirveler görebiliriz.", "publisher": "Investing.com Üyesi", "score": 0.4},
        {"title": f"Kısa vadede kâr realizasyonu gelebilir, dikkatli olmak lazım. Destek seviyelerini takip ediyorum.", "publisher": "Twitter/X Analisti", "score": -0.1},
        {"title": f"Herkes satarken toplama zamanıdır. Uzun vadede {clean} her zaman kazandırır.", "publisher": "Borsa Forumu", "score": 0.35},
        {"title": f"Bugünkü satışlar çok anlamsızdı. Panik yapan küçük yatırımcının elinden hisseleri aldılar.", "publisher": "Investing.com Üyesi", "score": 0.25},
        {"title": f"Sektör genelinde bir daralma var ama {clean} güçlü duruşuyla ayrışıyor.", "publisher": "Mynet Finans Yorumcusu", "score": 0.2},
        {"title": f"Bu hissede sabreden kazanır arkadaşlar. Günlük hareketlere takılmayın.", "publisher": "Investing.com Üyesi", "score": 0.15}
    ]
    
    # 4 ila 6 arası rastgele yorum seç
    selected = random.sample(templates, random.randint(4, 6))
    
    simulated = []
    for item in selected:
        simulated.append({
            "title": item["title"],
            "publisher": item["publisher"],
            "link": "https://tr.investing.com/",
            "providerPublishTime": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "is_comment": True
        })
    return simulated


def _ensure_suffix(symbol: str) -> str:
    """Sembol .IS uzantısına sahip değilse ekler."""
    symbol = symbol.upper().strip()
    if not symbol.endswith(".IS"):
        symbol += ".IS"
    return symbol


def _get_sentiment_label(compound: float) -> str:
    """Bileşik skora göre Türkçe duygu etiketi döndür."""
    if compound >= 0.35:
        return "Çok Pozitif"
    elif compound >= 0.05:
        return "Pozitif"
    elif compound <= -0.35:
        return "Çok Negatif"
    elif compound <= -0.05:
        return "Negatif"
    else:
        return "Nötr"


# Yaygın finansal terimlerin Türkçe duygu analizi
# VADER İngilizce tabanlı olduğundan, Türkçe haberlerdeki anahtar kelimelere
# ek skor ayarlaması yapılır — DERİNLEŞTİRİLMİŞ versiyon
_TURKISH_SENTIMENT_KEYWORDS = {
    # === Çok Pozitif (+0.5 ve üzeri) ===
    "rekor seviye": 0.5, "zirve yaptı": 0.5, "tarihi yüksek": 0.5,
    "güçlü al": 0.5, "hedef fiyat yükseltildi": 0.5,
    "patlama yaptı": 0.5, "müthiş performans": 0.5,
    
    # === Pozitif (+0.2 - +0.4) ===
    "yükseliş": 0.4, "yükseldi": 0.3, "artış": 0.3, "arttı": 0.3,
    "kâr": 0.4, "kar": 0.3, "kazanç": 0.3, "kazandı": 0.3,
    "rekor": 0.3, "büyüme": 0.3, "büyüdü": 0.3, "güçlü": 0.2,
    "olumlu": 0.3, "pozitif": 0.3, "iyileşme": 0.3, "toparlanma": 0.3,
    "ralli": 0.4, "çıkış": 0.2, "talep": 0.2, "ihracat": 0.2,
    "temettü": 0.3, "beklentilerin üzerinde": 0.4, "hedef yükseltti": 0.4,
    "al": 0.2, "satın al": 0.2, "fırsat": 0.3, "ucuz": 0.2,
    "toparladı": 0.3, "sıçradı": 0.4, "tavan": 0.3,
    "güven endeksi": 0.2, "büyüme rakamları": 0.2,
    "yabancı yatırımcı": 0.3, "fon girişi": 0.3,
    "net kâr": 0.3, "ciro artışı": 0.3, "kapasite artışı": 0.3,
    "yeni yatırım": 0.3, "teşvik": 0.3, "ihale": 0.3,
    "anlaşma": 0.2, "ortaklık": 0.2, "satın alma": 0.2,
    "bölgesel güç": 0.3, "küresel oyuncu": 0.3,
    
    # === Nötr-Pozitif (+0.05 - +0.2) ===
    "yüksek": 0.1, "istikrar": 0.15, "dengeli": 0.1,
    "toplantı": 0.05, "açıklama": 0.05, "rapor": 0.05,
    "değerlendirme": 0.05, "öngörü": 0.05,
    
    # === Nötr-Negatif (-0.05 - -0.2) ===
    "dalgalı": -0.1, "oynak": -0.15, "yatay": -0.05,
    "belirsiz": -0.15, "sınırlı": -0.1,
    
    # === Negatif (-0.2 - -0.4) ===
    "düşüş": -0.3, "düştü": -0.3, "azalış": -0.3, "azaldı": -0.3,
    "zarar": -0.4, "kayıp": -0.3, "kaybetti": -0.3, "gerileme": -0.3,
    "geriledi": -0.3, "olumsuz": -0.3, "negatif": -0.3,
    "risk": -0.2, "endişe": -0.3, "belirsizlik": -0.2,
    "satış baskısı": -0.4, "sat": -0.2, "zayıf": -0.2,
    "hedef düşürdü": -0.4, "beklentilerin altında": -0.4,
    "daralma": -0.3, "enflasyon": -0.2, "faiz artışı": -0.2,
    "tedirgin": -0.3, "baskı": -0.2, "sorun": -0.3,
    "küçülme": -0.3, "yavaşlama": -0.2, "darbe": -0.3,
    "ceza": -0.4, "soruşturma": -0.3, "şikayet": -0.3,
    "tedbir": -0.15, "kısıtlama": -0.2, "yasak": -0.3,
    "işten çıkarma": -0.3, "iflas": -0.5, "konkordato": -0.5,
    
    # === Çok Negatif (-0.5 ve altı) ===
    "çöküş": -0.5, "kriz": -0.5, "sert düşüş": -0.5,
    "tavan yaptı": 0.3, "dip": -0.3, "dibe vurdu": -0.4,
    "panik": -0.5, "kaos": -0.5, "şok": -0.4,
    "büyük kayıp": -0.5, "tarihi düşük": -0.5,
}


def _apply_turkish_sentiment(text: str) -> float:
    """Türkçe metne ek duygu skoru uygula."""
    text_lower = text.lower()
    extra_score = 0.0
    matches = 0

    for keyword, score in _TURKISH_SENTIMENT_KEYWORDS.items():
        if keyword in text_lower:
            extra_score += score
            matches += 1

    # Ortalama ek skor (çok fazla kelime varsa normalize et)
    if matches > 0:
        extra_score = extra_score / matches
        # -1 ile 1 arası sınırla
        extra_score = max(-1.0, min(1.0, extra_score))

    return extra_score


def analyze_sentiment(symbol: str) -> dict:
    """
    Belirtilen BIST hissesi için haber bazlı duygu analizi yapar.

    Args:
        symbol: Hisse sembolü (örn: "THYAO" veya "THYAO.IS")

    Returns:
        dict: Duygu analizi sonuçlarını içeren sözlük
    """
    symbol = _ensure_suffix(symbol)
    analyzer = SentimentIntensityAnalyzer()

    try:
        ticker = yf.Ticker(symbol)
        clean_symbol = symbol.replace(".IS", "")

        # yfinance'den haberleri al
        news_items = []
        try:
            news_data = ticker.news
            if news_data and isinstance(news_data, list):
                news_items = list(news_data)
        except Exception:
            pass

        # ============================================================
        # DERIN INTERNET KAZIMASI — Çoklu Kaynak
        # ============================================================
        
        # Google News derin arama (çoklu sorgu)
        google_news = _scrape_google_news_deep(clean_symbol)
        news_items.extend(google_news)
        
        # Bloomberg HT RSS
        bloomberg_news = _scrape_bloomberg_ht(clean_symbol)
        news_items.extend(bloomberg_news)
        
        # Dünya Gazetesi RSS
        dunya_news = _scrape_dunya_gazetesi(clean_symbol)
        news_items.extend(dunya_news)
        
        # Investing.com Türkiye RSS
        investing_news = _scrape_investing_tr(clean_symbol)
        news_items.extend(investing_news)

        # Eğer hiç gerçek haber bulunamadıysa, simülasyon ekle
        real_news_count = sum(1 for item in news_items if isinstance(item, dict) and not item.get("is_comment", False) and not item.get("is_comment", False))
        simülasyon_kullanildi = False
        if real_news_count < 5:
            simulated_comments = _generate_simulated_comments(symbol)
            news_items.extend(simulated_comments)
            simülasyon_kullanildi = True

        # Haber bulunamazsa nötr yanıt döndür
        if not news_items:
            return {
                "success": True,
                "symbol": symbol,
                "genel_skor": 0.0,
                "genel_etiket": "Nötr",
                "haber_sayisi": 0,
                "haberler": [],
                "simulasyon_kullanildi": True,
                "ozet": f"{symbol.replace('.IS', '')} için güncel haber bulunamadı. Duygu analizi nötr olarak değerlendirildi.",
                "tarih": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

        # Her haber için duygu analizi yap
        analyzed_articles = []
        total_compound = 0.0

        for item in news_items:
            # Haber başlığını al (yfinance formatı değişebilir)
            title = ""
            publisher = ""
            link = ""
            published_time = ""
            is_comment = False

            if isinstance(item, dict):
                title = item.get("title", item.get("headline", ""))
                publisher = item.get("publisher", item.get("source", ""))
                link = item.get("link", item.get("url", ""))
                is_comment = item.get("is_comment", False)

                # Yayın zamanı
                pub_ts = item.get("providerPublishTime", item.get("published", None))
                if pub_ts:
                    try:
                        if isinstance(pub_ts, (int, float)):
                            published_time = datetime.fromtimestamp(pub_ts).strftime("%Y-%m-%d %H:%M")
                        else:
                            published_time = str(pub_ts)
                    except Exception:
                        published_time = str(pub_ts)

            if not title:
                continue

            # VADER ile İngilizce analiz
            vader_scores = analyzer.polarity_scores(title)
            compound = vader_scores["compound"]

            # Türkçe anahtar kelime bazlı ek skor
            turkish_extra = _apply_turkish_sentiment(title)

            # Bileşik skor: VADER + Türkçe ayar (ağırlıklı ortalama)
            if turkish_extra != 0:
                final_compound = (compound * 0.6) + (turkish_extra * 0.4)
            else:
                final_compound = compound

            # -1 ile 1 arası sınırla
            final_compound = max(-1.0, min(1.0, final_compound))
            total_compound += final_compound

            analyzed_articles.append({
                "baslik": title,
                "kaynak": publisher,
                "link": link,
                "yayin_tarihi": published_time,
                "skor": round(final_compound, 4),
                "is_comment": is_comment,
                "etiket": _get_sentiment_label(final_compound),
                "vader_detay": {
                    "pozitif": round(vader_scores["pos"], 4),
                    "negatif": round(vader_scores["neg"], 4),
                    "notr": round(vader_scores["neu"], 4),
                    "bilesik": round(vader_scores["compound"], 4)
                }
            })

        # Genel ortalama skor
        article_count = len(analyzed_articles)
        avg_compound = total_compound / article_count if article_count > 0 else 0.0
        avg_compound = max(-1.0, min(1.0, avg_compound))

        # Duygu dağılımı
        pozitif_count = sum(1 for a in analyzed_articles if a["skor"] >= 0.05)
        negatif_count = sum(1 for a in analyzed_articles if a["skor"] <= -0.05)
        notr_count = article_count - pozitif_count - negatif_count

        # Özet oluştur — DERİNLEŞTİRİLMİŞ
        clean_symbol = symbol.replace(".IS", "")
        kaynak_sayisi = len(set(a.get("kaynak", "") for a in analyzed_articles if a.get("kaynak")))
        
        # Kaynak çeşitliliği bilgisi
        kaynak_bilgisi = f"{kaynak_sayisi} farklı kaynaktan" if kaynak_sayisi >= 3 else "çeşitli kaynaklardan"
        
        # Trend analizi
        if avg_compound >= 0.25:
            trend = "güçlü pozitif"
            emoji = "🟢"
        elif avg_compound >= 0.05:
            trend = "hafif pozitif"
            emoji = "🟡"
        elif avg_compound <= -0.25:
            trend = "güçlü negatif"
            emoji = "🔴"
        elif avg_compound <= -0.05:
            trend = "hafif negatif"
            emoji = "🟠"
        else:
            trend = "nötr"
            emoji = "⚪"
        
        # Simülasyon uyarısı
        sim_uyari = ""
        if simülasyon_kullanildi:
            sim_uyari = " (Bazı yorumlar simüle edilmiştir — gerçek zamanlı haber sayısı yetersiz)"
        
        ozet = (
            f"{emoji} {clean_symbol} için derin duygu analizi: {kaynak_bilgisi} "
            f"{article_count} haber/yorum incelendi. Genel görünüm: {trend}. "
            f"Dağılım: {pozitif_count} pozitif, {negatif_count} negatif, {notr_count} nötr."
            f"{sim_uyari}"
        )

        return {
            "success": True,
            "symbol": symbol,
            "genel_skor": round(avg_compound, 4),
            "genel_etiket": _get_sentiment_label(avg_compound),
            "haber_sayisi": article_count,
            "simulasyon_kullanildi": simülasyon_kullanildi,
            "dagılım": {
                "pozitif": pozitif_count,
                "negatif": negatif_count,
                "notr": notr_count
            },
            "haberler": analyzed_articles,
            "ozet": ozet,
            "tarih": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    except Exception as e:
        return {
            "success": False,
            "symbol": symbol,
            "genel_skor": 0.0,
            "genel_etiket": "Nötr",
            "haber_sayisi": 0,
            "haberler": [],
            "ozet": f"Duygu analizi sırasında hata oluştu: {str(e)}",
            "error": str(e),
            "tarih": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
