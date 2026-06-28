"""StockPilot V4 — Premium Siyah Arayuz, Ust Navigasyon"""
html = '''<!DOCTYPE html>
<html lang="tr">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>StockPilot — BIST Analiz Platformu</title>
<script>window.onerror=function(m,u,l,c,e){fetch('/api/log_error',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({type:'window.onerror',message:m,url:u,line:l,col:c,stack:e?e.stack:'none'})})};window.onunhandledrejection=function(e){fetch('/api/log_error',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({type:'unhandledrejection',message:e.reason?e.reason.toString():'none',stack:e.reason&&e.reason.stack?e.reason.stack:'none'})})}</script>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Playfair+Display:wght@500;600;700&display=swap" rel="stylesheet">
<script src="https://unpkg.com/lightweight-charts@4.2.1/dist/lightweight-charts.standalone.production.js"></script>
<link rel="stylesheet" href="css/style.css?v=4.0.0">
</head>
<body class="dark-default">

<!-- ====== UST BAR ====== -->
<header class="sp-topbar">
  <div class="sp-brand" onclick="window.StockPilot.navigate('dashboard')">
    <div class="sp-logo-diamond">&#9670;</div>
    <div class="sp-brand-text">
      <span class="sp-brand-name">StockPilot</span>
      <span class="sp-brand-sub">BORSA ISTANBUL</span>
    </div>
  </div>

  <div class="sp-search-wrapper">
    <svg class="sp-search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
    <input type="text" id="searchInput" class="sp-search-input" placeholder="Hisse kodu yazin... (THYAO, ASELS, GARAN)" autocomplete="off">
    <div class="search-dropdown" id="searchDropdown"></div>
  </div>

  <div class="sp-market-ticker">
    <div class="sp-ticker-item">
      <span class="sp-ticker-label">BIST 100</span>
      <span class="sp-ticker-value" id="bistValue">—</span>
      <span class="sp-ticker-change" id="bistChange">—</span>
    </div>
    <div class="sp-ticker-divider"></div>
    <div class="sp-ticker-item">
      <span class="sp-ticker-label">USD/TRY</span>
      <span class="sp-ticker-value" id="usdValue">—</span>
      <span class="sp-ticker-change" id="usdChange">—</span>
    </div>
    <div class="sp-ticker-divider"></div>
    <div class="sp-ticker-item">
      <span class="sp-ticker-label">ALTIN</span>
      <span class="sp-ticker-value" id="goldValue">—</span>
      <span class="sp-ticker-change" id="goldChange">—</span>
    </div>
  </div>

  <div class="sp-topbar-right">
    <span class="sp-clock" id="timeDisplay"></span>
    <button class="sp-theme-btn" onclick="window.StockPilot.toggleTheme()" title="Tema Degistir">&#9680;</button>
  </div>
</header>

<!-- ====== NAVIGASYON ====== -->
<nav class="sp-navbar">
  <div class="sp-nav-inner">
    <a class="sp-nav-link active" data-page="dashboard" onclick="window.StockPilot.navigate('dashboard')">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/></svg>
      <span>Panel</span>
    </a>
    <a class="sp-nav-link" data-page="analysis" onclick="window.StockPilot.navigate('analysis')">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
      <span>Analiz</span>
    </a>
    <a class="sp-nav-link" data-page="compare" onclick="window.StockPilot.navigate('compare')">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>
      <span>Karsilastir</span>
    </a>
    <a class="sp-nav-link" data-page="daily" onclick="window.StockPilot.navigate('daily')">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
      <span>Gunluk</span>
    </a>
    <a class="sp-nav-link" data-page="signals" onclick="window.StockPilot.navigate('signals')">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/></svg>
      <span>Sinyaller</span>
    </a>
    <a class="sp-nav-link" data-page="markets" onclick="window.StockPilot.navigate('markets')">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15 15 0 014 10 15 15 0 01-4 10"/></svg>
      <span>Piyasalar</span>
    </a>
    <a class="sp-nav-link" data-page="funds" onclick="window.StockPilot.navigate('funds')">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="2" y="7" width="20" height="10" rx="2"/><line x1="12" y1="7" x2="12" y2="17"/></svg>
      <span>Fonlar</span>
    </a>
    <a class="sp-nav-link" data-page="portfolio" onclick="window.StockPilot.navigate('portfolio')">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="10"/><path d="M12 2a10 10 0 009.2 7H12V2z"/></svg>
      <span>Portfoy</span>
    </a>
    <a class="sp-nav-link" data-page="watchlist" onclick="window.StockPilot.navigate('watchlist')">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M19 21l-7-5-7 5V5a2 2 0 012-2h10a2 2 0 012 2z"/></svg>
      <span>Takip</span>
    </a>
  </div>
</nav>

<!-- ====== ANA ICERIK ====== -->
<main class="sp-main">
  <div id="page-content"></div>
</main>

<div class="toast-container" id="toastContainer"></div>
<script src="js/charts.js?v=4.0.0"></script><script src="js/analysis.js?v=4.0.0"></script><script src="js/recommendations.js?v=4.0.0"></script><script src="js/portfolio.js?v=4.0.0"></script><script src="js/signals.js?v=4.0.0"></script><script src="js/compare.js?v=4.0.0"></script><script src="js/app.js?v=4.0.0"></script>
</body></html>'''

with open('frontend/index.html', 'w', encoding='utf-8') as f:
    f.write(html)
    print("index.html yazildi (V4 Premium Siyah)")

fx = {'Karsilastir': 'Kar\u015f\u0131la\u015ft\u0131r', 'Gunluk': 'G\u00fcnl\u00fck', 'Portfoy': 'Portf\u00f6y'}
for k, v in fx.items():
    html = html.replace(k, v)

with open('frontend/index.html', 'w', encoding='utf-8') as f:
    f.write(html)
print('OK')
