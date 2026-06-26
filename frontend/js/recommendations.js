/* ============================================
   StockPilot — Recommendations Renderer
   ============================================ */

window.StockPilotRecommendations = (function () {
  'use strict';

  let currentFilter = 'all';

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

  /**
   * Render daily recommendations page.
   */
  function renderDailyRecommendations(container, data) {
    const items = data && data.recommendations ? data.recommendations : getMockDailyData();
    const dateStr = data && data.date ? data.date : formatTurkishDate(new Date());
    currentFilter = 'all';

    container.innerHTML = `
      <div class="anim-fade-in">
        <div class="rec-hero">
          <div class="rec-hero-content">
            <h2 class="rec-hero-title"><span>⏰</span> Günlük Öneriler</h2>
            <p class="rec-hero-sub">Yapay zeka destekli BIST analizi — ${dateStr}</p>
          </div>
          <div class="rec-hero-badge">
            <span class="rec-hero-badge-icon">🤖</span>
            <span>AI Analiz</span>
          </div>
        </div>

        <div class="rec-filters">
          <button class="rec-filter active" data-filter="all" onclick="window.StockPilotRecommendations.filterRecs(this, 'daily')">
            <span class="rec-filter-icon">📋</span> Tümü
          </button>
          <button class="rec-filter" data-filter="AL" onclick="window.StockPilotRecommendations.filterRecs(this, 'daily')">
            <span class="rec-filter-dot al"></span> AL
          </button>
          <button class="rec-filter" data-filter="SAT" onclick="window.StockPilotRecommendations.filterRecs(this, 'daily')">
            <span class="rec-filter-dot sat"></span> SAT
          </button>
          <button class="rec-filter" data-filter="TUT" onclick="window.StockPilotRecommendations.filterRecs(this, 'daily')">
            <span class="rec-filter-dot tut"></span> TUT
          </button>
        </div>
        <div class="rec-list" id="recListDaily">
          ${renderRecCards(items)}
        </div>
      </div>
    `;
    container._recData = items;
  }

  /**
   * Render weekly recommendations page.
   */
  function renderWeeklyRecommendations(container, data) {
    const items = data && data.recommendations ? data.recommendations : getMockWeeklyData();
    const dateStr = data && data.date ? data.date : formatTurkishDate(new Date());
    currentFilter = 'all';

    container.innerHTML = `
      <div class="anim-fade-in">
        <div class="rec-hero">
          <div class="rec-hero-content">
            <h2 class="rec-hero-title"><span>📆</span> Haftalık Öneriler</h2>
            <p class="rec-hero-sub">3 aylık periyot analizi — ${dateStr}</p>
          </div>
          <div class="rec-hero-badge">
            <span class="rec-hero-badge-icon">📊</span>
            <span>Haftalık</span>
          </div>
        </div>

        <div class="rec-filters">
          <button class="rec-filter active" data-filter="all" onclick="window.StockPilotRecommendations.filterRecs(this, 'weekly')">
            <span class="rec-filter-icon">📋</span> Tümü
          </button>
          <button class="rec-filter" data-filter="AL" onclick="window.StockPilotRecommendations.filterRecs(this, 'weekly')">
            <span class="rec-filter-dot al"></span> AL
          </button>
          <button class="rec-filter" data-filter="SAT" onclick="window.StockPilotRecommendations.filterRecs(this, 'weekly')">
            <span class="rec-filter-dot sat"></span> SAT
          </button>
          <button class="rec-filter" data-filter="TUT" onclick="window.StockPilotRecommendations.filterRecs(this, 'weekly')">
            <span class="rec-filter-dot tut"></span> TUT
          </button>
        </div>
        <div class="rec-list" id="recListWeekly">
          ${renderRecCards(items)}
        </div>
      </div>
    `;
    container._recData = items;
  }

  /**
   * Filter recommendation cards.
   */
  function filterRecs(btn, type) {
    btn.parentElement.querySelectorAll('.rec-filter').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');

    const filter = btn.dataset.filter;
    currentFilter = filter;
    const listId = type === 'daily' ? 'recListDaily' : 'recListWeekly';
    const listEl = document.getElementById(listId);
    const container = document.getElementById('page-content');
    const allItems = container._recData || [];

    const filtered = filter === 'all' ? allItems : allItems.filter(r => r.action.toUpperCase() === filter);

    if (listEl) {
      listEl.innerHTML = filtered.length > 0
        ? renderRecCards(filtered)
        : `<div class="empty-state" style="padding:48px;">
            <div class="empty-icon">🔍</div>
            <div class="empty-title">Sonuç bulunamadı</div>
            <div class="empty-desc">Bu filtreye uygun öneri bulunmuyor.</div>
          </div>`;
    }
  }

  /**
   * Render recommendation cards HTML.
   */
  function renderRecCards(items) {
    const sorted = [...items].sort((a, b) => (b.confidence || 0) - (a.confidence || 0));

    return sorted.map((rec, idx) => {
      const changeClass = rec.changePercent >= 0 ? 'up' : 'down';
      const changeIcon = rec.changePercent >= 0 ? '▲' : '▼';
      const actionBadgeClass = getActionBadgeClass(rec.action);
      const badgeStyle = getBadgeStyle(rec.symbol);
      const fh = rec.fiyat_hedefleri || {};
      const giris = fh.giris_fiyati || (rec.price * 0.98);
      const hedef = fh.hedef_1 || (rec.price * (rec.action === 'SAT' ? 0.96 : 1.06));
      const stop = fh.stop_loss || (rec.price * (rec.action === 'SAT' ? 1.04 : 0.95));

      return `
        <div class="rec-card-premium glass-card anim-slide-up stagger-${Math.min(idx + 1, 8)}"
             onclick="window.StockPilot.analyzeStock('${rec.symbol}')">
          
          <div class="rec-rank">
            <span class="rec-rank-num">${idx + 1}</span>
          </div>

          <div class="rec-logo-area">
            ${rec.logoUrl
              ? `<img src="${rec.logoUrl}" alt="${rec.symbol}" class="rec-logo-img" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">
                 <div class="rec-logo-fallback" style="display:none; ${badgeStyle}">${rec.symbol.substring(0, 2)}</div>`
              : `<div class="rec-logo-fallback" style="${badgeStyle}">${rec.symbol.substring(0, 2)}</div>`
            }
          </div>

          <div class="rec-info">
            <div class="rec-info-top">
              <span class="rec-symbol-name">${rec.symbol}</span>
              <span class="rec-company-name">${rec.name || ''}</span>
              <span class="badge ${actionBadgeClass} rec-action-badge">${rec.action}</span>
            </div>
            
            <div class="rec-confidence-row">
              <div class="rec-confidence-bar-wrap">
                <div class="rec-confidence-bar">
                  <div class="rec-confidence-fill ${rec.action === 'AL' ? 'gold' : rec.action === 'SAT' ? 'slate' : 'neutral'}" style="width:${rec.confidence || 0}%"></div>
                </div>
              </div>
              <span class="rec-confidence-pct" style="color:${getScoreColor(rec.confidence || 0)}">%${rec.confidence || 0}</span>
            </div>

            ${rec.reason ? `<div class="rec-reason-text">💡 ${rec.reason}</div>` : ''}

            <div class="rec-targets">
              <div class="rec-target">
                <span class="rec-target-label">🎯 Giriş</span>
                <span class="rec-target-val">₺${formatNumber(giris)}</span>
              </div>
              <div class="rec-target">
                <span class="rec-target-label">🏁 Hedef</span>
                <span class="rec-target-val target">₺${formatNumber(hedef)}</span>
              </div>
              <div class="rec-target">
                <span class="rec-target-label">🛑 Stop</span>
                <span class="rec-target-val stop">₺${formatNumber(stop)}</span>
              </div>
            </div>
          </div>

          <div class="rec-price-block">
            <div class="rec-price-main">₺${formatNumber(rec.price)}</div>
            <div class="rec-price-change ${changeClass}">
              ${changeIcon} ${rec.changePercent >= 0 ? '+' : ''}${(rec.changePercent || 0).toFixed(2)}%
            </div>
          </div>
        </div>
      `;
    }).join('');
  }

  /**
   * Render recommendations skeleton.
   */
  function renderRecSkeleton() {
    let cards = '';
    for (let i = 0; i < 5; i++) {
      cards += `<div class="skeleton" style="height:100px;border-radius:16px;margin-bottom:12px;"></div>`;
    }
    return `
      <div class="anim-fade-in">
        <div class="skeleton skeleton-title" style="width:200px;margin-bottom:24px;"></div>
        ${cards}
      </div>
    `;
  }

  /**
   * Render watchlist page.
   */
  function renderWatchlist(container, data) {
    const items = data || [];

    if (items.length === 0) {
      container.innerHTML = `
        <div class="anim-fade-in">
          <div class="section-header">
            <h2 class="section-title"><span class="icon">⭐</span> Takip Listesi</h2>
          </div>
          <div class="glass-card-static">
            <div class="empty-state">
              <div class="empty-icon">📌</div>
              <div class="empty-title">Henüz takip listenizde hisse yok</div>
              <div class="empty-desc">Hisse analiz sayfasından beğendiğiniz hisseleri takip listesine ekleyebilirsiniz.</div>
            </div>
          </div>
        </div>
      `;
      return;
    }

    container.innerHTML = `
      <div class="anim-fade-in">
        <div class="section-header">
          <h2 class="section-title"><span class="icon">⭐</span> Takip Listesi</h2>
          <span class="text-secondary" style="font-size:0.85rem;">${items.length} hisse</span>
        </div>
        <div class="glass-card-static" style="padding:0;overflow:hidden;">
          ${items.map((item, idx) => {
            const changeClass = (item.changePercent || 0) >= 0 ? 'up' : 'down';
            const changeIcon = (item.changePercent || 0) >= 0 ? '▲' : '▼';
            const actionBadgeClass = getActionBadgeClass(item.action || 'TUT');
            return `
              <div class="watchlist-item anim-slide-up stagger-${Math.min(idx + 1, 8)}" style="border-bottom: 1px solid rgba(255,255,255,0.04);">
                <div class="watchlist-item-left" onclick="window.StockPilot.analyzeStock('${item.symbol}')">
                  ${item.logoUrl
                    ? `<div style="width: 36px; height: 36px; border-radius: 8px; background:#12121e; border: 1px solid rgba(255,255,255,0.06); display:flex; align-items:center; justify-content:center; overflow:hidden; flex-shrink:0; margin-right:12px;">
                         <img src="${item.logoUrl}" alt="${item.symbol}" style="width:70%; height:70%; object-fit:contain;" onerror="this.parentElement.innerHTML='${item.symbol.substring(0, 2)}'; this.parentElement.style.cssText='width: 36px; height: 36px; border-radius: 8px; margin-right: 12px; flex-shrink: 0; ${getBadgeStyle(item.symbol)}';">
                       </div>`
                    : `<div style="width: 36px; height: 36px; border-radius: 8px; margin-right: 12px; flex-shrink: 0; ${getBadgeStyle(item.symbol)}">${item.symbol.substring(0, 2)}</div>`}
                  <div>
                    <div class="wl-symbol">${item.symbol}</div>
                    <div class="wl-name">${item.name || ''}</div>
                  </div>
                </div>
                <div class="flex items-center gap-16">
                  <div style="text-align:right;">
                    <div class="wl-price">₺${formatNumber(item.price)}</div>
                    <div class="wl-change ${changeClass}" style="font-size:0.78rem;">
                      ${changeIcon} ${(item.changePercent || 0) >= 0 ? '+' : ''}${(item.changePercent || 0).toFixed(2)}%
                    </div>
                  </div>
                  <span class="badge ${actionBadgeClass}">${item.action || 'TUT'}</span>
                  <button class="remove-btn" onclick="event.stopPropagation(); window.StockPilot.removeFromWatchlist('${item.symbol}')" title="Kaldır">
                    ✕
                  </button>
                </div>
              </div>
            `;
          }).join('')}
        </div>
      </div>
    `;
  }

  /**
   * Render history page.
   */
  function renderHistory(container, data) {
    const items = data || [];

    if (items.length === 0) {
      container.innerHTML = `
        <div class="anim-fade-in">
          <div class="rec-hero">
            <div class="rec-hero-content">
              <h2 class="rec-hero-title"><span>🕐</span> Arama Geçmişi</h2>
              <p class="rec-hero-sub">Geçmiş hisse analizleriniz burada listelenir</p>
            </div>
          </div>
          <div class="glass-card" style="padding:48px;text-align:center;">
            <div class="empty-icon" style="font-size:3rem;">📋</div>
            <div class="empty-title">Henüz arama geçmişiniz yok</div>
            <div class="empty-desc">Hisse analiz yaptığınızda geçmişiniz burada görünecektir.</div>
          </div>
        </div>
      `;
      return;
    }

    const alCount = items.filter(i => i.action === 'AL').length;
    const satCount = items.filter(i => i.action === 'SAT').length;
    const tutCount = items.filter(i => i.action === 'TUT').length;

    container.innerHTML = `
      <div class="anim-fade-in">
        <div class="rec-hero">
          <div class="rec-hero-content">
            <h2 class="rec-hero-title"><span>🕐</span> Arama Geçmişi</h2>
            <p class="rec-hero-sub">Son ${items.length} analiz kaydı</p>
          </div>
          <div class="rec-hero-badge">
            <span class="rec-hero-badge-icon">📈</span>
            <span>${alCount} AL · ${satCount} SAT · ${tutCount} TUT</span>
          </div>
        </div>

        <div class="history-cards">
          ${items.map((item, idx) => {
            const actionBadgeClass = getActionBadgeClass(item.action || 'TUT');
            const actionEmoji = item.action === 'AL' ? '🟢' : item.action === 'SAT' ? '🔴' : '🟡';
            const confColor = getScoreColor(item.confidence || 0);
            
            return `
              <div class="history-card glass-card anim-slide-up stagger-${Math.min(idx + 1, 8)}"
                   onclick="window.StockPilot.analyzeStock('${item.symbol}')">
                <div class="history-card-left">
                  <div class="history-date">
                    <span class="history-date-icon">📅</span>
                    <span>${item.date || '—'}</span>
                  </div>
                  <div class="history-symbol-row">
                    <span class="history-symbol">${item.symbol}</span>
                    <span class="badge ${actionBadgeClass}">${actionEmoji} ${item.action || 'TUT'}</span>
                  </div>
                </div>
                <div class="history-card-right">
                  <div class="history-confidence">
                    <div class="rec-confidence-bar-wrap" style="width:100px;">
                      <div class="rec-confidence-bar">
                        <div class="rec-confidence-fill ${item.action === 'AL' ? 'gold' : item.action === 'SAT' ? 'slate' : 'neutral'}" style="width:${item.confidence || 0}%"></div>
                      </div>
                    </div>
                    <span class="rec-confidence-pct" style="color:${confColor}">%${item.confidence || 0}</span>
                  </div>
                  <div class="history-action-hint">Tekrar analiz et →</div>
                </div>
              </div>
            `;
          }).join('')}
        </div>
      </div>
    `;
  }

  // --- Mock Data ---

  function getMockDailyData() {
    return [
      { symbol: 'THYAO', name: 'Türk Hava Yolları', price: 312.40, changePercent: 3.25, action: 'AL', confidence: 87, reason: 'Güçlü teknik göstergeler ve yükselen trend desteği.' },
      { symbol: 'ASELS', name: 'Aselsan', price: 94.70, changePercent: 1.80, action: 'AL', confidence: 82, reason: 'Savunma sektörü talebi ve pozitif haber akışı.' },
      { symbol: 'SISE', name: 'Şişecam', price: 53.20, changePercent: -0.75, action: 'TUT', confidence: 65, reason: 'Nötr sinyaller. Destek seviyesi yakın.' },
      { symbol: 'EREGL', name: 'Ereğli Demir Çelik', price: 57.85, changePercent: -2.10, action: 'SAT', confidence: 71, reason: 'RSI aşırı alım bölgesinde, düzeltme bekleniyor.' },
      { symbol: 'KCHOL', name: 'Koç Holding', price: 186.50, changePercent: 0.95, action: 'AL', confidence: 78, reason: 'Holding iskontosu cazip seviyede.' },
      { symbol: 'GARAN', name: 'Garanti BBVA', price: 128.30, changePercent: 2.40, action: 'AL', confidence: 75, reason: 'Bankacılık sektöründe güçlü kar beklentisi.' },
      { symbol: 'TUPRS', name: 'Tüpraş', price: 178.60, changePercent: -1.30, action: 'TUT', confidence: 58, reason: 'Petrol fiyatlarındaki belirsizlik baskı yapıyor.' },
      { symbol: 'FROTO', name: 'Ford Otosan', price: 1145.00, changePercent: 0.45, action: 'TUT', confidence: 62, reason: 'Değerleme yüksek, fiyatlamada bekle-gör hakim.' },
    ];
  }

  function getMockWeeklyData() {
    return [
      { symbol: 'BIMAS', name: 'BİM Mağazalar', price: 246.80, changePercent: 4.15, action: 'AL', confidence: 91, reason: 'Enflasyona dayanıklı iş modeli, güçlü büyüme trendi devam ediyor.' },
      { symbol: 'SAHOL', name: 'Sabancı Holding', price: 89.45, changePercent: 2.70, action: 'AL', confidence: 85, reason: 'Enerji ve bankacılıktaki güçlü performans holdinge yansıyacak.' },
      { symbol: 'PGSUS', name: 'Pegasus', price: 762.50, changePercent: 5.20, action: 'AL', confidence: 83, reason: 'Yaz sezonu talebinde güçlü artış. Kapasite kullanımı yüksek.' },
      { symbol: 'AKBNK', name: 'Akbank', price: 68.30, changePercent: -1.50, action: 'TUT', confidence: 60, reason: 'Faiz ortamındaki değişimler bankacılık marjlarını etkileyebilir.' },
      { symbol: 'KOZAL', name: 'Koza Altın', price: 132.90, changePercent: -3.20, action: 'SAT', confidence: 74, reason: 'Altın fiyatlarında düşüş baskısı. Teknik göstergeler negatif.' },
      { symbol: 'TOASO', name: 'Tofaş', price: 215.30, changePercent: 1.85, action: 'AL', confidence: 77, reason: 'Otomotiv ihracatındaki artış olumlu sinyaller veriyor.' },
    ];
  }

  // --- Helpers ---

  function getActionBadgeClass(action) {
    const a = (action || '').toUpperCase();
    if (a === 'AL') return 'badge-al';
    if (a === 'SAT') return 'badge-sat';
    return 'badge-tut';
  }

  function getConfidenceBarColor(action) {
    const a = (action || '').toUpperCase();
    if (a === 'AL') return 'gold';
    if (a === 'SAT') return 'slate';
    return 'neutral';
  }

  function getScoreColor(score) {
    if (score >= 65) return '#c5a880'; // Gold
    if (score >= 40) return '#a0aec0'; // Slate/Silver
    return '#4a5568'; // Muted slate
  }

  function formatNumber(num) {
    if (num === null || num === undefined) return '—';
    return Number(num).toLocaleString('tr-TR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  function formatTurkishDate(date) {
    const months = ['Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran',
      'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık'];
    const days = ['Pazar', 'Pazartesi', 'Salı', 'Çarşamba', 'Perşembe', 'Cuma', 'Cumartesi'];
    return `${date.getDate()} ${months[date.getMonth()]} ${date.getFullYear()}, ${days[date.getDay()]}`;
  }

  return {
    renderDailyRecommendations,
    renderWeeklyRecommendations,
    renderRecSkeleton,
    renderWatchlist,
    renderHistory,
    filterRecs,
  };
})();
