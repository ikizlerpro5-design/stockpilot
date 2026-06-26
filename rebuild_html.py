"""index.html'i sifirdan temiz UTF-8 ile olustur"""
import os

html_content = '''<!DOCTYPE html>
<html lang="tr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>StockPilot - Borsa Istanbul Akilli Analiz Platformu</title>
  <meta name="description" content="StockPilot: BIST hisse senetleri icin yapay zeka destekli teknik analiz ve yatirim onerileri.">
  <script>
    window.onerror = function(msg, url, line, col, error) {
      fetch('/api/log_error', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ type: 'window.onerror', message: msg, url: url, line: line, col: col, stack: error ? error.stack : 'No stack trace available' }) }).catch(function(){});
      return false;
    };
    window.onunhandledrejection = function(event) {
      fetch('/api/log_error', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ type: 'unhandledrejection', message: event.reason ? (event.reason.message || event.reason.toString()) : 'Unhandled promise rejection', stack: event.reason && event.reason.stack ? event.reason.stack : 'No stack trace available' }) }).catch(function(){});
    };
  </script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
  <script src="https://unpkg.com/lightweight-charts@4.2.1/dist/lightweight-charts.standalone.production.js"></script>
  <link rel="stylesheet" href="css/style.css?v=2.2.0">
  <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><rect width='32' height='32' rx='8' fill='%23c5a880'/><path d='M8 22l6-8 4 4 6-10' stroke='white' fill='none' stroke-width='2.5' stroke-linecap='round' stroke-linejoin='round'/></svg>">
</head>
<body>

<div class="mesh-background">
  <div class="mesh-blob"></div>
  <div class="mesh-blob"></div>
  <div class="mesh-blob"></div>
  <div class="mesh-blob"></div>
</div>

<div class="app-container">
  <div class="sidebar-overlay" id="sidebarOverlay"></div>

  <aside class="sidebar" id="sidebar">
    <div class="sidebar-logo" onclick="window.StockPilot.navigate('dashboard')">
      <div class="logo-icon">
        <svg viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="22 7 13.5 15.5 8.5 10.5 2 17"></polyline>
          <polyline points="16 7 22 7 22 13"></polyline>
        </svg>
      </div>
      <div class="logo-text-area">
        <span class="logo-text">StockPilot</span>
        <span class="logo-sub">BIST Analiz Platformu</span>
      </div>
    </div>

    <nav class="sidebar-nav">
      <div class="nav-item active" data-page="dashboard" onclick="window.StockPilot.navigate('dashboard')"><span class="nav-icon"><svg viewBox="0 0 24 24"><rect x="3" y="3" width="7" height="7" rx="1"></rect><rect x="14" y="3" width="7" height="7" rx="1"></rect><rect x="3" y="14" width="7" height="7" rx="1"></rect><rect x="14" y="14" width="7" height="7" rx="1"></rect></svg></span><span>Ana Sayfa</span></div>
      <div class="nav-item" data-page="analysis" onclick="window.StockPilot.navigate('analysis')"><span class="nav-icon"><svg viewBox="0 0 24 24"><path d="M21 21H4a1 1 0 01-1-1V3"></path><path d="M7 14l4-4 4 4 5-5"></path></svg></span><span>Hisse Analiz</span></div>
      <div class="nav-item" data-page="daily" onclick="window.StockPilot.navigate('daily')"><span class="nav-icon"><svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg></span><span>Gunluk Oneriler</span></div>
      <div class="nav-item" data-page="weekly" onclick="window.StockPilot.navigate('weekly')"><span class="nav-icon"><svg viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect><line x1="16" y1="2" x2="16" y2="6"></line><line x1="8" y1="2" x2="8" y2="6"></line><line x1="3" y1="10" x2="21" y2="10"></line></svg></span><span>Haftalik Oneriler</span></div>
      <div class="nav-item" data-page="watchlist" onclick="window.StockPilot.navigate('watchlist')"><span class="nav-icon"><svg viewBox="0 0 24 24"><path d="M19 21l-7-5-7 5V5a2 2 0 012-2h10a2 2 0 012 2z"></path></svg></span><span>Takip Listesi</span></div>
      <div class="nav-item" data-page="signals" onclick="window.StockPilot.navigate('signals')"><span class="nav-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"></path></svg></span><span>Aktif Sinyaller</span></div>
      <div class="nav-item" data-page="markets" onclick="window.StockPilot.navigate('markets')"><span class="nav-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="2" y1="12" x2="22" y2="12"></line><path d="M12 2a15.3 15.3 0 014 10 15.3 15.3 0 01-4 10 15.3 15.3 0 01-4-10 15.3 15.3 0 014-10z"></path></svg></span><span>Piyasalar</span></div>
      <div class="nav-item" data-page="funds" onclick="window.StockPilot.navigate('funds')"><span class="nav-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="7" width="20" height="10" rx="2" ry="2"></rect><line x1="12" y1="7" x2="12" y2="17"></line><line x1="2" y1="12" x2="22" y2="12"></line></svg></span><span>Fonlar</span></div>
      <div class="nav-item" data-page="portfolio" onclick="window.StockPilot.navigate('portfolio')"><span class="nav-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21.21 15.89A10 10 0 1 1 8 2.83"></path><path d="M22 12A10 10 0 0 0 12 2v10z"></path></svg></span><span>Portfoyum</span></div>
      <div class="nav-item" data-page="history" onclick="window.StockPilot.navigate('history')"><span class="nav-icon"><svg viewBox="0 0 24 24"><polyline points="1 4 1 10 7 10"></polyline><path d="M3.51 15a9 9 0 102.13-9.36L1 10"></path></svg></span><span>Gecmis</span></div>
    </nav>

    <div class="sidebar-footer">
      <p>StockPilot v2.1 - BIST Analiz</p>
    </div>
  </aside>

  <div class="main-area" style="flex:1;">
    <header class="topbar">
      <div class="topbar-left">
        <button class="hamburger-btn" id="hamburgerBtn" onclick="window.StockPilot.toggleSidebar()">
          <svg viewBox="0 0 24 24" stroke-linecap="round" stroke-linejoin="round">
            <line x1="3" y1="6" x2="21" y2="6"></line><line x1="3" y1="12" x2="21" y2="12"></line><line x1="3" y1="18" x2="21" y2="18"></line>
          </svg>
        </button>
        <div class="search-container">
          <div class="search-bar">
            <svg viewBox="0 0 24 24" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
            <input type="text" id="searchInput" placeholder="Hisse ara... (orn: THYAO, ASELS)" autocomplete="off">
          </div>
          <div class="search-dropdown" id="searchDropdown"></div>
        </div>
      </div>
      <div class="topbar-right">
        <div class="bist-indicator" id="bistIndicator">
          <div class="live-dot"></div>
          <span class="bist-label">BIST 100</span>
          <span class="bist-value" id="bistValue">-</span>
          <span class="bist-change" id="bistChange">-</span>
        </div>
        <span class="time-display" id="timeDisplay"></span>
        <button class="theme-toggle-btn" id="themeToggleBtn" onclick="window.StockPilot.toggleTheme()" title="Temayi Degistir">
          <svg class="sun-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4"></circle><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"></path></svg>
          <svg class="moon-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"></path></svg>
        </button>
      </div>
    </header>

    <main class="main-content">
      <div id="page-content"></div>
    </main>
  </div>
</div>

<div class="toast-container" id="toastContainer"></div>

<script src="js/charts.js?v=2.2.0"></script>
<script src="js/analysis.js?v=2.2.0"></script>
<script src="js/recommendations.js?v=2.2.0"></script>
<script src="js/portfolio.js?v=2.2.0"></script>
<script src="js/signals.js?v=2.2.0"></script>
<script src="js/app.js?v=2.2.0"></script>

</body>
</html>'''

# Turkish character replacements (ASCII-safe -> proper UTF-8)
turkish_map = {
    'Istanbul': '\u0130stanbul',
    'Akilli': 'Ak\u0131ll\u0131',
    'icin': 'i\u00e7in',
    'onerileri': '\u00f6nerileri',
    'Gunluk Oneriler': 'G\u00fcnl\u00fck \u00d6neriler',
    'Haftalik Oneriler': 'Haftal\u0131k \u00d6neriler',
    'Portfoyum': 'Portf\u00f6y\u00fcm',
    'Gecmis': 'Ge\u00e7mi\u015f',
    'orn:': '\u00f6rn:',
    'Temayi Degistir': 'Temay\u0131 De\u011fi\u015ftir',
    'BIST Analiz Platformu': 'BIST Analiz Platformu',
}

for old, new in turkish_map.items():
    html_content = html_content.replace(old, new)

path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'frontend', 'index.html')

with open(path, 'w', encoding='utf-8', newline='\n') as f:
    f.write(html_content)

# Verify
with open(path, 'rb') as f:
    raw = f.read()

print('BOM:', 'VAR' if raw[:3] == b'\xef\xbb\xbf' else 'YOK')
idx = raw.find('\u0067\u00fc\u006e\u006c\u00fc\u006b'.encode('utf-8'))
print('Gunluk UTF-8:', 'DOGRU' if idx >= 0 else 'HATALI')
print('Dosya boyutu:', len(raw))
print('Basarili!')
