/* ============================================
   StockPilot — Hisse Karşılaştırma
   ============================================ */

window.StockPilotCompare = (function () {
  'use strict';

  const BIST_STOCKS = [
    'THYAO','ASELS','GARAN','EREGL','SISE','KCHOL','TUPRS','SAHOL',
    'AKBNK','YKBNK','BIMAS','TCELL','PGSUS','TAVHL','SASA','HEKTS',
    'KOZAL','PETKM','TTKOM','FROTO','TOASO','VESTL','ENKAI','ISCTR',
    'HALKB','VAKBN','ARCLK','DOHOL','EKGYO','MGROS','SOKM','CCOLA',
    'KONTR','SMRTG','GESAN','ODAS','DOAS','LOGO','MPARK','EUPWR','EMPAE'
  ];

  function renderComparePage(container) {
    container.innerHTML = `
      <div class="anim-fade-in">
        <div class="rec-hero">
          <div class="rec-hero-content">
            <h2 class="rec-hero-title"><span>🔄</span> Hisse Karşılaştırma</h2>
            <p class="rec-hero-sub">2-3 hisseyi yan yana kıyaslayın</p>
          </div>
        </div>

        <div class="compare-selectors">
          <div class="compare-selector">
            <label>Hisse 1</label>
            <select id="cmpSymbol1" class="pnl-select" onchange="window.StockPilotCompare.runCompare()">
              <option value="">Seçiniz</option>
              ${BIST_STOCKS.map(s => `<option value="${s}">${s}</option>`).join('')}
            </select>
          </div>
          <span class="compare-vs">VS</span>
          <div class="compare-selector">
            <label>Hisse 2</label>
            <select id="cmpSymbol2" class="pnl-select" onchange="window.StockPilotCompare.runCompare()">
              <option value="">Seçiniz</option>
              ${BIST_STOCKS.map(s => `<option value="${s}">${s}</option>`).join('')}
            </select>
          </div>
          <span class="compare-vs">VS</span>
          <div class="compare-selector">
            <label>Hisse 3 (opsiyonel)</label>
            <select id="cmpSymbol3" class="pnl-select" onchange="window.StockPilotCompare.runCompare()">
              <option value="">Seçiniz</option>
              ${BIST_STOCKS.map(s => `<option value="${s}">${s}</option>`).join('')}
            </select>
          </div>
        </div>

        <div id="compareResults">
          <div class="empty-state" style="padding:48px;">
            <div class="empty-icon">🔄</div>
            <div class="empty-title">Hisse Seçin</div>
            <div class="empty-desc">Karşılaştırmak için en az 2 hisse seçin</div>
          </div>
        </div>
      </div>
    `;
  }

  async function runCompare() {
    const s1 = document.getElementById('cmpSymbol1')?.value;
    const s2 = document.getElementById('cmpSymbol2')?.value;
    const s3 = document.getElementById('cmpSymbol3')?.value;
    
    const symbols = [s1, s2, s3].filter(Boolean);
    if (symbols.length < 2) {
      document.getElementById('compareResults').innerHTML = `
        <div class="empty-state" style="padding:48px;">
          <div class="empty-icon">🔄</div>
          <div class="empty-title">Hisse Seçin</div>
          <div class="empty-desc">Karşılaştırmak için en az 2 hisse seçin</div>
        </div>
      `;
      return;
    }

    document.getElementById('compareResults').innerHTML = `
      <div class="loading-container"><div class="loading-spinner"></div><p>Karşılaştırılıyor...</p></div>
    `;

    try {
      const res = await fetch(`/api/compare?symbols=${symbols.join(',')}`);
      const data = await res.json();
      if (!data.success) throw new Error(data.error);

      const stocks = data.karsilastirma || [];
      renderCompareCards(stocks);
    } catch (e) {
      document.getElementById('compareResults').innerHTML = `
        <div class="empty-state" style="padding:48px;">
          <div class="empty-icon">❌</div>
          <div class="empty-title">Hata</div>
          <div class="empty-desc">${e.message}</div>
        </div>
      `;
    }
  }

  function renderCompareCards(stocks) {
    const cols = stocks.length;
    const gridClass = cols === 2 ? 'grid-2' : 'grid-3';

    // En iyi skoru bul
    const bestScore = Math.max(...stocks.map(s => s.skor || 0));

    const renderCard = (s, idx) => {
      const isUp = (s.degisim_yuzde || 0) >= 0;
      const chgClass = isUp ? 'up' : 'down';
      const actionBadge = s.aksiyon === 'AL' ? 'badge-al' : s.aksiyon === 'SAT' ? 'badge-sat' : 'badge-tut';
      const isBest = (s.skor || 0) === bestScore && bestScore > 0;

      return `
        <div class="glass-card compare-card ${isBest ? 'compare-best' : ''}" onclick="window.StockPilot.analyzeStock('${s.symbol}')">
          ${isBest ? '<div class="compare-best-badge">🏆 En İyi</div>' : ''}
          <div class="compare-card-header">
            <span class="compare-symbol">${s.symbol}</span>
            <span class="compare-name">${s.isim || ''}</span>
            <span class="badge ${actionBadge}">${s.aksiyon || 'TUT'}</span>
          </div>
          <div class="compare-price-row">
            <span class="compare-price">₺${(s.fiyat || 0).toLocaleString('tr-TR', {minimumFractionDigits:2})}</span>
            <span class="compare-change ${chgClass}">${isUp ? '▲' : '▼'} %${Math.abs(s.degisim_yuzde || 0).toFixed(2)}</span>
          </div>
          
          <div class="compare-indicators">
            <div class="compare-ind">
              <span class="compare-ind-label">RSI</span>
              <span class="compare-ind-val">${(s.rsi || 50).toFixed(1)}</span>
              <span class="compare-ind-sig">${s.rsi_sinyal || '—'}</span>
            </div>
            <div class="compare-ind">
              <span class="compare-ind-label">MACD</span>
              <span class="compare-ind-val">—</span>
              <span class="compare-ind-sig">${s.macd_sinyal || '—'}</span>
            </div>
            <div class="compare-ind">
              <span class="compare-ind-label">Hacim</span>
              <span class="compare-ind-val">${s.hacim ? (s.hacim/1e6).toFixed(1) + 'M' : '—'}</span>
              <span class="compare-ind-sig">${s.hacim_sinyal || '—'}</span>
            </div>
          </div>

          <div class="compare-targets">
            <div class="compare-target">🎯 Hedef: <strong>₺${(s.hedef_1 || 0).toFixed(2)}</strong></div>
            <div class="compare-target">🛑 Stop: <strong>₺${(s.stop_loss || 0).toFixed(2)}</strong></div>
          </div>

          <div class="compare-score-bar">
            <div class="compare-score-fill" style="width:${s.skor || 0}%; background:${s.aksiyon === 'AL' ? 'var(--trend-up)' : s.aksiyon === 'SAT' ? 'var(--trend-down)' : 'var(--text-muted)'}"></div>
          </div>
          <div class="compare-confidence">Güven: <strong>%${s.guven || 0}</strong> | Skor: <strong>${s.skor || 0}/100</strong></div>
        </div>
      `;
    };

    document.getElementById('compareResults').innerHTML = `
      <div class="${gridClass} mt-24">
        ${stocks.map(renderCard).join('')}
      </div>
    `;
  }

  return { renderComparePage, runCompare };
})();
