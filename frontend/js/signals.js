/* ============================================
   StockPilot V2.0 — Aktif Sinyaller Sayfası
   ============================================ */

window.StockPilotSignals = (function () {
  'use strict';

  function renderSignalsPage(container) {
    container.innerHTML = `
      <div class="page-enter">
        <div class="rec-hero">
          <div class="rec-hero-content">
            <h2 class="rec-hero-title"><span>⚡</span> Aktif Sinyaller</h2>
            <p class="rec-hero-sub">Tüm BIST hisseleri için anlık AL/SAT sinyalleri, giriş/çıkış noktaları ve risk analizi</p>
          </div>
          <div class="rec-hero-badge">
            <span class="rec-hero-badge-icon">🔬</span>
            <span>Teknik & Duygu Analizi</span>
          </div>
        </div>

        <div class="signals-summary-bar" id="signalsSummary">
          <div class="signal-summary-item total"><div class="ss-count">—</div><div class="ss-label">Toplam</div></div>
          <div class="signal-summary-item al"><div class="ss-count">—</div><div class="ss-label">🟢 AL</div></div>
          <div class="signal-summary-item sat"><div class="ss-count">—</div><div class="ss-label">🔴 SAT</div></div>
          <div class="signal-summary-item tut"><div class="ss-count">—</div><div class="ss-label">🟡 TUT</div></div>
        </div>

        <div class="rec-filters" id="signalFilterBtns">
          <button class="rec-filter active" data-filter="all" onclick="StockPilotSignals.filterSignals('all')"><span class="rec-filter-icon">📋</span> Tümü</button>
          <button class="rec-filter" data-filter="AL" onclick="StockPilotSignals.filterSignals('AL')"><span class="rec-filter-dot al"></span> AL Sinyalleri</button>
          <button class="rec-filter" data-filter="SAT" onclick="StockPilotSignals.filterSignals('SAT')"><span class="rec-filter-dot sat"></span> SAT Sinyalleri</button>
          <button class="rec-filter" data-filter="TUT" onclick="StockPilotSignals.filterSignals('TUT')"><span class="rec-filter-dot tut"></span> TUT</button>
        </div>

        <div id="signalsContent">
          <div class="loading-container">
            <div class="loading-spinner"></div>
            <p class="loading-text">Sinyaller hesaplanıyor...</p>
          </div>
        </div>
      </div>
    `;

    loadSignals();
  }

  let _allSignals = [];

  async function loadSignals() {
    try {
      const res = await fetch('/api/signals');
      const data = await res.json();

      if (!data.success) {
        document.getElementById('signalsContent').innerHTML = `
          <div class="empty-state">
            <div class="empty-icon">❌</div>
            <div class="empty-title">Sinyal Yüklenemedi</div>
            <div class="empty-desc">${data.error || 'Bilinmeyen hata'}</div>
          </div>
        `;
        return;
      }

      _allSignals = data.sinyaller || [];
      const ozet = data.ozet || {};
      const total = ozet.toplam || _allSignals.length;
      const al = ozet.al_sayisi || 0;
      const sat = ozet.sat_sayisi || 0;
      const tut = ozet.tut_sayisi || 0;

      // Update summary bar with visual distribution
      const summaryEl = document.getElementById('signalsSummary');
      if (summaryEl) {
        const alPct = total > 0 ? (al / total * 100) : 0;
        const satPct = total > 0 ? (sat / total * 100) : 0;
        const tutPct = total > 0 ? (tut / total * 100) : 0;
        
        summaryEl.innerHTML = `
          <div class="signal-summary-item total">
            <div class="ss-count">${total}</div>
            <div class="ss-label">Toplam Hisse</div>
          </div>
          <div class="signal-summary-item al">
            <div class="ss-count">${al}</div>
            <div class="ss-label">🟢 AL</div>
            <div class="ss-sub">%${alPct.toFixed(0)}</div>
          </div>
          <div class="signal-summary-item sat">
            <div class="ss-count">${sat}</div>
            <div class="ss-label">🔴 SAT</div>
            <div class="ss-sub">%${satPct.toFixed(0)}</div>
          </div>
          <div class="signal-summary-item tut">
            <div class="ss-count">${tut}</div>
            <div class="ss-label">🟡 TUT</div>
            <div class="ss-sub">%${tutPct.toFixed(0)}</div>
          </div>
          <div class="signal-distribution">
            <div class="signal-dist-bar al" style="width:${alPct}%"></div>
            <div class="signal-dist-bar sat" style="width:${satPct}%"></div>
            <div class="signal-dist-bar tut" style="width:${tutPct}%"></div>
          </div>
        `;
      }

      renderSignalsList(_allSignals);
    } catch (err) {
      document.getElementById('signalsContent').innerHTML = `
        <div class="empty-state">
          <div class="empty-icon">⚠️</div>
          <div class="empty-title">Bağlantı Hatası</div>
          <div class="empty-desc">Sunucuya bağlanılamadı: ${err.message}</div>
        </div>
      `;
    }
  }

  function renderSignalsList(signals) {
    const container = document.getElementById('signalsContent');
    if (!container) return;

    if (!signals || signals.length === 0) {
      container.innerHTML = `
        <div class="empty-state" style="padding:48px;">
          <div class="empty-icon">📊</div>
          <div class="empty-title">Sinyal Bulunamadı</div>
          <div class="empty-desc">Filtreye uygun sinyal yok.</div>
        </div>
      `;
      return;
    }

    // Modern cards view
    let html = '<div class="signal-cards-grid">';
    
    for (const s of signals) {
      const chgClass = (s.degisim_yuzde || 0) >= 0 ? 'up' : 'down';
      const chgSign = (s.degisim_yuzde || 0) >= 0 ? '+' : '';
      const badgeClass = (s.aksiyon || 'TUT').toLowerCase();
      const actionEmoji = s.aksiyon === 'AL' ? '🟢' : s.aksiyon === 'SAT' ? '🔴' : '🟡';
      const riskOdul = (s.risk_odul_orani || 0).toFixed(1);

      html += `
        <div class="signal-card glass-card" onclick="window.StockPilot.analyzeStock('${s.sembol_kisa || ''}')">
          <div class="signal-card-top">
            <div class="signal-card-logo-area">
              ${s.logo_url ? `<img src="${s.logo_url}" alt="${s.sembol_kisa}" class="signal-logo" onerror="this.style.display='none'">` : ''}
              <span class="signal-symbol-text">${(s.sembol_kisa || '').substring(0, 2)}</span>
            </div>
            <div class="signal-card-info">
              <div class="signal-symbol-name">${s.sembol_kisa || ''}</div>
              <div class="signal-company">${s.isim || ''}</div>
            </div>
            <span class="badge badge-${badgeClass} signal-badge-lg">${actionEmoji} ${s.aksiyon || 'TUT'}</span>
          </div>

          <div class="signal-price-row">
            <div class="signal-price-main">₺${(s.fiyat || 0).toFixed(2)}</div>
            <div class="signal-price-change ${chgClass}">${chgSign}${(s.degisim_yuzde || 0).toFixed(2)}%</div>
          </div>

          <div class="signal-targets-row">
            <div class="signal-target">
              <span class="signal-target-label">🎯 Giriş</span>
              <span class="signal-target-val">₺${(s.giris_fiyati || 0).toFixed(2)}</span>
            </div>
            <div class="signal-target-arrow">→</div>
            <div class="signal-target">
              <span class="signal-target-label">🏁 Hedef</span>
              <span class="signal-target-val hedef">₺${(s.hedef_1 || 0).toFixed(2)}</span>
            </div>
          </div>

          <div class="signal-bottom-row">
            <div class="signal-risk-info">
              <span class="signal-stop">🛑 Stop: ₺${(s.stop_loss || 0).toFixed(2)}</span>
              <span class="signal-rr">⚖️ R/Ö: ${riskOdul}x</span>
            </div>
            <div class="signal-confidence">
              <div class="rec-confidence-bar-wrap" style="width:80px;">
                <div class="rec-confidence-bar">
                  <div class="rec-confidence-fill ${s.aksiyon === 'AL' ? 'gold' : s.aksiyon === 'SAT' ? 'slate' : 'neutral'}" style="width:${s.guven || 0}%"></div>
                </div>
              </div>
              <span class="signal-guv">%${s.guven || 0}</span>
            </div>
          </div>
        </div>
      `;
    }

    html += '</div>';
    container.innerHTML = html;
  }

  function filterSignals(filter) {
    const btns = document.querySelectorAll('#signalFilterBtns .rec-filter');
    btns.forEach(btn => {
      btn.classList.toggle('active', btn.dataset.filter === filter);
    });

    if (filter === 'all') {
      renderSignalsList(_allSignals);
    } else {
      const filtered = _allSignals.filter(s => s.aksiyon === filter);
      renderSignalsList(filtered);
    }
  }

  return {
    renderSignalsPage,
    filterSignals
  };
})();
