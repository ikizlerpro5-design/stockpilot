/* ============================================
   StockPilot — Analysis Page Renderer (V2 — modern, theme-consistent)
   ============================================ */

window.StockPilotAnalysis = (function () {
  'use strict';

  /**
   * Render the full analysis page.
   */
  function renderAnalysisPage(container, data) {
    if (!data) {
      container.innerHTML = renderEmptyAnalysis();
      return;
    }

    const changeUp = (data.change || 0) >= 0;
    const changeClass = changeUp ? 'up' : 'down';
    const changeIcon = changeUp ? '▲' : '▼';
    const actionBadgeClass = getActionBadgeClass(data.action);
    const gaugeId = 'gauge-canvas-' + Date.now();
    const scoreColor = getScoreColor(data.score);
    const conf = (data.confidence != null ? data.confidence : data.score) || 0;
    const risk = data.risk || '—';

    container.innerHTML = `
      <!-- ===== HERO + VERDICT (compact) ===== -->
      <div class="an-hero glass-card-static anim-fade-in">
        <div class="an-hero-identity">
          ${renderLogo(data)}
          <div class="an-hero-titles">
            <div class="an-hero-symbol">${data.symbol}<span class="an-exchange-tag">BIST</span></div>
            <div class="an-hero-name">${data.name || 'Borsa İstanbul'}</div>
          </div>
        </div>
        <div class="an-hero-price">
          <div class="an-price-value">₺${formatNumber(data.price)}</div>
          <div class="an-price-change ${changeClass}">
            ${changeIcon} ₺${formatNumber(Math.abs(data.change || 0))}
            <span>(${changeUp ? '+' : ''}${(data.changePercent || 0).toFixed(2)}%)</span>
          </div>
        </div>
        <div class="an-hero-badges">
          <span class="badge badge-lg ${actionBadgeClass}">${data.action || 'TUT'}</span>
          <span class="an-hero-score" style="color:${scoreColor}">Skor: ${Math.round(data.score)}</span>
        </div>
      </div>

      <!-- ===== CHART ===== -->
      <div class="an-section anim-fade-in stagger-1">
        <div class="an-chart-toolbar">
          <span class="an-chart-title">📈 Fiyat Grafiği</span>
          <div class="an-period-group">
            ${['1M','3M','6M','1Y','ALL'].map((p, i) => `
              <button class="an-period-btn ${p === '6M' ? 'active' : ''}" data-period="${p}"
                onclick="window.StockPilotAnalysis.changePeriod(this, '${data.symbol}')">
                ${({ '1M':'1A','3M':'3A','6M':'6A','1Y':'1Y','ALL':'Tümü' })[p]}
              </button>`).join('')}
          </div>
        </div>
        <div class="an-chart" id="mainChart"></div>
      </div>

      <!-- ===== KEY METRICS: Gauge + Price Targets ===== -->
      <div class="an-metrics-row anim-fade-in stagger-2">
        <div class="an-gauge-mini glass-card-static">
          <canvas id="${gaugeId}" class="an-gauge-canvas" width="300" height="180"></canvas>
          <div class="an-gauge-center">
            <div class="an-gauge-score" style="color:${scoreColor}">${Math.round(data.score)}</div>
            <span class="badge ${actionBadgeClass}">${data.action || 'TUT'}</span>
          </div>
        </div>
        <div class="an-targets-mini glass-card-static">
          <div class="section-header"><h2 class="section-title"><span class="icon">🎯</span> Fiyat Hedefleri</h2></div>
          ${renderPriceTargets(data.priceTargets, data.price)}
          <div style="margin-top:12px;font-size:0.7rem;color:var(--text-muted)">
            Risk: <b class="${getRiskClass(risk)}">${risk}</b> &nbsp;|&nbsp; Güven: <b>%${conf}</b> &nbsp;|&nbsp; 🕒 ${data.tarih || '—'}
          </div>
        </div>
      </div>

      <!-- ===== DEPTH / DERINLIK ===== -->
      <div class="an-section anim-fade-in stagger-3" id="depthSection">
        <div class="section-header"><h2 class="section-title"><span class="icon">📚</span> Emir Defteri — 25 Kademe Derinlik</h2></div>
        <div id="depthContent"><div class="an-empty-inline">⏳ Derinlik verisi yükleniyor...</div></div>
      </div>

      <!-- ===== TECHNICAL INDICATORS ===== -->
      <div class="an-section anim-fade-in stagger-4">
        <div class="section-header"><h2 class="section-title"><span class="icon">📊</span> Teknik Göstergeler</h2></div>
        <div class="an-indicators">${renderTechnicalCards(data.technical || {})}</div>
      </div>

      <!-- ===== SUPPORT/RESISTANCE + FIBONACCI ===== -->
      <div class="an-section anim-fade-in stagger-5">
        <div class="section-header"><h2 class="section-title"><span class="icon">📐</span> Destek, Direnç &amp; Fibonacci</h2></div>
        <div class="an-sr-grid">
          <div class="glass-card-static">
            <h3 class="an-subhead">📐 Klasik Destek / Direnç</h3>
            ${renderSupportResistance(data.supportResistance || {}, data.price)}
          </div>
          <div class="glass-card-static">
            <h3 class="an-subhead">📈 Fibonacci Geri Çekilme</h3>
            ${renderFibonacciTable(data.fibonacci || {})}
          </div>
        </div>
      </div>

      <!-- ===== REASONS ===== -->
      <div class="an-section anim-fade-in stagger-6">
        <div class="section-header"><h2 class="section-title"><span class="icon">📋</span> Alım / Satım Gerekçeleri</h2></div>
        <div class="an-reasons-row">
          <div class="an-reason-card buy">
            <div class="an-reason-head"><span class="an-reason-icon">✅</span> Alım Gerekçeleri</div>
            <div class="an-reason-list">${renderReasons(data.buyReasons, 'buy')}</div>
          </div>
          <div class="an-reason-card sell">
            <div class="an-reason-head"><span class="an-reason-icon">⚠️</span> Risk &amp; Satış Gerekçeleri</div>
            <div class="an-reason-list">${renderReasons(data.sellReasons, 'sell')}</div>
          </div>
        </div>
      </div>

      <!-- ===== NEWS & SENTIMENT ===== -->
      <div class="an-section anim-fade-in stagger-7">
        <div class="section-header"><h2 class="section-title"><span class="icon">📰</span> Haberler &amp; Duyarlılık</h2></div>
        ${renderNewsSentiment(data.sentiment || {})}
      </div>
    `;

    // Draw gauge + chart after DOM is ready
    requestAnimationFrame(() => {
      drawGauge(gaugeId, data.score, data.action);
      initChart(data);
      loadDepthData(data.symbol);
    });
  }

  /** Toggle the methodology explainer panel. */
  function toggleMethodology() {
    const el = document.getElementById('methodologyDetails');
    if (!el) return;
    el.style.display = el.style.display === 'none' ? 'block' : 'none';
  }

  /** Render the stock logo / fallback badge. */
  function renderLogo(data) {
    const initials = (data.symbol || 'BI').substring(0, 2);
    const badgeStyle = getBadgeStyle(data.symbol);
    if (data.logoUrl) {
      return `<div class="an-logo">
          <img src="${data.logoUrl}" alt="${data.symbol}"
               onerror="this.parentElement.classList.add('an-logo-fallback'); this.parentElement.setAttribute('style','${badgeStyle}'); this.parentElement.textContent='${initials}';">
        </div>`;
    }
    return `<div class="an-logo an-logo-fallback" style="${badgeStyle}">${initials}</div>`;
  }

  /**
   * Generate a unique gradient background for a stock badge based on its symbol hash.
   */
  function getBadgeStyle(symbol) {
    const s = symbol || 'BIST';
    let hash = 0;
    for (let i = 0; i < s.length; i++) {
      hash = s.charCodeAt(i) + ((hash << 5) - hash);
    }
    const h1 = Math.abs(hash % 360);
    const h2 = (h1 + 50) % 360;
    return `background: linear-gradient(135deg, hsl(${h1}, 45%, 42%), hsl(${h2}, 50%, 30%)); color:#fff; font-weight:700;`;
  }

  /**
   * Initialize main chart with data.
   */
  function initChart(data) {
    const chartContainer = document.getElementById('mainChart');
    if (!chartContainer) return;

    chartContainer.innerHTML = `<div class="an-chart-loading"><span class="shimmer"></span></div>`;

    loadChart(data.symbol, '6mo', data.price);
  }

  function loadChart(symbol, apiPeriod, fallbackPrice) {
    fetch(`/api/chart-data/${symbol}?period=${apiPeriod}`)
      .then(res => res.json())
      .then(resData => {
        if (resData.success && resData.data && resData.data.length > 0) {
          const candleData = resData.data.map((d, index) => {
            const volItem = resData.volume ? resData.volume[index] : null;
            return { ...d, volume: volItem ? volItem.value : 0 };
          });
          StockPilotCharts.createStockChart('mainChart', candleData, resData.sma50, resData.sma200);
        } else if (fallbackPrice) {
          renderMockChart(fallbackPrice);
        }
      })
      .catch(() => { if (fallbackPrice) renderMockChart(fallbackPrice); });
  }

  function renderMockChart(price) {
    const candleData = StockPilotCharts.generateMockCandleData(60, price * 0.9);
    const sma50 = StockPilotCharts.calculateSMA(candleData, 10);
    const sma200 = StockPilotCharts.calculateSMA(candleData, 30);
    StockPilotCharts.createStockChart('mainChart', candleData, sma50, sma200);
  }

  /**
   * Handle chart period change.
   */
  function changePeriod(btn, symbol) {
    document.querySelectorAll('.an-period-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    const periodMap = { '1M': '1mo', '3M': '3mo', '6M': '6mo', '1Y': '1y', 'ALL': '2y' };
    loadChart(symbol, periodMap[btn.dataset.period] || '6mo', null);
  }

  /**
   * Draw the gauge/speedometer on a canvas.
   */
  function drawGauge(canvasId, score, action) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;
    const displayWidth = canvas.clientWidth || 520;
    const displayHeight = canvas.clientHeight || 290;
    canvas.width = displayWidth * dpr;
    canvas.height = displayHeight * dpr;
    ctx.scale(dpr, dpr);

    const cx = displayWidth / 2;
    const cy = displayHeight - 18;
    const radius = Math.min(cx - 18, cy - 18);
    const lineWidth = 16;
    const startAngle = Math.PI;
    const endAngle = 2 * Math.PI;

    // Background arc
    ctx.beginPath();
    ctx.arc(cx, cy, radius, startAngle, endAngle);
    ctx.strokeStyle = 'rgba(160, 160, 180, 0.12)';
    ctx.lineWidth = lineWidth;
    ctx.lineCap = 'round';
    ctx.stroke();

    // Gradient arc (Slate → Silver → Gold)
    const gradient = ctx.createLinearGradient(cx - radius, cy, cx + radius, cy);
    gradient.addColorStop(0, '#5a6478');
    gradient.addColorStop(0.5, '#aab3c4');
    gradient.addColorStop(1, '#c5a880');

    const scoreAngle = startAngle + (Math.max(0, Math.min(100, score)) / 100) * Math.PI;

    ctx.beginPath();
    ctx.arc(cx, cy, radius, startAngle, scoreAngle);
    ctx.strokeStyle = gradient;
    ctx.lineWidth = lineWidth;
    ctx.lineCap = 'round';
    ctx.stroke();

    // Glow
    ctx.beginPath();
    ctx.arc(cx, cy, radius, startAngle, scoreAngle);
    ctx.strokeStyle = gradient;
    ctx.lineWidth = lineWidth + 8;
    ctx.lineCap = 'round';
    ctx.globalAlpha = 0.12;
    ctx.stroke();
    ctx.globalAlpha = 1;

    // Needle dot
    const needleX = cx + radius * Math.cos(scoreAngle);
    const needleY = cy + radius * Math.sin(scoreAngle);
    const col = getScoreColor(score);

    ctx.beginPath();
    ctx.arc(needleX, needleY, 7, 0, 2 * Math.PI);
    ctx.fillStyle = col;
    ctx.fill();

    ctx.beginPath();
    ctx.arc(needleX, needleY, 13, 0, 2 * Math.PI);
    ctx.fillStyle = col;
    ctx.globalAlpha = 0.22;
    ctx.fill();
    ctx.globalAlpha = 1;

    // Tick marks
    for (let i = 0; i <= 10; i++) {
      const angle = startAngle + (i / 10) * Math.PI;
      const innerR = radius - lineWidth / 2 - 8;
      const outerR = radius - lineWidth / 2 - 4;
      ctx.beginPath();
      ctx.moveTo(cx + innerR * Math.cos(angle), cy + innerR * Math.sin(angle));
      ctx.lineTo(cx + outerR * Math.cos(angle), cy + outerR * Math.sin(angle));
      ctx.strokeStyle = 'rgba(160, 160, 180, 0.22)';
      ctx.lineWidth = 1;
      ctx.stroke();
    }
  }

  /**
   * Render reason list items.
   */
  function renderReasons(reasons, type) {
    if (!reasons || reasons.length === 0) {
      return `<div class="an-reason-empty">Bu yönde belirgin bir sinyal tespit edilmedi.</div>`;
    }
    return reasons.map(r => `
      <div class="an-reason-item">
        <span class="an-reason-dot ${type}"></span>
        <span>${r}</span>
      </div>
    `).join('');
  }

  /**
   * Render smart price targets card.
   */
  function renderPriceTargets(pt, currentPrice) {
    if (!pt || !pt.basarili) {
      return `
        <div class="price-target-card glass-card-static">
          <div class="price-target-header"><span class="price-target-title">🎯 Fiyat Hedefleri</span></div>
          <div class="an-empty-inline">Bu hisse için fiyat hedefi hesaplanamadı.</div>
        </div>`;
    }

    const { giris_fiyati, hedef_1, hedef_1_kar_yuzde, hedef_2, hedef_2_kar_yuzde, stop_loss, zarar_yuzde, risk_odul_orani } = pt;
    const maxVal = Math.max(hedef_2, currentPrice) * 1.05;
    const getWidth = (val) => Math.min(100, Math.max(6, (val / maxVal) * 100)).toFixed(1);

    return `
      <div class="price-target-card glass-card-static">
        <div class="price-target-header">
          <span class="price-target-title">🎯 Akıllı Fiyat Hedefleri</span>
          <div class="risk-reward-badge"><span>Risk/Ödül:</span> <span>${(risk_odul_orani || 0).toFixed(2)}x</span></div>
        </div>
        <div class="price-levels">
          <div class="price-level">
            <span class="price-level-label stoploss">Stop Loss</span>
            <div class="price-level-bar"><div class="price-level-fill stoploss" style="width:${getWidth(stop_loss)}%"></div></div>
            <span class="price-level-value" style="color:var(--red)">₺${formatNumber(stop_loss)}</span>
            <span class="price-level-pct negative">${(zarar_yuzde || 0).toFixed(2)}%</span>
          </div>
          <div class="price-level">
            <span class="price-level-label giris">Giriş</span>
            <div class="price-level-bar"><div class="price-level-fill giris" style="width:${getWidth(giris_fiyati)}%"></div></div>
            <span class="price-level-value" style="color:var(--cyan)">₺${formatNumber(giris_fiyati)}</span>
            <span class="price-level-pct" style="color:var(--cyan)">Optimum</span>
          </div>
          <div class="price-level">
            <span class="price-level-label hedef">Hedef 1</span>
            <div class="price-level-bar"><div class="price-level-fill hedef" style="width:${getWidth(hedef_1)}%"></div></div>
            <span class="price-level-value" style="color:var(--green)">₺${formatNumber(hedef_1)}</span>
            <span class="price-level-pct positive">+${(hedef_1_kar_yuzde || 0).toFixed(2)}%</span>
          </div>
          <div class="price-level">
            <span class="price-level-label hedef2">Hedef 2</span>
            <div class="price-level-bar"><div class="price-level-fill hedef" style="width:${getWidth(hedef_2)}%; background:var(--gradient-accent)"></div></div>
            <span class="price-level-value" style="color:var(--green-light)">₺${formatNumber(hedef_2)}</span>
            <span class="price-level-pct positive">+${(hedef_2_kar_yuzde || 0).toFixed(2)}%</span>
          </div>
        </div>
        <div class="an-pt-footer">
          <span>Mevcut Fiyat: <strong>₺${formatNumber(currentPrice)}</strong></span>
          <span>Volatilite (ATR 14): <strong>₺${formatNumber(pt.atr || 0)}</strong></span>
        </div>
      </div>`;
  }

  /**
   * Render Fibonacci retracement levels table.
   */
  function renderFibonacciTable(fib) {
    if (!fib || fib.seviye_0 == null) {
      return `<div class="an-empty-inline">Fibonacci seviyeleri hesaplanamadı.</div>`;
    }

    const levels = [
      { ratio: "0.000 (Zirve)", value: fib.seviye_0, label: "Direnç" },
      { ratio: "0.236", value: fib.seviye_0236, label: "Hafif düzeltme" },
      { ratio: "0.382", value: fib.seviye_0382, label: "Düzeltme desteği" },
      { ratio: "0.500", value: fib.seviye_0500, label: "Denge seviyesi" },
      { ratio: "0.618 (Altın Oran)", value: fib.seviye_0618, label: "Güçlü destek" },
      { ratio: "0.786", value: fib.seviye_0786, label: "Derin düzeltme" },
      { ratio: "1.000 (Dip)", value: fib.seviye_1, label: "Ana trend desteği" }
    ];

    return `
      <div class="an-fib-meta">
        <span>Trend: <strong class="${fib.trend_yonu === 'Yükseliş' ? 'text-up' : 'text-down'}">${fib.trend_yonu || '—'}</strong></span>
        <span>Konum: <strong style="color:var(--cyan)">${fib.bolge || '—'}</strong></span>
      </div>
      <div class="an-table-wrap">
        <table class="an-table">
          <thead><tr><th>Seviye</th><th>Fiyat</th><th>Yorum</th></tr></thead>
          <tbody>
            ${levels.map(l => `
              <tr>
                <td class="an-table-num">${l.ratio}</td>
                <td class="an-table-num" style="color:var(--cyan); font-weight:700;">₺${formatNumber(l.value)}</td>
                <td class="an-table-desc">${l.label}</td>
              </tr>`).join('')}
          </tbody>
        </table>
      </div>`;
  }

  /**
   * Render technical indicator cards.
   */
  function renderTechnicalCards(t) {
    const indicators = [
      { name: 'RSI (14)', value: fmtVal(t.rsi), signal: getRSISignal(t.rsi), desc: 'Göreceli Güç Endeksi', icon: '📈' },
      { name: 'MACD', value: fmtVal(t.macd), signal: t.macdSignal || 'Nötr', desc: 'Hareketli Ort. Yakınsama', icon: '📉' },
      { name: 'Bollinger', value: shortText(t.bollingerSignal), signal: bbBadge(t.bollingerSignal), desc: 'Volatilite bantları', icon: '📊' },
      { name: 'SMA 50/200', value: shortText(t.smaSignal), signal: smaBadge(t.smaSignal), desc: 'Trend yönü', icon: '〰️' },
      { name: 'ADX', value: fmtVal(t.adx), signal: t.adxSignal || '—', desc: 'Trend gücü', icon: '💪' },
      { name: 'Stochastic', value: fmtVal(t.stochastic), signal: shortText(t.stochasticSignal) || 'Nötr', desc: 'Stokastik osilatör', icon: '🔄' },
      { name: 'Hacim', value: t.volume || '—', signal: shortText(t.volumeSignal) || 'Normal', desc: 'İşlem hacmi', icon: '📶' },
      { name: 'ATR (14)', value: fmtVal(t.atr), signal: t.atrSignal || 'Volatilite', desc: 'Ortalama gerçek aralık', icon: '📏' },
    ];

    return indicators.map(ind => `
      <div class="an-ind-card glass-card-static">
        <div class="an-ind-top">
          <span class="an-ind-name">${ind.icon} ${ind.name}</span>
          <span class="badge ${getSignalBadgeClass(ind.signal)}">${ind.signal}</span>
        </div>
        <div class="an-ind-value">${ind.value}</div>
        <div class="an-ind-desc">${ind.desc}</div>
      </div>`).join('');
  }

  /**
   * Render support and resistance levels as a price ladder.
   */
  function renderSupportResistance(sr, currentPrice) {
    const levels = sr.levels || [];
    if (!levels.length) {
      return `<div class="an-empty-inline">Destek / direnç seviyeleri hesaplanamadı.</div>`;
    }

    return `
      <div class="an-sr-ladder">
        ${levels.map(l => {
          const isRes = l.type === 'resistance';
          const isPivot = l.type === 'pivot';
          const cls = isPivot ? 'pivot' : (isRes ? 'res' : 'sup');
          return `
            <div class="an-sr-row ${cls}">
              <span class="an-sr-dot"></span>
              <span class="an-sr-label">${l.label}</span>
              <span class="an-sr-value">₺${l.value ? formatNumber(l.value) : '—'}</span>
            </div>`;
        }).join('')}
      </div>
      ${currentPrice ? `<div class="an-sr-current">Mevcut Fiyat: <strong>₺${formatNumber(currentPrice)}</strong></div>` : ''}`;
  }

  /**
   * Load depth data with priority + AI analysis + auto-refresh.
   */
  let _depthRefreshTimer = null;

  function loadDepthData(symbol) {
    // Onceki timer'i temizle
    if (_depthRefreshTimer) clearInterval(_depthRefreshTimer);
    
    const container = document.getElementById('depthContent');
    if (!container) return;

    // Backend'e oncelik bildir
    fetch(`/api/depth/priority/${symbol}`, { method: 'POST' }).catch(() => {});

    function refresh() {
      Promise.all([
        fetch(`/api/depth/${symbol}`).then(r => r.json()),
        fetch(`/api/depth/analyze/${symbol}`).then(r => r.json()),
        fetch(`/api/depth/photo/${symbol}`).then(r => r.json()).catch(() => ({success:false}))
      ])
      .then(([depthRes, aiRes, photoRes]) => {
        // Fotoğraf HTML'i
        let photoHtml = '';
        if (photoRes.success && photoRes.photo) {
          photoHtml = `
            <div class="depth-photo-wrap glass-card-static" style="margin-bottom:12px;overflow:hidden">
              <div class="depth-photo-header" style="display:flex;align-items:center;justify-content:space-between;padding:8px 12px;border-bottom:1px solid var(--glass-border)">
                <span>📸 Telegram'dan Gelen Ham Derinlik Görüntüsü</span>
                <button onclick="this.closest('.depth-photo-wrap').querySelector('img').style.display=this.closest('.depth-photo-wrap').querySelector('img').style.display==='none'?'block':'none';this.textContent=this.textContent==='Gizle'?'Göster':'Gizle'" style="font-size:0.7rem;background:var(--glass-bg);border:1px solid var(--glass-border);color:var(--text);padding:2px 8px;border-radius:4px;cursor:pointer">Gizle</button>
              </div>
              <img src="data:image/png;base64,${photoRes.photo}" style="width:100%;max-width:400px;display:block;margin:0 auto" alt="Derinlik Fotoğrafı" />
            </div>`;
        }

        if (depthRes.success && depthRes.depth && (depthRes.depth.alis.length || depthRes.depth.satis.length)) {
          const aiHtml = aiRes.success && aiRes.analysis
            ? renderAIAnalysis(aiRes.analysis, depthRes.depth.symbol)
            : '';
          container.innerHTML = photoHtml + renderDepthTable(depthRes.depth, depthRes.depth.price) + aiHtml;
        } else {
          // Veri yoksa tetikle
          if (!depthRes.success) {
            fetch(`/api/depth/fetch/${symbol}`, { method: 'POST' }).catch(() => {});
          }
          container.innerHTML = photoHtml + '<div class="an-empty-inline">📡 Derinlik verisi cekiliyor... (3 sn\'de bir yenileniyor)</div>';
        }
      })
      .catch(() => {
        container.innerHTML = '<div class="an-empty-inline">⚠️ Derinlik verisi yuklenemedi.</div>';
      });
    }

    // Ilk fetch hemen
    refresh();
    // 3 saniyede bir yenile (backend de ayni hizda cekiyor)
    _depthRefreshTimer = setInterval(refresh, 3000);
  }

  /**
   * Render AI depth analysis commentary.
   */
  function renderAIAnalysis(analysis, symbol) {
    if (!analysis || !analysis.comment) return '';
    
    const vClass = analysis.verdict === 'al' ? 'depth-ai-buy'
      : analysis.verdict === 'sat' ? 'depth-ai-sell' : 'depth-ai-neutral';
    const vLabel = analysis.verdict === 'al' ? '🟢 ALICI'
      : analysis.verdict === 'sat' ? '🔴 SATICI' : '⚖️ DENGELİ';
    
    const fmt = (n) => n >= 1000000 ? (n/1000000).toFixed(1)+'M' : n >= 1000 ? (n/1000).toFixed(0)+'K' : String(n);
    const d = analysis.details || {};
    
    // Depth-based support/resistance + trading signal
    let levelsHtml = '';
    const sup = d.strongest_support;
    const res = d.strongest_resistance;
    const sig = analysis.signal;

    if (sup || res || sig) {
      levelsHtml = '<div class="depth-levels-row">';
      if (sup) {
        levelsHtml += `
          <div class="depth-level-card support">
            <div class="depth-level-label">📉 Kademe Desteği</div>
            <div class="depth-level-price">₺${sup.price.toFixed(2)}</div>
            <div class="depth-level-info">%${sup.distance_pct.toFixed(1)} aşağıda • ${fmt(sup.lot)} lot</div>
          </div>`;
      }
      if (res) {
        levelsHtml += `
          <div class="depth-level-card resistance">
            <div class="depth-level-label">📈 Kademe Direnci</div>
            <div class="depth-level-price">₺${res.price.toFixed(2)}</div>
            <div class="depth-level-info">%${res.distance_pct.toFixed(1)} yukarıda • ${fmt(res.lot)} lot</div>
          </div>`;
      }
      levelsHtml += '</div>';
    }

    // Trading signal card
    let signalHtml = '';
    if (sig && sig.entry) {
      const rrColor = sig.rr_ratio >= 2 ? 'var(--green)' : sig.rr_ratio >= 1 ? 'var(--accent)' : 'var(--red)';
      signalHtml = `
        <div class="depth-signal-row">
          <div class="depth-signal-card">
            <div class="depth-signal-label">🟢 GİRİŞ</div>
            <div class="depth-signal-price">₺${sig.entry.toFixed(2)}</div>
          </div>
          <div class="depth-signal-card stop">
            <div class="depth-signal-label">🛑 STOP</div>
            <div class="depth-signal-price">₺${sig.stop.toFixed(2)}</div>
            <div class="depth-signal-info">Risk: ₺${sig.risk_tl.toFixed(2)}</div>
          </div>
          <div class="depth-signal-card target">
            <div class="depth-signal-label">🎯 HEDEF</div>
            <div class="depth-signal-price">₺${sig.target.toFixed(2)}</div>
            <div class="depth-signal-info">Ödül: ₺${sig.reward_tl.toFixed(2)}</div>
          </div>
          <div class="depth-signal-card rr">
            <div class="depth-signal-label">📊 R/R</div>
            <div class="depth-signal-price" style="color:${rrColor}">${sig.rr_ratio.toFixed(2)}</div>
            <div class="depth-signal-info">${sig.suggested_lot || 100} lot öneri</div>
          </div>
        </div>`;
    }
    
    return `
      <div class="depth-ai-wrap glass-card-static ${vClass}">
        <div class="depth-ai-header">
          <span class="depth-ai-verdict">${vLabel}</span>
          <span class="depth-ai-score">Kademe Skoru: ${analysis.score}/100</span>
        </div>
        <div class="depth-ai-comment">🧠 ${analysis.comment}</div>
        ${levelsHtml}
        ${signalHtml}
        <div class="depth-ai-stats">
          <div class="depth-ai-stat">
            <span class="depth-ai-stat-val">${fmt(d.total_alis_lot || 0)}</span>
            <span class="depth-ai-stat-lbl">Toplam Alış Lot</span>
          </div>
          <div class="depth-ai-stat">
            <span class="depth-ai-stat-val">${fmt(d.total_satis_lot || 0)}</span>
            <span class="depth-ai-stat-lbl">Toplam Satış Lot</span>
          </div>
          <div class="depth-ai-stat">
            <span class="depth-ai-stat-val">₺${(d.spread || 0).toFixed(2)}</span>
            <span class="depth-ai-stat-lbl">Spread</span>
          </div>
          <div class="depth-ai-stat">
            <span class="depth-ai-stat-val">%${((d.alis_ratio || 0.5)*100).toFixed(0)}</span>
            <span class="depth-ai-stat-lbl">Alış Oranı</span>
          </div>
        </div>
      </div>`;
  }

  /**
   * Render depth/order book table.
   */
  function renderDepthTable(depth, price) {
    const maxRows = Math.max(depth.alis.length, depth.satis.length, 1);
    const priceStr = price ? `₺${price.toFixed(2)}` : '—';
    
    // Eger veri yoksa uyari goster
    if (depth.alis.length === 0 && depth.satis.length === 0) {
      return `
        <div class="depth-table-wrap glass-card-static">
          <div class="depth-header-row">
            <span class="depth-symbol-badge">📊 ${depth.symbol || ''}</span>
            <span class="depth-price-badge">${priceStr}</span>
          </div>
          <div class="an-empty-inline" style="margin:20px;text-align:center">
            ⚠️ Bu hisse icin derinlik verisi henuz parse edilemedi.<br>
            <small>OCR metni yetersiz — farkli bir hisse deneyin (THYAO, ASELS)</small>
          </div>
        </div>`;
    }
    
    const fmtLot = (n) => {
      if (n == null || n === 0) return '—';
      if (n >= 1000000) return (n / 1000000).toFixed(2) + 'M';
      if (n >= 1000) return (n / 1000).toFixed(1) + 'K';
      return n.toLocaleString('tr-TR');
    };

    let rows = '';
    for (let i = 0; i < maxRows; i++) {
      const alisRow = depth.alis[i];
      const satisRow = depth.satis[i];
      const alisPrice = alisRow ? (Array.isArray(alisRow) ? alisRow[0] : alisRow).toFixed(2) : '';
      const alisQty = alisRow ? (Array.isArray(alisRow) ? alisRow[1] : 0) : 0;
      const satisPrice = satisRow ? (Array.isArray(satisRow) ? satisRow[0] : satisRow).toFixed(2) : '';
      const satisQty = satisRow ? (Array.isArray(satisRow) ? satisRow[1] : 0) : 0;

      rows += `
        <tr>
          <td class="depth-row-num">${i + 1}</td>
          <td class="depth-qty-col">${alisPrice ? fmtLot(alisQty) : '—'}</td>
          <td class="depth-alis-col">${alisPrice || '—'}</td>
          <td class="depth-mid-col">${i === 0 ? priceStr : ''}</td>
          <td class="depth-satis-col">${satisPrice || '—'}</td>
          <td class="depth-qty-col">${satisPrice ? fmtLot(satisQty) : '—'}</td>
        </tr>`;
    }

    return `
      <div class="depth-table-wrap glass-card-static">
        <div class="depth-header-row">
          <span class="depth-symbol-badge">📊 ${depth.symbol || ''}</span>
          <span class="depth-price-badge">${priceStr}</span>
        </div>
        <table class="depth-table">
          <thead>
            <tr>
              <th>#</th>
              <th>Lot</th>
              <th class="depth-alis-head">🟢 ALIŞ</th>
              <th class="depth-mid-head">Fiyat</th>
              <th class="depth-satis-head">🔴 SATIŞ</th>
              <th>Lot</th>
            </tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
        <div class="depth-footer">
          <span>📡 @ucretsizderinlikbot • 25 Kademe</span>
          <span>${depth.alis.length} Alış / ${depth.satis.length} Satış</span>
        </div>
      </div>`;
  }

  /**
   * Render news and sentiment section.
   */
  function renderNewsSentiment(sentiment) {
    const overall = sentiment.overall != null ? sentiment.overall : 0.5;
    const posPercent = Math.round(overall * 100);
    const negPercent = 100 - posPercent;
    const articles = sentiment.articles || [];
    const simulasyon = sentiment.simulasyon || false;

    const news = articles.filter(a => !a.isComment);
    const comments = articles.filter(a => a.isComment);

    // Simülasyon uyarısı
    const simulasyonUyarisi = simulasyon ? `
      <div class="simulasyon-uyarisi">
        ⚠️ Yeterli güncel haber bulunamadığı için bazı yorumlar simüle edilmiştir. Yatırım kararlarınızı yalnızca bu verilere dayandırmayın.
      </div>` : '';

    const renderCard = (a) => {
      const sClass = a.score >= 0.55 ? 'positive' : a.score <= 0.45 ? 'negative' : 'neutral';
      const sLabel = a.score >= 0.55 ? 'Olumlu' : a.score <= 0.45 ? 'Olumsuz' : 'Nötr';
      return `
        <a class="an-news-card" ${a.link ? `href="${a.link}" target="_blank" rel="noopener"` : ''}>
          <div class="an-news-body">
            <div class="an-news-title" title="${a.title}">${a.title}</div>
            <div class="an-news-source">${a.source || 'Borsa Forumu'}</div>
          </div>
          <span class="an-sent-tag ${sClass}">${sLabel}</span>
        </a>`;
    };

    const colHtml = (items, emptyMsg) => items.length
      ? items.map(renderCard).join('')
      : `<div class="an-empty-inline">${emptyMsg}</div>`;

    const overallClass = posPercent >= 55 ? 'positive' : posPercent <= 45 ? 'negative' : 'neutral';
    const overallLabel = posPercent >= 55 ? '😊 Olumlu' : posPercent <= 45 ? '😟 Olumsuz' : '😐 Nötr';

    return `
      ${simulasyonUyarisi}
      <div class="glass-card-static an-sent-summary">
        <div class="an-sent-head">
          <span>Yapay Zeka Destekli Genel Duyarlılık</span>
          <span class="an-sent-tag ${overallClass}">${overallLabel} %${posPercent}</span>
        </div>
        <div class="sentiment-bar-wrapper">
          <div class="sentiment-bar-neg" style="width:${negPercent}%"></div>
          <div class="sentiment-bar-pos" style="width:${posPercent}%"></div>
        </div>
      </div>
      <div class="an-news-grid">
        <div>
          <h3 class="an-subhead">📰 Sektörel &amp; Kurumsal Haberler</h3>
          <div class="an-news-list">${colHtml(news, 'Son dönemde kurumsal haber bulunmuyor.')}</div>
        </div>
        <div>
          <h3 class="an-subhead">💬 Sosyal Medya &amp; Forum Yorumları</h3>
          <div class="an-news-list">${colHtml(comments, 'Son dönemde forum yorumu bulunmuyor.')}</div>
        </div>
      </div>`;
  }

  /**
   * Render empty analysis state (no stock selected).
   */
  function renderEmptyAnalysis() {
    return `
      <div class="an-empty">
        <div class="an-empty-icon">🔍</div>
        <div class="an-empty-title">Hisse Seçilmedi</div>
        <div class="an-empty-desc">Yukarıdaki arama çubuğundan bir BIST hissesi arayın (örn: THYAO) ve detaylı analizi görün.</div>
      </div>`;
  }

  /**
   * Render loading skeleton for analysis page.
   */
  function renderAnalysisSkeleton() {
    return `
      <div class="anim-fade-in">
        <div class="an-skel-hero">
          <div class="skeleton" style="width:60px;height:60px;border-radius:14px;"></div>
          <div style="flex:1;">
            <div class="skeleton skeleton-title" style="width:140px;"></div>
            <div class="skeleton skeleton-text" style="width:200px;"></div>
          </div>
          <div style="text-align:right;">
            <div class="skeleton skeleton-title" style="width:120px;margin-left:auto;"></div>
            <div class="skeleton skeleton-text" style="width:90px;margin-left:auto;"></div>
          </div>
        </div>
        <div class="skeleton" style="height:56px;border-radius:10px;margin-bottom:24px;"></div>
        <div class="skeleton skeleton-chart" style="height:340px;margin-bottom:24px;"></div>
        <div class="an-verdict-grid" style="margin-bottom:24px;">
          <div class="skeleton skeleton-card" style="height:320px;"></div>
          <div class="skeleton skeleton-card" style="height:320px;"></div>
        </div>
        <div class="an-indicators">
          ${Array(8).fill('<div class="skeleton skeleton-card" style="height:110px;"></div>').join('')}
        </div>
      </div>`;
  }

  // --- Helpers ---

  function getActionBadgeClass(action) {
    const a = (action || '').toUpperCase();
    if (a === 'AL') return 'badge-al';
    if (a === 'SAT') return 'badge-sat';
    return 'badge-tut';
  }

  function getRiskClass(risk) {
    const r = (risk || '').toLowerCase();
    if (r.includes('düşük')) return 'text-up';
    if (r.includes('yüksek')) return 'text-down';
    return '';
  }

  function getScoreColor(score) {
    if (score >= 65) return '#c5a880'; // Gold — AL
    if (score >= 40) return '#aab3c4'; // Silver — TUT
    return '#718096';                  // Slate — SAT
  }

  function getRSISignal(rsi) {
    const v = Number(rsi);
    if (isNaN(v)) return 'Nötr';
    if (v >= 70) return 'SAT';
    if (v <= 30) return 'AL';
    return 'Nötr';
  }

  function getSignalBadgeClass(signal) {
    const s = (signal || '').toUpperCase();
    if (s.includes('AL') || s.includes('GÜÇLÜ') || s.includes('YÜKSEL')) return 'badge-al';
    if (s.includes('SAT') || s.includes('DÜŞÜŞ') || s.includes('ZAYIF')) return 'badge-sat';
    return 'badge-notr';
  }

  function bbBadge(signal) {
    const s = (signal || '').toLowerCase();
    if (s.includes('satım') || s.includes('alt')) return 'AL';
    if (s.includes('alım') || s.includes('üst')) return 'SAT';
    return 'Nötr';
  }

  function smaBadge(signal) {
    const s = (signal || '').toLowerCase();
    if (s.includes('golden') || s.includes('altın') || s.includes('yükseliş')) return 'AL';
    if (s.includes('death') || s.includes('ölüm') || s.includes('düşüş')) return 'SAT';
    return 'Nötr';
  }

  function shortText(txt) {
    if (!txt) return '';
    // Take the leading label before a dash/parenthesis for compact display
    return String(txt).split(/[-(]/)[0].trim();
  }

  function fmtVal(v) {
    if (v === null || v === undefined || v === '') return '—';
    const n = Number(v);
    if (isNaN(n)) return v;
    return n.toLocaleString('tr-TR', { maximumFractionDigits: 2 });
  }

  function formatNumber(num) {
    if (num === null || num === undefined) return '—';
    return Number(num).toLocaleString('tr-TR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  return {
    renderAnalysisPage,
    renderAnalysisSkeleton,
    changePeriod,
    drawGauge,
    toggleMethodology,
  };
})();
