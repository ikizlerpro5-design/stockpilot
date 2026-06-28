/* ============================================
   StockPilot — Main Application Controller
   ============================================ */

window.StockPilot = (function () {
  'use strict';

  // --- State ---
  const state = {
    currentPage: null,
    currentSymbol: null,
    analysisData: null,
    watchlist: [],
    history: [],
    recentSearches: [],
    sidebarOpen: false,
  };

  // --- BIST Stock Database (for search autocomplete) ---
  const BIST_STOCKS = [
    { symbol: 'THYAO', name: 'Türk Hava Yolları' },
    { symbol: 'ASELS', name: 'Aselsan' },
    { symbol: 'SISE', name: 'Şişecam' },
    { symbol: 'EREGL', name: 'Ereğli Demir Çelik' },
    { symbol: 'KCHOL', name: 'Koç Holding' },
    { symbol: 'GARAN', name: 'Garanti BBVA' },
    { symbol: 'TUPRS', name: 'Tüpraş' },
    { symbol: 'FROTO', name: 'Ford Otosan' },
    { symbol: 'BIMAS', name: 'BİM Mağazalar' },
    { symbol: 'SAHOL', name: 'Sabancı Holding' },
    { symbol: 'PGSUS', name: 'Pegasus' },
    { symbol: 'AKBNK', name: 'Akbank' },
    { symbol: 'KOZAL', name: 'Koza Altın' },
    { symbol: 'TOASO', name: 'Tofaş' },
    { symbol: 'TAVHL', name: 'TAV Havalimanları' },
    { symbol: 'TCELL', name: 'Turkcell' },
    { symbol: 'HEKTS', name: 'Hektaş' },
    { symbol: 'PETKM', name: 'Petkim' },
    { symbol: 'EKGYO', name: 'Emlak Konut GYO' },
    { symbol: 'ISCTR', name: 'İş Bankası C' },
    { symbol: 'SASA', name: 'SASA Polyester' },
    { symbol: 'VESTL', name: 'Vestel Elektronik' },
    { symbol: 'ARCLK', name: 'Arçelik' },
    { symbol: 'DOHOL', name: 'Doğan Holding' },
    { symbol: 'YKBNK', name: 'Yapı Kredi' },
    { symbol: 'HALKB', name: 'Halkbank' },
    { symbol: 'VAKBN', name: 'Vakıfbank' },
    { symbol: 'MGROS', name: 'Migros' },
    { symbol: 'SOKM', name: 'Şok Marketler' },
    { symbol: 'TTKOM', name: 'Türk Telekom' },
    { symbol: 'ENKAI', name: 'Enka İnşaat' },
    { symbol: 'OTKAR', name: 'Otokar' },
    { symbol: 'TKFEN', name: 'Tekfen Holding' },
    { symbol: 'ULKER', name: 'Ülker Bisküvi' },
    { symbol: 'AEFES', name: 'Anadolu Efes' },
    { symbol: 'CCOLA', name: 'Coca-Cola İçecek' },
    { symbol: 'EMPAE', name: 'Empa Elektronik' },
    { symbol: 'EUPWR', name: 'Europower Enerji' },
    { symbol: 'KONTR', name: 'Kontrolmatik' },
    { symbol: 'SMRTG', name: 'Smart Güneş Enerjisi' },
    { symbol: 'GESAN', name: 'Girişim Elektrik' },
    { symbol: 'ODAS', name: 'Odaş Elektrik' },
    { symbol: 'DOAS', name: 'Doğuş Otomotiv' },
    { symbol: 'LOGO', name: 'Logo Yazılım' },
    { symbol: 'MPARK', name: 'MLP Sağlık' },
  ];

  // --- DOM References ---
  let pageContent, searchInput, searchDropdown;

  // --- Initialize ---
  function init() {
    pageContent = document.getElementById('page-content');
    searchInput = document.getElementById('searchInput');
    searchDropdown = document.getElementById('searchDropdown');

    // Load persisted state
    loadState();

    // Apply saved theme
    const savedTheme = localStorage.getItem('stockpilot_theme') || 'dark';
    state.theme = savedTheme;
    document.body.classList.toggle('light-theme', savedTheme === 'light');
    document.body.classList.toggle('dark-theme', savedTheme === 'dark');

    // Setup event listeners
    setupSearch();
    setupKeyboardNav();

    // Start time display
    updateTimeDisplay();
    setInterval(updateTimeDisplay, 1000);

    // === WEBSOCKET — Anlık Canlı Veri ===
    connectWebSocket();
    
    // İlk yükleme için bir kere API'den çek (socket bağlanana kadar)
    updateBistIndicator();

    // Route from hash
    const hash = window.location.hash.replace('#', '');
    if (hash) {
      const parts = hash.split('/');
      if (parts[0] === 'analysis' && parts[1]) {
        analyzeStock(parts[1]);
      } else {
        navigate(parts[0] || 'dashboard');
      }
    } else {
      navigate('dashboard');
    }

    // Hash change listener
    window.addEventListener('hashchange', () => {
      const h = window.location.hash.replace('#', '');
      const parts = h.split('/');
      if (parts[0] === 'analysis' && parts[1]) {
        if (state.currentSymbol !== parts[1]) {
          analyzeStock(parts[1]);
        }
      } else {
        navigate(parts[0] || 'dashboard', true);
      }
    });
  }

  // --- Navigation ---
  function navigate(page, fromHash) {
    StockPilotCharts.destroyAll();
    state.currentPage = page;

    // Update top nav active state
    document.querySelectorAll('.sp-nav-link').forEach(item => {
      item.classList.toggle('active', item.dataset.page === page);
    });

    // Update URL hash
    if (!fromHash) {
      window.location.hash = page;
    }

    // Render page
    switch (page) {
      case 'dashboard':
        renderDashboard();
        break;
      case 'analysis':
        renderAnalysisRoute();
        break;
      case 'daily':
        renderDailyPage();
        break;
      case 'weekly':
        renderWeeklyPage();
        break;
      case 'watchlist':
        renderWatchlistPage();
        break;
      case 'portfolio':
        renderPortfolioRoute();
        break;
      case 'signals':
        renderSignalsRoute();
        break;
      case 'compare':
        renderCompareRoute();
        break;
      case 'markets':
        renderMarketsPage();
        break;
      case 'funds':
        renderFundsPage();
        break;
      case 'history':
        renderHistoryPage();
        break;
      default:
        renderDashboard();
    }

    // Scroll to top
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  // --- Dashboard ---
  function renderDashboard() {
    const recentChips = state.recentSearches.length > 0
      ? `
        <div class="mt-32 anim-fade-in stagger-5">
          <div class="section-header">
            <h2 class="section-title"><span class="icon">🕐</span> Son Aramalarım</h2>
          </div>
          <div class="chips-row">
            ${state.recentSearches.slice(0, 8).map(s => `
              <span class="chip" onclick="window.StockPilot.analyzeStock('${s}')">📈 ${s}</span>
            `).join('')}
          </div>
        </div>
      ` : '';

    pageContent.innerHTML = `
      <!-- Market Overview -->
      <div class="anim-fade-in">
        <div class="section-header">
          <h2 class="section-title"><span class="icon">📊</span> Piyasa Özeti</h2>
        </div>
        <div class="grid-4">
          <div class="glass-card market-overview-card">
            <div class="flex justify-between items-center mb-8">
              <span style="font-size:0.82rem;color:var(--text-secondary);">BIST 100</span>
              <div class="live-dot"></div>
            </div>
            <div style="font-size:1.5rem;font-weight:700;" id="dashBistValue">—</div>
            <div style="font-size:0.85rem;font-weight:600;" id="dashBistChange">—</div>
            <div class="market-chart" id="bistMiniChart"></div>
          </div>
          <div class="glass-card market-overview-card">
            <div class="flex justify-between items-center mb-8">
              <span style="font-size:0.82rem;color:var(--text-secondary);">USD/TRY</span>
              <div class="live-dot"></div>
            </div>
            <div style="font-size:1.5rem;font-weight:700;" id="dashUsdValue">—</div>
            <div style="font-size:0.85rem;font-weight:600;" id="dashUsdChange">—</div>
            <div class="market-chart" id="usdMiniChart"></div>
          </div>
          <div class="glass-card market-overview-card">
            <div class="flex justify-between items-center mb-8">
              <span style="font-size:0.82rem;color:var(--text-secondary);">EUR/TRY</span>
              <div class="live-dot"></div>
            </div>
            <div style="font-size:1.5rem;font-weight:700;" id="dashEurValue">—</div>
            <div style="font-size:0.85rem;font-weight:600;" id="dashEurChange">—</div>
            <div class="market-chart" id="eurMiniChart"></div>
          </div>
          <div class="glass-card market-overview-card">
            <div class="flex justify-between items-center mb-8">
              <span style="font-size:0.82rem;color:var(--text-secondary);">Altın (gr/TL)</span>
              <div class="live-dot"></div>
            </div>
            <div style="font-size:1.5rem;font-weight:700;" id="dashGoldValue">—</div>
            <div style="font-size:0.85rem;font-weight:600;" id="dashGoldChange">—</div>
            <div class="market-chart" id="goldMiniChart"></div>
          </div>
        </div>
      </div>

      <!-- Fon Özeti Widget -->
      <div class="mt-32 anim-fade-in stagger-3">
        <div class="section-header">
          <h2 class="section-title"><span class="icon">💰</span> Fon Özeti</h2>
          <button class="btn btn-ghost" onclick="window.StockPilot.navigate('funds')">Tüm Fonlar →</button>
        </div>
        <div id="dashFundsWidget">
          <div class="grid-3">
            <div class="glass-card" style="padding:16px;text-align:center;"><div class="skeleton" style="height:80px;"></div></div>
            <div class="glass-card" style="padding:16px;text-align:center;"><div class="skeleton" style="height:80px;"></div></div>
            <div class="glass-card" style="padding:16px;text-align:center;"><div class="skeleton" style="height:80px;"></div></div>
          </div>
        </div>
      </div>

      <!-- Top Picks -->
      <div class="mt-32 anim-fade-in stagger-3">
        <div class="section-header">
          <h2 class="section-title"><span class="icon">🏆</span> Günün Öne Çıkanları</h2>
          <button class="btn btn-ghost" onclick="window.StockPilot.navigate('daily')">Tümünü Gör →</button>
        </div>
        <div class="grid-3">
          ${renderTopPicks()}
        </div>
      </div>

      <!-- News -->
      <div class="mt-32 anim-fade-in stagger-4">
        <div class="section-header">
          <h2 class="section-title"><span class="icon">📰</span> Son Haberler</h2>
        </div>
        <div class="news-list">
          ${renderDashboardNews()}
        </div>
      </div>

      <!-- Canli Sinyaller -->
      <div class="mt-32 anim-fade-in stagger-5">
        <div class="section-header">
          <h2 class="section-title"><span class="icon">⚡</span> Canli Al/Sat Sinyalleri</h2>
          <span style="font-size:0.7rem;color:var(--text-muted);">Kademe analizi • 3sn guncelleme</span>
        </div>
        <div id="dashSignalsWidget">
          <div class="an-empty-inline">📡 Sinyaller yukleniyor...</div>
        </div>
      </div>

      ${recentChips}
    `;

    // Load signals + dashboard data
    loadDashboardSignals();
    setInterval(loadDashboardSignals, 5000);

    // Render mini charts and update indicators after DOM
    requestAnimationFrame(async () => {
      try {
        const res = await fetch('/api/market-overview');
        const data = await res.json();
        if (data.success) {
          const isBistUp = data.xu100 ? (data.xu100.degisim >= 0) : true;
          const isUsdUp = data.usdtry ? (data.usdtry.degisim >= 0) : true;
          const isEurUp = data.eurtry ? (data.eurtry.degisim >= 0) : true;
          const isGoldUp = data.altin ? (data.altin.degisim >= 0) : true;
          
          StockPilotCharts.createMiniChart('bistMiniChart', StockPilotCharts.generateMockLineData(30, data.xu100 ? data.xu100.deger : 10500, isBistUp ? 'up' : 'down'), isBistUp);
          StockPilotCharts.createMiniChart('usdMiniChart', StockPilotCharts.generateMockLineData(30, data.usdtry ? data.usdtry.deger : 38.5, isUsdUp ? 'up' : 'down'), isUsdUp);
          StockPilotCharts.createMiniChart('eurMiniChart', StockPilotCharts.generateMockLineData(30, data.eurtry ? data.eurtry.deger : 42.0, isEurUp ? 'up' : 'down'), isEurUp);
          StockPilotCharts.createMiniChart('goldMiniChart', StockPilotCharts.generateMockLineData(30, data.altin ? data.altin.deger : 3100, isGoldUp ? 'up' : 'down'), isGoldUp);

          // Update dashboard card values directly from fetched data
          const dbBist = document.getElementById('dashBistValue');
          const dbBistChg = document.getElementById('dashBistChange');
          if (data.xu100) {
            if (dbBist) dbBist.textContent = formatNumber(data.xu100.deger);
            if (dbBistChg) {
              const pre = data.xu100.degisim >= 0 ? '▲ +' : '▼ ';
              dbBistChg.textContent = `${pre}${Math.abs(data.xu100.degisim_yuzde).toFixed(2)}%`;
              dbBistChg.className = `market-change-label ${data.xu100.degisim >= 0 ? 'up' : 'down'}`;
            }
          }
          const dbUsd = document.getElementById('dashUsdValue');
          const dbUsdChg = document.getElementById('dashUsdChange');
          if (data.usdtry) {
            if (dbUsd) dbUsd.textContent = '₺' + formatNumber(data.usdtry.deger);
            if (dbUsdChg) {
              const pre = data.usdtry.degisim >= 0 ? '▲ +' : '▼ ';
              dbUsdChg.textContent = `${pre}${Math.abs(data.usdtry.degisim_yuzde).toFixed(2)}%`;
              dbUsdChg.className = `market-change-label ${data.usdtry.degisim >= 0 ? 'up' : 'down'}`;
            }
          }
          const dbEur = document.getElementById('dashEurValue');
          const dbEurChg = document.getElementById('dashEurChange');
          if (data.eurtry) {
            if (dbEur) dbEur.textContent = '₺' + formatNumber(data.eurtry.deger);
            if (dbEurChg) {
              const pre = data.eurtry.degisim >= 0 ? '▲ +' : '▼ ';
              dbEurChg.textContent = `${pre}${Math.abs(data.eurtry.degisim_yuzde).toFixed(2)}%`;
              dbEurChg.className = `market-change-label ${data.eurtry.degisim >= 0 ? 'up' : 'down'}`;
            }
          }
          const dbGold = document.getElementById('dashGoldValue');
          const dbGoldChg = document.getElementById('dashGoldChange');
          if (data.altin) {
            if (dbGold) dbGold.textContent = '₺' + formatNumber(data.altin.deger);
            if (dbGoldChg) {
              const pre = data.altin.degisim >= 0 ? '▲ +' : '▼ ';
              dbGoldChg.textContent = `${pre}${Math.abs(data.altin.degisim_yuzde).toFixed(2)}%`;
              dbGoldChg.className = `market-change-label ${data.altin.degisim >= 0 ? 'up' : 'down'}`;
            }
          }
        }
      } catch (e) {
        StockPilotCharts.createMiniChart('bistMiniChart', StockPilotCharts.generateMockLineData(30, 10500, 'up'), true);
        StockPilotCharts.createMiniChart('usdMiniChart', StockPilotCharts.generateMockLineData(30, 38.5, 'down'), false);
        StockPilotCharts.createMiniChart('eurMiniChart', StockPilotCharts.generateMockLineData(30, 42.0, 'up'), true);
        StockPilotCharts.createMiniChart('goldMiniChart', StockPilotCharts.generateMockLineData(30, 3100, 'up'), true);
      }
      
      // Fon widget'ı yükle
      try {
        const fRes = await fetch('/api/funds');
        const fData = await fRes.json();
        if (fData.success) {
          renderDashboardFunds(fData);
        }
      } catch (e) { /* fon verisi yüklenemezse sessiz kal */ }
      
      updateBistIndicator();
    });
  }

  function getBadgeStyle(symbol) {
    const s = symbol || 'BIST';
    let hash = 0;
    for (let i = 0; i < s.length; i++) {
      hash = s.charCodeAt(i) + ((hash << 5) - hash);
    }
    const h1 = Math.abs(hash % 360);
    const h2 = (h1 + 50) % 360;
    return `background: linear-gradient(135deg, hsl(${h1}, 75%, 40%), hsl(${h2}, 80%, 30%)); text-shadow: 0 1px 3px rgba(0,0,0,0.3); font-weight:700; color:#fff; display:flex; align-items:center; justify-content:center;`;
  }

  function renderTopPicks() {
    const picks = [
      { symbol: 'THYAO', name: 'Türk Hava Yolları', price: 312.40, changePercent: 3.25, action: 'AL', confidence: 87 },
      { symbol: 'ASELS', name: 'Aselsan', price: 94.70, changePercent: 1.80, action: 'AL', confidence: 82 },
      { symbol: 'EREGL', name: 'Ereğli Demir Çelik', price: 57.85, changePercent: -2.10, action: 'SAT', confidence: 71 },
    ];

    return picks.map(p => {
      const changeClass = p.changePercent >= 0 ? 'up' : 'down';
      const changeIcon = p.changePercent >= 0 ? '▲' : '▼';
      const actionBadge = getActionBadgeClass(p.action);
      const confColor = p.action === 'AL' ? 'green' : p.action === 'SAT' ? 'red' : 'yellow';
      const initials = p.symbol.substring(0, 2);
      // Generate a stable color from symbol name
      let hash = 0;
      for (let i = 0; i < p.symbol.length; i++) hash = p.symbol.charCodeAt(i) + ((hash << 5) - hash);
      const hue = Math.abs(hash % 360);

      return `
        <div class="glass-card stock-card" onclick="window.StockPilot.analyzeStock('${p.symbol}')">
          <div class="stock-card-header" style="display:flex; align-items:center; gap: 12px; margin-bottom:12px;">
            <div class="stock-logo" style="width:36px;height:36px;border-radius:8px;background:linear-gradient(135deg,hsl(${hue},60%,35%),hsl(${(hue+40)%360},70%,25%));display:flex;align-items:center;justify-content:center;flex-shrink:0;font-weight:700;font-size:0.7rem;color:#fff;text-shadow:0 1px 2px rgba(0,0,0,0.4);">
              ${initials}
            </div>
            <div style="flex:1; min-width:0;">
              <div class="stock-symbol" style="white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${p.symbol}</div>
              <div class="stock-name" style="white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${p.name}</div>
            </div>
            <span class="badge ${actionBadge}">${p.action}</span>
          </div>
          <div class="stock-price">₺${formatNumber(p.price)}</div>
          <div class="stock-change ${changeClass}">${changeIcon} ${p.changePercent >= 0 ? '+' : ''}${p.changePercent.toFixed(2)}%</div>
          <div class="stock-card-footer">
            <div class="confidence-bar-container">
              <div class="confidence-bar-label">
                <span>Güven</span>
                <span>${p.confidence}%</span>
              </div>
              <div class="confidence-bar">
                <div class="confidence-bar-fill ${confColor}" style="width:${p.confidence}%"></div>
              </div>
            </div>
          </div>
        </div>
      `;
    }).join('');
  }

  function loadDashboardSignals() {
    const el = document.getElementById('dashSignalsWidget');
    if (!el) return;
    fetch('/api/signals/live')
      .then(r => r.json())
      .then(data => {
        if (!data.success || !data.signals || !Object.keys(data.signals).length) {
          el.innerHTML = '<div class="an-empty-inline">🔍 Henuz sinyal yok. Watchlist\'e hisse ekleyin.</div>';
          return;
        }
        let html = '<div class="signal-cards">';
        for (const [sym, sig] of Object.entries(data.signals)) {
          const isAnomaly = sig.type === 'ANOMALI';
          const cls = isAnomaly ? 'signal-anomaly' 
            : sig.type === 'AL' ? 'signal-al' 
            : sig.type === 'SAT' ? 'signal-sat' : 'signal-tut';
          const emoji = isAnomaly ? '⚡' : sig.type === 'AL' ? '🟢' : sig.type === 'SAT' ? '🔴' : '⚪';
          
          // Anomali alert'leri
          let anomalyHtml = '';
          if (sig.anomalies && sig.anomalies.length > 0) {
            anomalyHtml = '<div class="signal-anomalies">' +
              sig.anomalies.map(a => 
                `<div class="signal-anomaly-item ${a.severity === 'high' ? 'anomaly-high' : a.severity === 'medium' ? 'anomaly-med' : 'anomaly-low'}">${a.msg}</div>`
              ).join('') +
              '</div>';
          }
          
          // Trend bilgisi
          let trendHtml = '';
          if (sig.trend && sig.trend !== 'notr' && sig.trend !== 'yetersiz_veri') {
            const trendLabel = sig.trend === 'alis_birikiyor' ? '📈 Alış birikiyor' : '📉 Satış birikiyor';
            trendHtml = `<div class="signal-trend">${trendLabel}</div>`;
          }
          
          html += `
            <div class="signal-card ${cls}" onclick="window.StockPilot.analyzeStock('${sym}')">
              <div class="signal-card-top">
                <span class="signal-symbol">${sym}</span>
                <span class="signal-type">${emoji} ${sig.type}</span>
              </div>
              <div class="signal-confidence">Guven: %${sig.confidence || 50}</div>
              ${anomalyHtml}
              ${trendHtml}
              <div class="signal-reasons">${(sig.reasons || []).slice(0, 2).join(' • ')}</div>
              <div class="signal-meta">
                ${sig.entry ? '<span>Giris: ₺'+sig.entry.toFixed(2)+'</span>' : ''}
                ${sig.stop ? '<span>Stop: ₺'+sig.stop.toFixed(2)+'</span>' : ''}
                ${sig.price ? '<span>Fiyat: ₺'+sig.price.toFixed(2)+'</span>' : ''}
              </div>
            </div>`;
        }
        html += '</div>';
        el.innerHTML = html;
      })
      .catch(() => {});
  }

  function renderDashboardNews() {
    const news = [
      { title: 'Türk Hava Yolları yolcu sayısında rekor kırdı', source: 'Bloomberg HT', score: 0.85, symbol: 'THYAO', time: '2 saat önce', category: 'Havacılık' },
      { title: 'Aselsan yeni savunma ihalesini kazandı', source: 'Dünya Gazetesi', score: 0.90, symbol: 'ASELS', time: '3 saat önce', category: 'Savunma' },
      { title: 'Merkez Bankası faiz kararını açıkladı', source: 'Anadolu Ajansı', score: 0.50, symbol: null, time: '5 saat önce', category: 'Ekonomi' },
      { title: 'BIST 100 endeksi güne yükselişle başladı', source: 'Ekonomist', score: 0.65, symbol: null, time: '6 saat önce', category: 'Piyasa' },
      { title: 'Ereğli Demir Çelik yeni yatırım planını duyurdu', source: 'Bloomberg HT', score: 0.78, symbol: 'EREGL', time: '7 saat önce', category: 'Sanayi' },
      { title: 'Tüpraş rafineri kapasite artışı hedefliyor', source: 'Dünya Gazetesi', score: 0.72, symbol: 'TUPRS', time: '8 saat önce', category: 'Enerji' },
    ];

    return `
      <div class="news-grid-modern">
        ${news.map((n, i) => {
          const sClass = n.score >= 0.6 ? 'positive' : n.score <= 0.4 ? 'negative' : 'neutral';
          const sEmoji = n.score >= 0.6 ? '📈' : n.score <= 0.4 ? '📉' : '📊';
          const clickable = n.symbol ? `onclick="window.StockPilot.analyzeStock('${n.symbol}')"` : '';
          const cursorClass = n.symbol ? 'cursor:pointer;' : '';
          
          return `
            <div class="news-card-modern glass-card anim-fade-in stagger-${i}" ${clickable} style="${cursorClass}">
              <div class="news-card-top">
                <span class="news-category-badge">${n.category}</span>
                <span class="news-time">${n.time}</span>
              </div>
              <div class="news-card-title">${sEmoji} ${n.title}</div>
              <div class="news-card-bottom">
                <div class="news-source-row">
                  <span class="news-source-dot"></span>
                  <span class="news-source-name">${n.source}</span>
                </div>
                <div class="news-sentiment-row">
                  <div class="news-sentiment-bar">
                    <div class="news-sentiment-fill ${sClass}" style="width:${Math.round(n.score * 100)}%"></div>
                  </div>
                  <span class="news-sentiment-label ${sClass}">%${Math.round(n.score * 100)}</span>
                </div>
              </div>
              ${n.symbol ? `<div class="news-card-link">Hisse analizini gör →</div>` : ''}
            </div>
          `;
        }).join('')}
      </div>
    `;
  }

  // --- Analysis ---
  function renderAnalysisRoute() {
    if (state.currentSymbol && state.analysisData) {
      StockPilotAnalysis.renderAnalysisPage(pageContent, state.analysisData);
    } else {
      pageContent.innerHTML = `
        <div class="empty-state" style="min-height:60vh;">
          <div class="empty-icon">🔍</div>
          <div class="empty-title">Hisse Seçilmedi</div>
          <div class="empty-desc">Yukarıdaki arama çubuğunu kullanarak bir BIST hissesi arayın ve detaylı analiz görün.</div>
        </div>
      `;
    }
  }

  // --- Portfolio ---
  function renderPortfolioRoute() {
    StockPilotPortfolio.renderPortfolioPage(pageContent);
  }

  // --- Signals ---
  function renderSignalsRoute() {
    StockPilotSignals.renderSignalsPage(pageContent);
  }

  // --- Compare ---
  function renderCompareRoute() {
    StockPilotCompare.renderComparePage(pageContent);
  }

  // --- Funds ---
  async function renderFundsPage() {
    pageContent.innerHTML = `
      <div class="anim-fade-in">
        <div class="section-header">
          <h2 class="section-title"><span class="icon">💰</span> Yatırım Fonları</h2>
          <p class="section-subtitle">TEFAS fonları günlük açıklanan fiyatlar — Pusula Portföy & Tera Yatırım</p>
        </div>
        <div id="fundsContent">
          <div class="loading-container">
            <div class="loading-spinner"></div>
            <p class="loading-text">Fon verileri yükleniyor...</p>
          </div>
        </div>
      </div>
    `;

    try {
      const res = await fetch('/api/funds');
      const data = await res.json();

      if (data.success) {
        const funds = data.fonlar || [];
        const yukselenler = data.yukselenler || [];
        const dusenler = data.dusenler || [];
        const gruplar = data.gruplar || {};

        const riskIcon = (r) => {
          if (r >= 6) return '<span class="risk-badge high">Yüksek Risk</span>';
          if (r >= 4) return '<span class="risk-badge mid">Orta Risk</span>';
          return '<span class="risk-badge low">Düşük Risk</span>';
        };

        const renderFundCard = (f) => {
          const isUp = f.degisim >= 0;
          const chgIcon = isUp ? '▲' : '▼';
          const chgClass = isUp ? 'up' : 'down';
          const durumText = f.durum === 'yeni' ? 'Yeni' : f.durum === 'hata' ? 'Hata' : isUp ? 'Yükseliş' : 'Düşüş';
          const fiyatGoster = f.fiyat > 0 ? '₺' + formatNumber(f.fiyat) : '—';
          
          return `
            <div class="glass-card fund-card">
              <div class="fund-card-header">
                <div class="fund-code-badge">${f.kod}</div>
                <div class="fund-risk">${riskIcon(f.risk)}</div>
              </div>
              <div class="fund-name" title="${f.ad}">${f.ad}</div>
              <div class="fund-tur">${f.kurum || ''} · ${f.tur}</div>
              <div class="fund-price-row">
                <span class="fund-price ${chgClass}">${fiyatGoster}</span>
                <span class="fund-change ${chgClass}">${chgIcon} ${f.degisim_yuzde.toFixed(2)}%</span>
              </div>
              <div class="fund-details">
                <div class="fund-detail-item">
                  <span>Günlük Değişim</span>
                  <span class="${chgClass}">₺${formatNumber(Math.abs(f.degisim))}</span>
                </div>
                <div class="fund-detail-item">
                  <span>5G Yüksek</span>
                  <span>₺${f.yuksek_5g > 0 ? formatNumber(f.yuksek_5g) : '—'}</span>
                </div>
                <div class="fund-detail-item">
                  <span>5G Düşük</span>
                  <span>₺${f.dusuk_5g > 0 ? formatNumber(f.dusuk_5g) : '—'}</span>
                </div>
                <div class="fund-detail-item">
                  <span>Hacim</span>
                  <span>${f.hacim > 0 ? f.hacim.toLocaleString('tr-TR') : '—'}</span>
                </div>
              </div>
              ${f.son_aciklama ? `
              <div class="fund-disclosure">
                <div class="fund-disclosure-label">📋 Son Açıklanan Veri</div>
                <div class="fund-disclosure-row">
                  <span>Kapanış</span>
                  <span class="fund-disclosure-price">₺${formatNumber(f.son_aciklama.kapanis)}</span>
                </div>
                <div class="fund-disclosure-row">
                  <span>Tarih</span>
                  <span>${f.son_aciklama.tarih}</span>
                </div>
              </div>
              ` : ''}
              <div class="fund-status ${chgClass}">● ${durumText}</div>
            </div>
          `;
        };

        const contentHtml = `
          <!-- Özet Kartları -->
          <div class="grid-3 mb-32 anim-fade-in">
            <div class="glass-card market-card-xl">
              <div class="market-card-header">
                <span class="market-card-icon">📊</span>
                <span class="market-card-title">Toplam Fon</span>
              </div>
              <div class="market-card-value" style="color:var(--text-primary);">${data.toplam}</div>
              <div class="market-card-change" style="color:var(--text-secondary);">takip ediliyor</div>
            </div>
            <div class="glass-card market-card-xl">
              <div class="market-card-header">
                <span class="market-card-icon">🚀</span>
                <span class="market-card-title">En Çok Yükselen</span>
              </div>
              ${yukselenler.length > 0 ? `
              <div class="market-card-value up">${yukselenler[0].kod}</div>
              <div class="market-card-change up">▲ %${yukselenler[0].degisim_yuzde.toFixed(2)} — ₺${formatNumber(yukselenler[0].fiyat)}</div>
              ` : '<div class="market-card-value">—</div>'}
            </div>
            <div class="glass-card market-card-xl">
              <div class="market-card-header">
                <span class="market-card-icon">📉</span>
                <span class="market-card-title">En Çok Düşen</span>
              </div>
              ${dusenler.length > 0 ? `
              <div class="market-card-value down">${dusenler[0].kod}</div>
              <div class="market-card-change down">▼ %${Math.abs(dusenler[0].degisim_yuzde).toFixed(2)} — ₺${formatNumber(dusenler[0].fiyat)}</div>
              ` : '<div class="market-card-value">—</div>'}
            </div>
          </div>

          <!-- Hisse/Endeks Fonları -->
          <div class="mb-32 anim-fade-in stagger-1">
            <div class="section-header">
              <h3 class="section-title"><span class="icon">📈</span> Hisse & Endeks Fonları</h3>
            </div>
            <div class="fund-grid">
              ${(gruplar.hisse || []).map(renderFundCard).join('')}
              ${(!gruplar.hisse || gruplar.hisse.length === 0) ? '<div class="empty-state-sm">Hisse BYF verisi bulunamadı</div>' : ''}
            </div>
          </div>

          <!-- Tahvil BYF'leri -->
          <div class="mb-32 anim-fade-in stagger-2">
            <div class="section-header">
              <h3 class="section-title"><span class="icon">🏦</span> Tahvil BYF'leri</h3>
            </div>
            <div class="fund-grid">
              ${(gruplar.tahvil || []).map(renderFundCard).join('')}
              ${(!gruplar.tahvil || gruplar.tahvil.length === 0) ? '<div class="empty-state-sm">Tahvil BYF verisi bulunamadı</div>' : ''}
            </div>
          </div>

          <!-- Diğer Fonlar -->
          ${(gruplar.diger || []).length > 0 ? `
          <div class="mb-32 anim-fade-in stagger-3">
            <div class="section-header">
              <h3 class="section-title"><span class="icon">🌐</span> Diğer Fonlar</h3>
            </div>
            <div class="fund-grid">
              ${gruplar.diger.map(renderFundCard).join('')}
            </div>
          </div>
          ` : ''}

          <!-- Son Güncelleme -->
          <div class="text-center anim-fade-in" style="color:var(--text-muted);font-size:0.8rem;">
            Son güncelleme: ${data.tarih || '—'} | Veri Kaynağı: yfinance
          </div>
        `;

        pageContent.innerHTML = contentHtml;
      } else {
        pageContent.innerHTML = `
          <div class="empty-state" style="min-height:40vh;">
            <div class="empty-icon">❌</div>
            <div class="empty-title">Fon Verisi Alınamadı</div>
            <div class="empty-desc">${data.error || 'Geçici bir sorun oluştu.'}</div>
          </div>
        `;
      }
    } catch (err) {
      pageContent.innerHTML = `
        <div class="empty-state" style="min-height:40vh;">
          <div class="empty-icon">❌</div>
          <div class="empty-title">Bağlantı Hatası</div>
          <div class="empty-desc">Fon verileri yüklenirken hata: ${err.message}</div>
        </div>
      `;
    }
  }
  async function renderMarketsPage() {
    pageContent.innerHTML = `
      <div class="anim-fade-in">
        <div class="section-header">
          <h2 class="section-title"><span class="icon">🌍</span> Piyasalar</h2>
          <p class="section-subtitle">Canlı döviz, altın ve BIST 100 verileri</p>
        </div>
        <div id="marketsContent">
          <div class="loading-container">
            <div class="loading-spinner"></div>
            <p class="loading-text">Piyasa verileri yükleniyor...</p>
          </div>
        </div>
      </div>
    `;

    try {
      const res = await fetch('/api/market-overview');
      const data = await res.json();
      
      if (data.success) {
        const isBistUp = data.xu100 ? data.xu100.degisim >= 0 : true;
        const bistChgIcon = isBistUp ? '▲' : '▼';
        
        const contentHtml = `
          <!-- Ana Piyasa Kartları -->
          <div class="grid-4 mb-32 anim-fade-in">
            <div class="glass-card market-card-xl">
              <div class="market-card-header">
                <span class="market-card-icon">📈</span>
                <span class="market-card-title">BIST 100</span>
                <div class="live-dot"></div>
              </div>
              <div class="market-card-value ${isBistUp ? 'up' : 'down'}">${data.xu100 ? formatNumber(data.xu100.deger) : '—'}</div>
              <div class="market-card-change ${isBistUp ? 'up' : 'down'}">
                ${bistChgIcon} ${data.xu100 ? Math.abs(data.xu100.degisim_yuzde).toFixed(2) : '—'}%
              </div>
              ${data.xu100 ? `
              <div class="market-card-range">
                <div class="range-item"><span>Gün İçi Yüksek</span><span class="up">${formatNumber(data.xu100.yuksek)}</span></div>
                <div class="range-item"><span>Gün İçi Düşük</span><span class="down">${formatNumber(data.xu100.dusuk)}</span></div>
              </div>` : ''}
            </div>

            <div class="glass-card market-card-xl">
              <div class="market-card-header">
                <span class="market-card-icon">💵</span>
                <span class="market-card-title">USD/TRY</span>
                <div class="live-dot"></div>
              </div>
              <div class="market-card-value ${data.usdtry && data.usdtry.degisim >= 0 ? 'up' : 'down'}">₺${data.usdtry ? formatNumber(data.usdtry.deger) : '—'}</div>
              <div class="market-card-change ${data.usdtry && data.usdtry.degisim >= 0 ? 'up' : 'down'}">
                ${data.usdtry && data.usdtry.degisim >= 0 ? '▲' : '▼'} ${data.usdtry ? Math.abs(data.usdtry.degisim_yuzde).toFixed(2) : '—'}%
              </div>
              <div class="market-card-range">
                <div class="range-item"><span>Günlük Değişim</span><span>₺${data.usdtry ? formatNumber(Math.abs(data.usdtry.degisim)) : '—'}</span></div>
                <div class="range-item"><span>Durum</span><span>${data.usdtry ? data.usdtry.durum : '—'}</span></div>
              </div>
            </div>

            <div class="glass-card market-card-xl">
              <div class="market-card-header">
                <span class="market-card-icon">💶</span>
                <span class="market-card-title">EUR/TRY</span>
                <div class="live-dot"></div>
              </div>
              <div class="market-card-value ${data.eurtry && data.eurtry.degisim >= 0 ? 'up' : 'down'}">₺${data.eurtry ? formatNumber(data.eurtry.deger) : '—'}</div>
              <div class="market-card-change ${data.eurtry && data.eurtry.degisim >= 0 ? 'up' : 'down'}">
                ${data.eurtry && data.eurtry.degisim >= 0 ? '▲' : '▼'} ${data.eurtry ? Math.abs(data.eurtry.degisim_yuzde).toFixed(2) : '—'}%
              </div>
              <div class="market-card-range">
                <div class="range-item"><span>Günlük Değişim</span><span>₺${data.eurtry ? formatNumber(Math.abs(data.eurtry.degisim)) : '—'}</span></div>
                <div class="range-item"><span>Durum</span><span>${data.eurtry ? data.eurtry.durum : '—'}</span></div>
              </div>
            </div>

            <div class="glass-card market-card-xl">
              <div class="market-card-header">
                <span class="market-card-icon">🪙</span>
                <span class="market-card-title">Gram Altın</span>
                <div class="live-dot"></div>
              </div>
              <div class="market-card-value ${data.altin && data.altin.degisim >= 0 ? 'up' : 'down'}">₺${data.altin ? formatNumber(data.altin.deger) : '—'}</div>
              <div class="market-card-change ${data.altin && data.altin.degisim >= 0 ? 'up' : 'down'}">
                ${data.altin && data.altin.degisim >= 0 ? '▲' : '▼'} ${data.altin ? Math.abs(data.altin.degisim_yuzde).toFixed(2) : '—'}%
              </div>
              <div class="market-card-range">
                <div class="range-item"><span>Günlük Değişim</span><span>₺${data.altin ? formatNumber(Math.abs(data.altin.degisim)) : '—'}</span></div>
                <div class="range-item"><span>Durum</span><span>${data.altin ? data.altin.durum : '—'}</span></div>
              </div>
            </div>
          </div>

          <!-- Mini Grafikler -->
          <div class="grid-4 mb-32 anim-fade-in stagger-1">
            <div class="glass-card" style="min-height:180px;">
              <div style="font-size:0.8rem;color:var(--text-secondary);margin-bottom:8px;">BIST 100 — 5 Günlük</div>
              <div class="market-chart" id="marketsBistChart" style="height:140px;"></div>
            </div>
            <div class="glass-card" style="min-height:180px;">
              <div style="font-size:0.8rem;color:var(--text-secondary);margin-bottom:8px;">USD/TRY — 5 Günlük</div>
              <div class="market-chart" id="marketsUsdChart" style="height:140px;"></div>
            </div>
            <div class="glass-card" style="min-height:180px;">
              <div style="font-size:0.8rem;color:var(--text-secondary);margin-bottom:8px;">EUR/TRY — 5 Günlük</div>
              <div class="market-chart" id="marketsEurChart" style="height:140px;"></div>
            </div>
            <div class="glass-card" style="min-height:180px;">
              <div style="font-size:0.8rem;color:var(--text-secondary);margin-bottom:8px;">Altın (gr/TL) — 5 Günlük</div>
              <div class="market-chart" id="marketsGoldChart" style="height:140px;"></div>
            </div>
          </div>

          <!-- En Çok Yükselen / Düşen -->
          <div class="grid-2 mb-24 anim-fade-in stagger-2">
            <div class="glass-card">
              <div class="section-header">
                <h3 class="section-title"><span class="icon">🚀</span> En Çok Yükselenler</h3>
              </div>
              <div class="movers-list">
                ${(data.yukselenler || []).slice(0, 5).map(m => `
                  <div class="mover-item" onclick="window.StockPilot.analyzeStock('${m.symbol}')" style="cursor:pointer;">
                    <div class="flex items-center gap-8" style="flex:1;min-width:0;">
                      <img src="${m.logo_url}" alt="${m.symbol}" style="width:24px;height:24px;border-radius:4px;" onerror="this.style.display='none'">
                      <span style="font-weight:600;white-space:nowrap;">${m.symbol}</span>
                      <span style="font-size:0.8rem;color:var(--text-secondary);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${m.isim}</span>
                    </div>
                    <div style="text-align:right;">
                      <div style="font-weight:600;">₺${formatNumber(m.fiyat)}</div>
                      <div class="up" style="font-size:0.85rem;">▲ %${m.degisim_yuzde.toFixed(2)}</div>
                    </div>
                  </div>
                `).join('')}
                ${(!data.yukselenler || data.yukselenler.length === 0) ? '<div class="empty-state-sm">Veri bulunamadı</div>' : ''}
              </div>
            </div>
            <div class="glass-card">
              <div class="section-header">
                <h3 class="section-title"><span class="icon">📉</span> En Çok Düşenler</h3>
              </div>
              <div class="movers-list">
                ${(data.dusenler || []).slice(0, 5).map(m => `
                  <div class="mover-item" onclick="window.StockPilot.analyzeStock('${m.symbol}')" style="cursor:pointer;">
                    <div class="flex items-center gap-8" style="flex:1;min-width:0;">
                      <img src="${m.logo_url}" alt="${m.symbol}" style="width:24px;height:24px;border-radius:4px;" onerror="this.style.display='none'">
                      <span style="font-weight:600;white-space:nowrap;">${m.symbol}</span>
                      <span style="font-size:0.8rem;color:var(--text-secondary);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${m.isim}</span>
                    </div>
                    <div style="text-align:right;">
                      <div style="font-weight:600;">₺${formatNumber(m.fiyat)}</div>
                      <div class="down" style="font-size:0.85rem;">▼ %${Math.abs(m.degisim_yuzde).toFixed(2)}</div>
                    </div>
                  </div>
                `).join('')}
                ${(!data.dusenler || data.dusenler.length === 0) ? '<div class="empty-state-sm">Veri bulunamadı</div>' : ''}
              </div>
            </div>
          </div>

          <!-- Son Güncelleme -->
          <div class="text-center anim-fade-in" style="color:var(--text-muted);font-size:0.8rem;">
            Son güncelleme: ${data.tarih || '—'}
          </div>
        `;

        pageContent.innerHTML = contentHtml;

        // Render mini charts
        requestAnimationFrame(() => {
          if (data.xu100) {
            StockPilotCharts.createMiniChart('marketsBistChart', StockPilotCharts.generateMockLineData(30, data.xu100.deger, isBistUp ? 'up' : 'down'), isBistUp);
          }
          if (data.usdtry) {
            StockPilotCharts.createMiniChart('marketsUsdChart', StockPilotCharts.generateMockLineData(30, data.usdtry.deger, data.usdtry.degisim >= 0 ? 'up' : 'down'), data.usdtry.degisim >= 0);
          }
          if (data.eurtry) {
            StockPilotCharts.createMiniChart('marketsEurChart', StockPilotCharts.generateMockLineData(30, data.eurtry.deger, data.eurtry.degisim >= 0 ? 'up' : 'down'), data.eurtry.degisim >= 0);
          }
          if (data.altin) {
            StockPilotCharts.createMiniChart('marketsGoldChart', StockPilotCharts.generateMockLineData(30, data.altin.deger, data.altin.degisim >= 0 ? 'up' : 'down'), data.altin.degisim >= 0);
          }
        });
      } else {
        pageContent.innerHTML = `
          <div class="empty-state" style="min-height:40vh;">
            <div class="empty-icon">❌</div>
            <div class="empty-title">Piyasa Verisi Alınamadı</div>
            <div class="empty-desc">${data.error || 'Geçici bir sorun oluştu, lütfen daha sonra tekrar deneyin.'}</div>
          </div>
        `;
      }
    } catch (err) {
      pageContent.innerHTML = `
        <div class="empty-state" style="min-height:40vh;">
          <div class="empty-icon">❌</div>
          <div class="empty-title">Bağlantı Hatası</div>
          <div class="empty-desc">Piyasa verileri yüklenirken bir hata oluştu: ${err.message}</div>
        </div>
      `;
    }
  }

  function analyzeStock(symbol) {
    if (!symbol) return;
    symbol = symbol.toUpperCase().trim();
    if (!symbol) return;

    state.currentSymbol = symbol;
    state.currentPage = 'analysis';
    window.location.hash = `analysis/${symbol}`;

    // Update nav
    document.querySelectorAll('.sp-nav-link').forEach(item => {
      item.classList.toggle('active', item.dataset.page === 'analysis');
    });

    // Destroy existing charts
    StockPilotCharts.destroyAll();

    // Show loading
    pageContent.innerHTML = StockPilotAnalysis.renderAnalysisSkeleton();

    // Add to recent searches
    addToRecentSearches(symbol);

    // Try API, fallback to mock
    fetchAnalysis(symbol)
      .then(data => {
        state.analysisData = data;
        StockPilotAnalysis.renderAnalysisPage(pageContent, data);
        addToHistory(symbol, data);
      })
      .catch(() => {
        // Use mock data
        const mockData = generateMockAnalysis(symbol);
        state.analysisData = mockData;
        StockPilotAnalysis.renderAnalysisPage(pageContent, mockData);
        addToHistory(symbol, mockData);
      });

    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  // --- Recommendations ---
  function renderDailyPage() {
    pageContent.innerHTML = StockPilotRecommendations.renderRecSkeleton();
    fetchDailyRecommendations()
      .then(data => StockPilotRecommendations.renderDailyRecommendations(pageContent, data))
      .catch(() => StockPilotRecommendations.renderDailyRecommendations(pageContent, null));
  }

  function renderWeeklyPage() {
    pageContent.innerHTML = StockPilotRecommendations.renderRecSkeleton();
    fetchWeeklyRecommendations()
      .then(data => StockPilotRecommendations.renderWeeklyRecommendations(pageContent, data))
      .catch(() => StockPilotRecommendations.renderWeeklyRecommendations(pageContent, null));
  }

  // --- Watchlist ---
  function renderWatchlistPage() {
    const domains = {
      THYAO: "turkishairlines.com",
      ASELS: "aselsan.com.tr",
      GARAN: "garantibbva.com.tr",
      EREGL: "erdemir.com.tr",
      SISE: "sisecam.com.tr",
      KCHOL: "koc.com.tr",
      TUPRS: "tupras.com.tr",
      SAHOL: "sabanci.com.tr",
      AKBNK: "akbank.com",
      YKBNK: "yapikredi.com.tr",
      BIMAS: "bim.com.tr",
      TCELL: "turkcell.com.tr",
      PGSUS: "flypgs.com",
      TAVHL: "tavhavalimanlari.com.tr",
      SASA: "sasa.com.tr",
      EMPAE: "empa.com",
      EUPWR: "europowerenerji.com.tr",
      KONTR: "kontrolmatik.com",
      SMRTG: "smartgunes.com",
      GESAN: "girisimelektrik.com",
      ODAS: "odasenerji.com.tr",
      DOAS: "dogusotomotiv.com.tr",
      LOGO: "logo.com.tr",
      MPARK: "medicalpark.com.tr",
    };

    const items = state.watchlist.map(s => {
      const stock = BIST_STOCKS.find(b => b.symbol === s);
      const domain = domains[s] || (s.toLowerCase() + ".com");
      return {
        symbol: s,
        name: stock ? stock.name : '',
        price: 50 + Math.random() * 300,
        changePercent: (Math.random() - 0.45) * 8,
        action: ['AL', 'SAT', 'TUT'][Math.floor(Math.random() * 3)],
        logoUrl: `https://www.google.com/s2/favicons?sz=128&domain=${domain}`
      };
    });
    StockPilotRecommendations.renderWatchlist(pageContent, items);
  }

  function addToWatchlist(symbol) {
    if (!symbol) return;
    if (state.watchlist.includes(symbol)) {
      showToast('Bu hisse zaten takip listenizde.', 'info');
      return;
    }
    state.watchlist.push(symbol);
    saveState();
    showToast(`${symbol} takip listesine eklendi!`, 'success');
  }

  function removeFromWatchlist(symbol) {
    state.watchlist = state.watchlist.filter(s => s !== symbol);
    saveState();
    showToast(`${symbol} takip listesinden çıkarıldı.`, 'info');
    if (state.currentPage === 'watchlist') {
      renderWatchlistPage();
    }
  }

  // --- History ---
  function renderHistoryPage() {
    StockPilotRecommendations.renderHistory(pageContent, state.history);
  }

  function addToHistory(symbol, data) {
    const entry = {
      symbol: symbol,
      action: data.action || 'TUT',
      confidence: data.confidence || data.score || 0,
      date: formatTurkishDateShort(new Date()),
    };
    // Remove duplicate
    state.history = state.history.filter(h => !(h.symbol === symbol && h.date === entry.date));
    state.history.unshift(entry);
    if (state.history.length > 50) state.history = state.history.slice(0, 50);
    saveState();
  }

  function addToRecentSearches(symbol) {
    state.recentSearches = state.recentSearches.filter(s => s !== symbol);
    state.recentSearches.unshift(symbol);
    if (state.recentSearches.length > 10) state.recentSearches = state.recentSearches.slice(0, 10);
    saveState();
  }

  // --- Search ---
  function setupSearch() {
    searchInput.addEventListener('input', handleSearchInput);
    searchInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        const val = searchInput.value.toUpperCase().trim();
        if (val) {
          analyzeStock(val);
          searchInput.value = '';
          searchDropdown.classList.remove('active');
        }
      }
      if (e.key === 'Escape') {
        searchDropdown.classList.remove('active');
      }
    });

    // Close dropdown on click outside
    document.addEventListener('click', (e) => {
      if (!e.target.closest('.search-container')) {
        searchDropdown.classList.remove('active');
      }
    });
  }

  function handleSearchInput() {
    const query = searchInput.value.toUpperCase().trim();
    if (query.length === 0) {
      searchDropdown.classList.remove('active');
      return;
    }

    const results = BIST_STOCKS.filter(s =>
      s.symbol.includes(query) || s.name.toUpperCase().includes(query)
    ).slice(0, 8);

    if (results.length === 0) {
      searchDropdown.innerHTML = `
        <div style="padding:16px;text-align:center;color:var(--text-muted);font-size:0.85rem;">
          Sonuç bulunamadı
        </div>
      `;
    } else {
      searchDropdown.innerHTML = results.map(s => {
        const badgeStyle = getBadgeStyle(s.symbol);
        return `
          <div class="search-dropdown-item" onclick="window.StockPilot.analyzeStock('${s.symbol}'); document.getElementById('searchInput').value=''; document.getElementById('searchDropdown').classList.remove('active');" style="display:flex; align-items:center; gap: 10px;">
            <div style="width: 28px; height: 28px; border-radius: 6px; font-size: 0.7rem; flex-shrink: 0; ${badgeStyle}">${s.symbol.substring(0, 2)}</div>
            <div style="flex:1;">
              <span class="stock-symbol">${s.symbol}</span>
              <span class="stock-name" style="margin-left:8px;">${s.name}</span>
            </div>
            <span style="font-size:0.75rem;color:var(--text-muted);">BIST</span>
          </div>
        `;
      }).join('');
    }

    searchDropdown.classList.add('active');
  }

  function setupKeyboardNav() {
    document.addEventListener('keydown', (e) => {
      // Ctrl+K or / to focus search
      if ((e.ctrlKey && e.key === 'k') || (e.key === '/' && document.activeElement.tagName !== 'INPUT')) {
        e.preventDefault();
        searchInput.focus();
      }
    });
  }

  // --- Sidebar ---
  function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebarOverlay');
    state.sidebarOpen = !state.sidebarOpen;
    sidebar.classList.toggle('open', state.sidebarOpen);
    overlay.classList.toggle('active', state.sidebarOpen);
  }

  function closeSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebarOverlay');
    state.sidebarOpen = false;
    sidebar.classList.remove('open');
    overlay.classList.remove('active');
  }

  // Setup overlay click
  document.addEventListener('DOMContentLoaded', () => {
    const overlay = document.getElementById('sidebarOverlay');
    if (overlay) {
      overlay.addEventListener('click', closeSidebar);
    }
  });

  // --- Time Display ---
  function updateTimeDisplay() {
    const el = document.getElementById('timeDisplay');
    if (!el) return;
    const now = new Date();
    const h = String(now.getHours()).padStart(2, '0');
    const m = String(now.getMinutes()).padStart(2, '0');
    const s = String(now.getSeconds()).padStart(2, '0');
    el.textContent = `${h}:${m}:${s}`;
  }

  // --- WEBSOCKET — Anlık Canlı Veri ---
  function connectWebSocket() {
    try {
      // Sunucuya WebSocket bağlantısı
      const socket = io(window.location.origin, {
        transports: ['websocket', 'polling'],
        reconnection: true,
        reconnectionDelay: 2000
      });

      socket.on('connect', () => {
        console.log('[WS] Bağlandı — canlı veri akışı aktif');
      });

      socket.on('market_update', (data) => {
        // Topbar ticker'ları güncelle
        if (data.bist) {
          const bv = document.getElementById('bistValue');
          const bc = document.getElementById('bistChange');
          if (bv) bv.textContent = formatNumber(data.bist.deger);
          if (bc) {
            const p = data.bist.degisim_yuzde >= 0 ? '+' : '';
            bc.textContent = `${p}${data.bist.degisim_yuzde.toFixed(2)}%`;
            bc.className = `sp-ticker-change ${data.bist.degisim_yuzde >= 0 ? 'up' : 'down'}`;
          }
        }
        if (data.usd) {
          const uv = document.getElementById('usdValue');
          const uc = document.getElementById('usdChange');
          if (uv) uv.textContent = '₺' + formatNumber(data.usd.deger);
          if (uc) {
            const p = data.usd.degisim_yuzde >= 0 ? '+' : '';
            uc.textContent = `${p}${data.usd.degisim_yuzde.toFixed(2)}%`;
            uc.className = `sp-ticker-change ${data.usd.degisim_yuzde >= 0 ? 'up' : 'down'}`;
          }
        }
        if (data.altin) {
          const gv = document.getElementById('goldValue');
          const gc = document.getElementById('goldChange');
          if (gv) gv.textContent = '₺' + formatNumber(data.altin.deger);
          if (gc) {
            const p = data.altin.degisim_yuzde >= 0 ? '+' : '';
            gc.textContent = `${p}${data.altin.degisim_yuzde.toFixed(2)}%`;
            gc.className = `sp-ticker-change ${data.altin.degisim_yuzde >= 0 ? 'up' : 'down'}`;
          }
        }

        // Dashboard kartlarını güncelle (eğer dashboard açıksa)
        if (state.currentPage === 'dashboard') {
          if (data.bist) {
            const db = document.getElementById('dashBistValue');
            const dc = document.getElementById('dashBistChange');
            if (db) db.textContent = formatNumber(data.bist.deger);
            if (dc) {
              const p = data.bist.degisim_yuzde >= 0 ? '▲ +' : '▼ ';
              dc.textContent = `${p}${Math.abs(data.bist.degisim_yuzde).toFixed(2)}%`;
              dc.className = `market-change-label ${data.bist.degisim_yuzde >= 0 ? 'up' : 'down'}`;
            }
          }
          if (data.usd) {
            const du = document.getElementById('dashUsdValue');
            const dc = document.getElementById('dashUsdChange');
            if (du) du.textContent = '₺' + formatNumber(data.usd.deger);
            if (dc) {
              const p = data.usd.degisim_yuzde >= 0 ? '▲ +' : '▼ ';
              dc.textContent = `${p}${Math.abs(data.usd.degisim_yuzde).toFixed(2)}%`;
              dc.className = `market-change-label ${data.usd.degisim_yuzde >= 0 ? 'up' : 'down'}`;
            }
          }
          if (data.eur) {
            const de = document.getElementById('dashEurValue');
            const dc = document.getElementById('dashEurChange');
            if (de) de.textContent = '₺' + formatNumber(data.eur.deger);
            if (dc) {
              const p = data.eur.degisim_yuzde >= 0 ? '▲ +' : '▼ ';
              dc.textContent = `${p}${Math.abs(data.eur.degisim_yuzde).toFixed(2)}%`;
              dc.className = `market-change-label ${data.eur.degisim_yuzde >= 0 ? 'up' : 'down'}`;
            }
          }
          if (data.altin) {
            const dg = document.getElementById('dashGoldValue');
            const dc = document.getElementById('dashGoldChange');
            if (dg) dg.textContent = '₺' + formatNumber(data.altin.deger);
            if (dc) {
              const p = data.altin.degisim_yuzde >= 0 ? '▲ +' : '▼ ';
              dc.textContent = `${p}${Math.abs(data.altin.degisim_yuzde).toFixed(2)}%`;
              dc.className = `market-change-label ${data.altin.degisim_yuzde >= 0 ? 'up' : 'down'}`;
            }
          }
        }
      });

      socket.on('signal_alert', (signal) => {
        if (!signal || !signal.type || signal.type === 'TUT') return;
        const emoji = signal.type === 'AL' ? '🟢' : '🔴';
        const msg = `${emoji} ${signal.symbol}: ${signal.type} (%${signal.confidence})`;
        showToast(msg, signal.type === 'AL' ? 'success' : 'error');
        // Dashboard sinyal panelini de guncelle
        if (typeof loadDashboardSignals === 'function') loadDashboardSignals();
      });

      socket.on('disconnect', () => {
        console.log('[WS] Bağlantı koptu — yeniden bağlanıyor...');
        // Fallback: 60 saniyede bir API'den çek
        setTimeout(() => {
          if (!socket.connected) updateBistIndicator();
        }, 10000);
      });

      // Socket referansını sakla
      window._wsSocket = socket;
    } catch (e) {
      console.log('[WS] Socket.IO yüklenemedi, polling kullanılıyor:', e.message);
      // Fallback: 60 saniyede bir polling
      setInterval(updateBistIndicator, 60000);
    }
  }

  // --- BIST Indicator & Live Dashboard Prices ---
  async function updateBistIndicator() {
    try {
      const res = await fetch('/api/market-overview');
      const data = await res.json();
      if (data.success) {
        // Topbar BIST 100
        if (data.xu100) {
          const val = document.getElementById('bistValue');
          const chg = document.getElementById('bistChange');
          if (val) val.textContent = formatNumber(data.xu100.deger);
          if (chg) {
            const prefix = data.xu100.degisim >= 0 ? '+' : '';
            chg.textContent = `${prefix}${data.xu100.degisim_yuzde.toFixed(2)}%`;
            chg.className = `sp-ticker-change ${data.xu100.degisim >= 0 ? 'up' : 'down'}`;
          }
        }
        // Topbar USD/TRY
        if (data.usdtry) {
          const uv = document.getElementById('usdValue');
          const uc = document.getElementById('usdChange');
          if (uv) uv.textContent = '₺' + formatNumber(data.usdtry.deger);
          if (uc) {
            const prefix = data.usdtry.degisim >= 0 ? '+' : '';
            uc.textContent = `${prefix}${data.usdtry.degisim_yuzde.toFixed(2)}%`;
            uc.className = `sp-ticker-change ${data.usdtry.degisim >= 0 ? 'up' : 'down'}`;
          }
        }
        // Topbar ALTIN
        if (data.altin) {
          const gv = document.getElementById('goldValue');
          const gc = document.getElementById('goldChange');
          if (gv) gv.textContent = '₺' + formatNumber(data.altin.deger);
          if (gc) {
            const prefix = data.altin.degisim >= 0 ? '+' : '';
            gc.textContent = `${prefix}${data.altin.degisim_yuzde.toFixed(2)}%`;
            gc.className = `sp-ticker-change ${data.altin.degisim >= 0 ? 'up' : 'down'}`;
          }
        }
        
        // Dashboard cards
        if (state.currentPage === 'dashboard') {
          if (data.xu100) {
            const dbVal = document.getElementById('dashBistValue');
            const dbChg = document.getElementById('dashBistChange');
            if (dbVal) dbVal.textContent = formatNumber(data.xu100.deger);
            if (dbChg) {
              const prefix = data.xu100.degisim >= 0 ? '▲ +' : '▼ ';
              dbChg.textContent = `${prefix}${Math.abs(data.xu100.degisim_yuzde).toFixed(2)}%`;
              dbChg.className = `market-change-label ${data.xu100.degisim >= 0 ? 'up' : 'down'}`;
            }
          }
          if (data.usdtry) {
            const duVal = document.getElementById('dashUsdValue');
            const duChg = document.getElementById('dashUsdChange');
            if (duVal) duVal.textContent = '₺' + formatNumber(data.usdtry.deger);
            if (duChg) {
              const prefix = data.usdtry.degisim >= 0 ? '▲ +' : '▼ ';
              duChg.textContent = `${prefix}${Math.abs(data.usdtry.degisim_yuzde).toFixed(2)}%`;
              duChg.className = `market-change-label ${data.usdtry.degisim >= 0 ? 'up' : 'down'}`;
            }
          }
          if (data.eurtry) {
            const deVal = document.getElementById('dashEurValue');
            const deChg = document.getElementById('dashEurChange');
            if (deVal) deVal.textContent = '₺' + formatNumber(data.eurtry.deger);
            if (deChg) {
              const prefix = data.eurtry.degisim >= 0 ? '▲ +' : '▼ ';
              deChg.textContent = `${prefix}${Math.abs(data.eurtry.degisim_yuzde).toFixed(2)}%`;
              deChg.className = `market-change-label ${data.eurtry.degisim >= 0 ? 'up' : 'down'}`;
            }
          }
          if (data.altin) {
            const dgVal = document.getElementById('dashGoldValue');
            const dgChg = document.getElementById('dashGoldChange');
            if (dgVal) dgVal.textContent = '₺' + formatNumber(data.altin.deger);
            if (dgChg) {
              const prefix = data.altin.degisim >= 0 ? '▲ +' : '▼ ';
              dgChg.textContent = `${prefix}${Math.abs(data.altin.degisim_yuzde).toFixed(2)}%`;
              dgChg.className = `market-change-label ${data.altin.degisim >= 0 ? 'up' : 'down'}`;
            }
          }
        }
      }
    } catch (e) { /* ignore */ }
  }

  // --- Theme Swapper ---
  function toggleTheme() {
    const newTheme = state.theme === 'dark' ? 'light' : 'dark';
    state.theme = newTheme;
    
    document.body.classList.toggle('light-theme', newTheme === 'light');
    document.body.classList.toggle('dark-theme', newTheme === 'dark');
    
    localStorage.setItem('stockpilot_theme', newTheme);
    
    // Also notify charts if needed
    if (window.StockPilotCharts && typeof StockPilotCharts.updateChartsTheme === 'function') {
      StockPilotCharts.updateChartsTheme(newTheme);
    }
    
    showToast(`Tema değiştirildi: ${newTheme === 'dark' ? 'Siyah' : 'Beyaz'}`, 'info');
  }

  // --- Toast Notifications ---
  function showToast(message, type) {
    type = type || 'info';
    const container = document.getElementById('toastContainer');
    const icons = { success: '✅', error: '❌', info: 'ℹ️' };

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
      <span class="toast-icon">${icons[type] || 'ℹ️'}</span>
      <span>${message}</span>
    `;

    container.appendChild(toast);

    setTimeout(() => {
      toast.classList.add('fade-out');
      setTimeout(() => toast.remove(), 300);
    }, 3500);
  }

  function formatVolume(num) {
    if (!num) return '—';
    if (num >= 1000000) {
      return (num / 1000000).toFixed(2) + 'M';
    }
    if (num >= 1000) {
      return (num / 1000).toFixed(2) + 'K';
    }
    return num.toString();
  }

  // --- API Helpers ---
  async function fetchAnalysis(symbol) {
    const res = await fetch(`/api/analyze/${symbol}`);
    if (!res.ok) throw new Error('API error');
    const data = await res.json();
    
    if (data.success) {
      return {
        success: true,
        symbol: data.symbol.replace('.IS', ''),
        name: data.isim || data.symbol.replace('.IS', ''),
        price: data.teknik.fiyat.guncel_fiyat,
        change: data.teknik.fiyat.degisim,
        changePercent: data.teknik.fiyat.degisim_yuzde,
        score: data.oneri.skor,
        action: data.oneri.aksiyon,
        confidence: data.oneri.guven,
        risk: data.oneri.risk_seviyesi || 'Orta',
        summary: data.oneri.ozet || '',
        buyReasons: data.oneri.nedenler_al,
        sellReasons: data.oneri.nedenler_sat,
        technical: {
          rsi: data.teknik.rsi.deger,
          macd: data.teknik.macd.macd,
          macdSignal: data.teknik.macd.yorum,
          bollinger: data.teknik.bollinger.ust_bant,
          bollingerSignal: data.teknik.bollinger.sinyal,
          smaStatus: data.teknik.sma.sma_50,
          smaSignal: data.teknik.sma.sinyal,
          adx: data.teknik.adx.deger,
          adxSignal: data.teknik.adx.sinyal,
          stochastic: data.teknik.stochastic.k,
          stochasticSignal: data.teknik.stochastic.sinyal,
          volume: formatVolume(data.teknik.hacim.guncel),
          volumeSignal: data.teknik.hacim.sinyal,
          atr: data.teknik.atr != null ? data.teknik.atr : "—",
          atrSignal: "Volatilite"
        },
        supportResistance: {
          levels: [
            { label: 'Direnç 2', value: data.teknik.destek_direnc.direnc_2, type: 'resistance' },
            { label: 'Direnç 1', value: data.teknik.destek_direnc.direnc_1, type: 'resistance' },
            { label: 'Pivot', value: data.teknik.destek_direnc.pivot, type: 'pivot' },
            { label: 'Destek 1', value: data.teknik.destek_direnc.destek_1, type: 'support' },
            { label: 'Destek 2', value: data.teknik.destek_direnc.destek_2, type: 'support' }
          ]
        },
        logoUrl: data.logo_url,
        sentiment: {
          overall: (data.duygu.genel_skor + 1) / 2, // Convert -1..1 to 0..1
          simulasyon: data.duygu.simulasyon_kullanildi || false,
          articles: data.duygu.haberler ? data.duygu.haberler.map(a => ({
            title: a.baslik,
            source: a.kaynak,
            score: (a.skor + 1) / 2,
            isComment: a.is_comment || false
          })) : []
        },
        priceTargets: data.oneri.fiyat_hedefleri || {},
        fibonacci: data.teknik.fibonacci || {},
        tarih: data.tarih,
        chartData: null // loaded by chart-data endpoint
      };
    }
    return data;
  }

  async function fetchDailyRecommendations() {
    const res = await fetch('/api/recommend/daily');
    if (!res.ok) throw new Error('API error');
    const data = await res.json();
    if (data.success && data.oneriler) {
      return {
        success: true,
        date: data.tarih,
        recommendations: data.oneriler.map(r => ({
          symbol: r.symbol.replace('.IS', ''),
          name: r.name,
          action: r.action,
          confidence: r.confidence,
          score: r.score,
          reason: r.reason,
          price: r.fiyat,
          changePercent: r.degisim_yuzde,
          fiyat_hedefleri: r.fiyat_hedefleri,
          logoUrl: r.logo_url
        }))
      };
    }
    return data;
  }

  async function fetchWeeklyRecommendations() {
    const res = await fetch('/api/recommend/weekly');
    if (!res.ok) throw new Error('API error');
    const data = await res.json();
    if (data.success && data.oneriler) {
      return {
        success: true,
        date: data.tarih,
        recommendations: data.oneriler.map(r => ({
          symbol: r.symbol.replace('.IS', ''),
          name: r.name,
          action: r.action,
          confidence: r.confidence,
          score: r.score,
          reason: r.reason,
          price: r.fiyat,
          changePercent: r.degisim_yuzde,
          fiyat_hedefleri: r.fiyat_hedefleri,
          logoUrl: r.logo_url
        }))
      };
    }
    return data;
  }

  // --- Mock Data Generator ---
  function generateMockAnalysis(symbol) {
    const stock = BIST_STOCKS.find(s => s.symbol === symbol);
    const price = 30 + Math.random() * 400;
    const changePercent = (Math.random() - 0.45) * 8;
    const change = price * changePercent / 100;
    const score = Math.floor(25 + Math.random() * 65);
    const action = score >= 65 ? 'AL' : score <= 35 ? 'SAT' : 'TUT';

    return {
      symbol: symbol,
      name: stock ? stock.name : symbol + ' A.Ş.',
      price: parseFloat(price.toFixed(2)),
      change: parseFloat(change.toFixed(2)),
      changePercent: parseFloat(changePercent.toFixed(2)),
      score: score,
      action: action,
      confidence: score,
      risk: score >= 60 ? 'Düşük' : score <= 35 ? 'Yüksek' : 'Orta',
      summary: '',
      buyReasons: [
        'RSI göstergesi toparlanma sinyali veriyor',
        '50 günlük hareketli ortalama destek görevi görüyor',
        'İşlem hacminde artış dikkat çekiyor',
        'Sektörel bazda olumlu gelişmeler mevcut',
      ],
      sellReasons: [
        'Kısa vadeli direnç seviyesine yaklaşıldı',
        'MACD histogramı zayıflama eğiliminde',
        'Genel piyasa volatilitesi yüksek seyrediyor',
      ],
      technical: {
        rsi: Math.floor(25 + Math.random() * 55),
        macd: (Math.random() * 2 - 1).toFixed(3),
        macdSignal: Math.random() > 0.5 ? 'AL' : 'SAT',
        bollinger: ['Alt Bant', 'Orta', 'Üst Bant'][Math.floor(Math.random() * 3)],
        bollingerSignal: Math.random() > 0.5 ? 'AL' : 'Nötr',
        smaStatus: Math.random() > 0.5 ? 'Üstünde' : 'Altında',
        smaSignal: Math.random() > 0.5 ? 'AL' : 'SAT',
        adx: Math.floor(15 + Math.random() * 35),
        adxSignal: Math.random() > 0.5 ? 'Güçlü' : 'Zayıf',
        stochastic: Math.floor(20 + Math.random() * 60),
        stochasticSignal: 'Nötr',
        volume: (Math.random() * 10).toFixed(1) + 'M',
        volumeSignal: 'Normal',
        atr: (Math.random() * 5).toFixed(2),
        atrSignal: 'Orta',
      },
      supportResistance: {
        levels: [
          { label: 'Direnç 3', value: parseFloat((price * 1.12).toFixed(2)), type: 'resistance' },
          { label: 'Direnç 2', value: parseFloat((price * 1.08).toFixed(2)), type: 'resistance' },
          { label: 'Direnç 1', value: parseFloat((price * 1.04).toFixed(2)), type: 'resistance' },
          { label: 'Destek 1', value: parseFloat((price * 0.96).toFixed(2)), type: 'support' },
          { label: 'Destek 2', value: parseFloat((price * 0.92).toFixed(2)), type: 'support' },
          { label: 'Destek 3', value: parseFloat((price * 0.88).toFixed(2)), type: 'support' },
        ],
      },
      sentiment: {
        overall: 0.35 + Math.random() * 0.4,
        simulasyon: true,
        articles: [
          { title: `${symbol} hissesinde yatırımcılar yeni gelişmeleri takip ediyor`, source: 'Bloomberg HT', score: 0.7, isComment: false },
          { title: `${symbol} için analist değerlendirmeleri karışık sinyaller veriyor`, source: 'Ekonomist', score: 0.5, isComment: false },
          { title: `${stock ? stock.name : symbol} sektöründe rekabet artıyor`, source: 'Dünya Gazetesi', score: 0.4, isComment: false },
          { title: `BIST'te ${symbol} hareketliliği devam ediyor`, source: 'Anadolu Ajansı', score: 0.65, isComment: false },
          { title: `${symbol} bu fiyatlardan toplanır bence, orta vadeli hedefim yüksek.`, source: 'Investing Yorumu', score: 0.8, isComment: true },
          { title: `Teknik olarak RSI aşırı satım bölgesinden döndü, tepki yükselişi başladı.`, source: 'Borsa Forumu', score: 0.75, isComment: true },
          { title: `Endeks bozmazsa bu kağıdın önü açık. Hedef 2x.`, source: 'Sosyal Medya Yorumu', score: 0.7, isComment: true }
        ],
      },
      priceTargets: {
        basarili: true,
        giris_fiyati: parseFloat((price * 0.98).toFixed(2)),
        hedef_1: parseFloat((price * 1.05).toFixed(2)),
        hedef_1_kar_yuzde: 5.0,
        hedef_2: parseFloat((price * 1.12).toFixed(2)),
        hedef_2_kar_yuzde: 12.0,
        stop_loss: parseFloat((price * 0.94).toFixed(2)),
        zarar_yuzde: -6.0,
        risk_odul_orani: 1.83,
        atr: parseFloat((price * 0.02).toFixed(2))
      },
      fibonacci: {
        swing_yuksek: parseFloat((price * 1.15).toFixed(2)),
        swing_dusuk: parseFloat((price * 0.85).toFixed(2)),
        trend_yonu: action === 'AL' ? 'Yükseliş' : 'Düşüş',
        bolge: 'Altın Oran Bölgesi (0.618-0.786)',
        seviye_0: parseFloat((price * 1.15).toFixed(2)),
        seviye_0236: parseFloat((price * 1.08).toFixed(2)),
        seviye_0382: parseFloat((price * 1.035).toFixed(2)),
        seviye_0500: parseFloat((price * 1.0).toFixed(2)),
        seviye_0618: parseFloat((price * 0.965).toFixed(2)),
        seviye_0786: parseFloat((price * 0.91).toFixed(2)),
        seviye_1: parseFloat((price * 0.85).toFixed(2))
      },
      tarih: formatTurkishDateShort(new Date())
    };
  }

  // --- Persistence ---
  function saveState() {
    try {
      localStorage.setItem('stockpilot_watchlist', JSON.stringify(state.watchlist));
      localStorage.setItem('stockpilot_history', JSON.stringify(state.history));
      localStorage.setItem('stockpilot_recent', JSON.stringify(state.recentSearches));
    } catch (e) { /* ignore */ }
  }

  function loadState() {
    try {
      const wl = localStorage.getItem('stockpilot_watchlist');
      if (wl) {
        const parsed = JSON.parse(wl);
        if (Array.isArray(parsed)) state.watchlist = parsed;
      }
      const hist = localStorage.getItem('stockpilot_history');
      if (hist) {
        const parsed = JSON.parse(hist);
        if (Array.isArray(parsed)) state.history = parsed;
      }
      const recent = localStorage.getItem('stockpilot_recent');
      if (recent) {
        const parsed = JSON.parse(recent);
        if (Array.isArray(parsed)) state.recentSearches = parsed;
      }
    } catch (e) { /* ignore */ }
  }

  // --- Helpers ---
  function getActionBadgeClass(action) {
    const a = (action || '').toUpperCase();
    if (a === 'AL') return 'badge-al';
    if (a === 'SAT') return 'badge-sat';
    return 'badge-tut';
  }

  function formatNumber(num) {
    if (num === null || num === undefined) return '—';
    return Number(num).toLocaleString('tr-TR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  function formatTurkishDateShort(date) {
    const d = String(date.getDate()).padStart(2, '0');
    const m = String(date.getMonth() + 1).padStart(2, '0');
    const y = date.getFullYear();
    const h = String(date.getHours()).padStart(2, '0');
    const min = String(date.getMinutes()).padStart(2, '0');
    return `${d}.${m}.${y} ${h}:${min}`;
  }

  // --- Dashboard Fund Widget ---
  function renderDashboardFunds(fData) {
    const widget = document.getElementById('dashFundsWidget');
    if (!widget) return;

    const funds = fData.fonlar || [];
    // En yüksek getirili 3 fonu göster (PHE, PBR, TLY öncelikli)
    const priorityCodes = ['PHE', 'PBR', 'TLY'];
    const priority = funds.filter(f => priorityCodes.includes(f.kod));
    const others = funds.filter(f => !priorityCodes.includes(f.kod) && f.fiyat > 0)
      .sort((a, b) => b.degisim_yuzde - a.degisim_yuzde);
    const topFunds = [...priority, ...others].slice(0, 3);

    const renderMiniFund = (f) => {
      const isUp = f.degisim >= 0;
      const chgIcon = isUp ? '▲' : '▼';
      const chgClass = isUp ? 'up' : 'down';
      return `
        <div class="glass-card dash-fund-card" onclick="window.StockPilot.navigate('funds')" style="cursor:pointer;">
          <div class="flex justify-between items-center mb-8">
            <span class="fund-code-badge" style="font-size:0.72rem;padding:3px 8px;">${f.kod}</span>
            <span class="fund-change ${chgClass}" style="font-size:0.72rem;">${chgIcon} ${f.degisim_yuzde.toFixed(2)}%</span>
          </div>
          <div style="font-size:0.78rem;color:var(--text-secondary);margin-bottom:4px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${f.kurum || ''}</div>
          <div style="font-size:1.3rem;font-weight:700;color:var(--text-primary);">₺${formatNumber(f.fiyat)}</div>
          <div style="font-size:0.72rem;color:var(--text-muted);margin-top:4px;">${f.tur}</div>
        </div>
      `;
    };

    widget.innerHTML = `
      <div class="grid-3">
        ${topFunds.map(renderMiniFund).join('')}
        ${topFunds.length === 0 ? '<div class="glass-card" style="padding:24px;text-align:center;color:var(--text-muted);">Fon verisi yüklenemedi</div>' : ''}
      </div>
    `;
  }

  // --- Init on DOM Ready ---
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // --- Public API ---
  return {
    navigate,
    analyzeStock,
    addToWatchlist,
    removeFromWatchlist,
    toggleSidebar,
    showToast,
    toggleTheme,
    state,
  };
})();
