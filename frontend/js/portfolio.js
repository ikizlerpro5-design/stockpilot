/* ============================================
   StockPilot — Portfolio Management Page Renderer
   ============================================ */

window.StockPilotPortfolio = (function () {
  'use strict';

  function formatNumber(num) {
    if (num === null || num === undefined) return '—';
    return Number(num).toLocaleString('tr-TR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
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

  /**
   * Render the Portfolio page.
   */
  function renderPortfolioPage(container) {
    container.innerHTML = `
      <div class="anim-fade-in">
        <div class="section-header">
          <h2 class="section-title"><span class="icon">💼</span> Portföyüm</h2>
        </div>
        
        <!-- Loading state -->
        <div id="portfolio-loading">
          <div class="skeleton skeleton-chart mb-24" style="height:120px;"></div>
          <div class="grid-2 mb-24">
            <div class="skeleton skeleton-card" style="height:200px;"></div>
            <div class="skeleton skeleton-card" style="height:200px;"></div>
          </div>
          <div class="skeleton skeleton-card" style="height:300px;"></div>
        </div>

        <div id="portfolio-content" style="display:none;"></div>
      </div>
    `;

    fetchAndRenderData();
  }

  /**
   * Fetch portfolio data from backend API and render tables.
   */
  async function fetchAndRenderData() {
    const loadingEl = document.getElementById('portfolio-loading');
    const contentEl = document.getElementById('portfolio-content');
    if (!loadingEl || !contentEl) return;

    try {
      const res = await fetch('/api/portfolio');
      if (!res.ok) throw new Error('Portföy verileri yüklenemedi.');
      const resData = await res.json();

      if (!resData.success) throw new Error(resData.error || 'Bilinmeyen hata');

      renderData(contentEl, resData);
      
      loadingEl.style.display = 'none';
      contentEl.style.display = 'block';
    } catch (err) {
      console.error(err);
      loadingEl.innerHTML = `
        <div class="empty-state" style="min-height: 40vh;">
          <div class="empty-icon">❌</div>
          <div class="empty-title">Veri Yüklenemedi</div>
          <div class="empty-desc">${err.message}</div>
          <button class="btn btn-primary mt-16" onclick="window.StockPilotPortfolio.refresh()">Tekrar Dene</button>
        </div>
      `;
    }
  }

  /**
   * Render portfolio data fields.
   */
  function renderData(container, data) {
    const summary = data.summary || { total_cost: 0, total_value: 0, total_profit_loss: 0, total_profit_loss_percent: 0 };
    const holdings = data.holdings || [];
    const transactions = data.transactions || [];

    const plClass = summary.total_profit_loss >= 0 ? 'up' : 'down';
    const plSign = summary.total_profit_loss >= 0 ? '+' : '';
    const plIcon = summary.total_profit_loss >= 0 ? '▲' : '▼';

    // Summary Widgets
    const summaryHtml = `
      <div class="grid-4 mb-24 anim-fade-in stagger-1">
        <div class="glass-card">
          <div style="font-size:0.8rem;color:var(--text-secondary);margin-bottom:8px;">Toplam Portföy Değeri</div>
          <div style="font-size:1.6rem;font-weight:700;color:var(--text-primary);">₺${formatNumber(summary.total_value)}</div>
          <div class="stock-change ${plClass}" style="font-size:0.82rem;font-weight:600;margin-top:6px;">
            ${plIcon} ${plSign}%${summary.total_profit_loss_percent.toFixed(2)}
          </div>
        </div>
        <div class="glass-card">
          <div style="font-size:0.8rem;color:var(--text-secondary);margin-bottom:8px;">Toplam Maliyet</div>
          <div style="font-size:1.6rem;font-weight:700;color:var(--text-primary);">₺${formatNumber(summary.total_cost)}</div>
          <div style="font-size:0.75rem;color:var(--text-muted);margin-top:6px;">Alım maliyetleri toplamı</div>
        </div>
        <div class="glass-card">
          <div style="font-size:0.8rem;color:var(--text-secondary);margin-bottom:8px;">Net Kar / Zarar</div>
          <div class="portfolio-pl-value ${summary.total_profit_loss >= 0 ? 'trend-up' : 'trend-down'}" style="font-size:1.6rem;font-weight:700;">
            ₺${formatNumber(summary.total_profit_loss)}
          </div>
          <div style="font-size:0.75rem;color:var(--text-muted);margin-top:6px;">Gerçekleşmemiş kar/zarar</div>
        </div>
        <div class="glass-card">
          <div style="font-size:0.8rem;color:var(--text-secondary);margin-bottom:8px;">Pozisyon Sayısı</div>
          <div style="font-size:1.6rem;font-weight:700;color:var(--text-primary);">${holdings.length} Hissedar</div>
          <div style="font-size:0.75rem;color:var(--text-muted);margin-top:6px;">Benzersiz hisse pozisyonu</div>
        </div>
      </div>
    `;

    // Add Transaction Form
    const formHtml = `
      <div class="glass-card mb-24 anim-fade-in stagger-2">
        <h3 class="mb-16 text-primary" style="font-size:1.1rem;font-weight:600;display:flex;align-items:center;gap:8px;">
          <span>➕</span> Yeni Alım İşlemi Ekle
        </h3>
        <form id="portfolio-add-form" onsubmit="window.StockPilotPortfolio.handleAdd(event)" style="display:grid; grid-template-columns: 1fr 1fr 1fr auto; gap:16px; align-items:end;">
          <div>
            <label class="form-label" for="port-symbol" style="display:block;font-size:0.78rem;color:var(--text-secondary);margin-bottom:6px;">Hisse Kodu</label>
            <input class="form-input" type="text" id="port-symbol" placeholder="Örn: THYAO" required autocomplete="off" style="width:100%;padding:10px 14px;background:rgba(255,255,255,0.03);border:1px solid var(--glass-border);border-radius:var(--radius-sm);color:var(--text-primary);font-weight:600;text-transform:uppercase;">
          </div>
          <div>
            <label class="form-label" for="port-price" style="display:block;font-size:0.78rem;color:var(--text-secondary);margin-bottom:6px;">Alış Fiyatı (₺)</label>
            <input class="form-input" type="number" id="port-price" step="0.01" min="0.01" placeholder="0.00" required style="width:100%;padding:10px 14px;background:rgba(255,255,255,0.03);border:1px solid var(--glass-border);border-radius:var(--radius-sm);color:var(--text-primary);">
          </div>
          <div>
            <label class="form-label" for="port-qty" style="display:block;font-size:0.78rem;color:var(--text-secondary);margin-bottom:6px;">Miktar (Adet)</label>
            <input class="form-input" type="number" id="port-qty" step="0.0001" min="0.0001" placeholder="0" required style="width:100%;padding:10px 14px;background:rgba(255,255,255,0.03);border:1px solid var(--glass-border);border-radius:var(--radius-sm);color:var(--text-primary);">
          </div>
          <button class="btn btn-primary" type="submit" style="padding:11px 24px;">Portföye Ekle</button>
        </form>
      </div>
    `;

    // Positions Table
    let holdingsHtml = '';
    if (holdings.length === 0) {
      holdingsHtml = `
        <div style="padding:40px;text-align:center;color:var(--text-muted);font-size:0.88rem;">
          Henüz portföyünüzde aktif pozisyon bulunmuyor. Yukarıdaki formu kullanarak alım işlemi ekleyin!
        </div>
      `;
    } else {
      holdingsHtml = `
        <div style="overflow-x:auto;">
          <table class="portfolio-table" style="width:100%;border-collapse:collapse;text-align:left;font-size:0.88rem;">
            <thead>
              <tr style="border-bottom:1px solid var(--glass-border);color:var(--text-secondary);">
                <th style="padding:14px 12px;">Hisse</th>
                <th style="padding:14px 12px;text-align:right;">Miktar</th>
                <th style="padding:14px 12px;text-align:right;">Ort. Maliyet</th>
                <th style="padding:14px 12px;text-align:right;">Güncel Fiyat</th>
                <th style="padding:14px 12px;text-align:right;">Toplam Maliyet</th>
                <th style="padding:14px 12px;text-align:right;">Güncel Değer</th>
                <th style="padding:14px 12px;text-align:right;">Kar / Zarar</th>
              </tr>
            </thead>
            <tbody>
              ${holdings.map(h => {
                const badgeStyle = getBadgeStyle(h.symbol);
                const itemPlClass = h.profit_loss >= 0 ? 'trend-up' : 'trend-down';
                const itemPlSign = h.profit_loss >= 0 ? '+' : '';
                const logoHtml = h.logo_url
                  ? `<img src="${h.logo_url}" alt="${h.symbol}" style="width:100%;height:100%;object-fit:contain;border-radius:4px;" onerror="this.parentElement.innerHTML='${h.symbol.substring(0, 2)}'; this.parentElement.style.cssText='width:28px;height:28px;border-radius:6px;${badgeStyle}';">`
                  : `<div style="width:28px;height:28px;border-radius:6px;${badgeStyle}">${h.symbol.substring(0, 2)}</div>`;

                return `
                  <tr style="border-bottom:1px solid rgba(255,255,255,0.03);cursor:pointer;transition:background 0.2s;" onclick="window.StockPilot.analyzeStock('${h.symbol}')" class="portfolio-row-hover">
                    <td style="padding:14px 12px;display:flex;align-items:center;gap:12px;">
                      <div style="width:28px;height:28px;border-radius:6px;background:#12121e;border:1px solid var(--glass-border);display:flex;align-items:center;justify-content:center;overflow:hidden;flex-shrink:0;">
                        ${logoHtml}
                      </div>
                      <div>
                        <span style="font-weight:700;color:var(--text-primary);">${h.symbol}</span>
                        <span style="display:block;font-size:0.75rem;color:var(--text-secondary);max-width:140px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${h.name}</span>
                      </div>
                    </td>
                    <td style="padding:14px 12px;text-align:right;font-weight:500;">${h.quantity}</td>
                    <td style="padding:14px 12px;text-align:right;font-variant-numeric:tabular-nums;">₺${formatNumber(h.avg_buy_price)}</td>
                    <td style="padding:14px 12px;text-align:right;font-variant-numeric:tabular-nums;">₺${formatNumber(h.current_price)}</td>
                    <td style="padding:14px 12px;text-align:right;font-variant-numeric:tabular-nums;">₺${formatNumber(h.total_cost)}</td>
                    <td style="padding:14px 12px;text-align:right;font-variant-numeric:tabular-nums;font-weight:600;">₺${formatNumber(h.current_value)}</td>
                    <td style="padding:14px 12px;text-align:right;font-variant-numeric:tabular-nums;font-weight:700;" class="${itemPlClass}">
                      ₺${formatNumber(h.profit_loss)}
                      <span style="display:block;font-size:0.72rem;font-weight:600;">${itemPlSign}${h.profit_loss_percent.toFixed(2)}%</span>
                    </td>
                  </tr>
                `;
              }).join('')}
            </tbody>
          </table>
        </div>
      `;
    }

    // Transaction History Table
    let txHtml = '';
    if (transactions.length === 0) {
      txHtml = `
        <div style="padding:24px;text-align:center;color:var(--text-muted);font-size:0.8rem;">
          Herhangi bir işlem geçmişi bulunmuyor.
        </div>
      `;
    } else {
      txHtml = `
        <div style="overflow-x:auto;">
          <table style="width:100%;border-collapse:collapse;text-align:left;font-size:0.82rem;">
            <thead>
              <tr style="border-bottom:1px solid var(--glass-border);color:var(--text-secondary);">
                <th style="padding:10px 12px;">Hisse</th>
                <th style="padding:10px 12px;">Tarih</th>
                <th style="padding:10px 12px;text-align:right;">Alış Fiyatı</th>
                <th style="padding:10px 12px;text-align:right;">Miktar</th>
                <th style="padding:10px 12px;text-align:right;">Toplam Tutar</th>
                <th style="padding:10px 12px;text-align:center;">İşlem</th>
              </tr>
            </thead>
            <tbody>
              ${transactions.map(t => `
                <tr style="border-bottom:1px solid rgba(255,255,255,0.02);">
                  <td style="padding:10px 12px;font-weight:600;color:var(--green);">${t.symbol}</td>
                  <td style="padding:10px 12px;color:var(--text-secondary);">${formatDateString(t.added_at)}</td>
                  <td style="padding:10px 12px;text-align:right;font-variant-numeric:tabular-nums;">₺${formatNumber(t.buy_price)}</td>
                  <td style="padding:10px 12px;text-align:right;">${t.quantity}</td>
                  <td style="padding:10px 12px;text-align:right;font-variant-numeric:tabular-nums;font-weight:500;">₺${formatNumber(t.buy_price * t.quantity)}</td>
                  <td style="padding:10px 12px;text-align:center;">
                    <button class="btn btn-ghost" onclick="window.StockPilotPortfolio.handleDelete(${t.id})" style="padding:4px 8px;color:var(--red);font-size:0.75rem;border-radius:4px;border:1px solid rgba(255,71,87,0.15);background:rgba(255,71,87,0.05);">
                      Sil
                    </button>
                  </td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      `;
    }

    container.innerHTML = `
      ${summaryHtml}
      ${formHtml}
      
      <!-- Holdings Grid -->
      <div class="glass-card-static mb-24 anim-fade-in stagger-3">
        <h3 class="mb-16 text-primary" style="font-size:1.1rem;font-weight:600;display:flex;align-items:center;gap:8px;">
          <span>📈</span> Aktif Pozisyonlar
        </h3>
        ${holdingsHtml}
      </div>

      <!-- Transactions Grid -->
      <div class="glass-card-static anim-fade-in stagger-4">
        <h3 class="mb-16 text-primary" style="font-size:1.1rem;font-weight:600;display:flex;align-items:center;gap:8px;">
          <span>📜</span> İşlem Geçmişi
        </h3>
        ${txHtml}
      </div>
    `;
  }

  /**
   * Handle form submit to add transaction.
   */
  async function handleAdd(event) {
    event.preventDefault();

    const symInput = document.getElementById('port-symbol');
    const priceInput = document.getElementById('port-price');
    const qtyInput = document.getElementById('port-qty');

    if (!symInput || !priceInput || !qtyInput) return;

    const symbol = symInput.value.toUpperCase().trim();
    const buy_price = parseFloat(priceInput.value);
    const quantity = parseFloat(qtyInput.value);

    if (!symbol) {
      window.StockPilot.showToast('Lütfen geçerli bir hisse kodu girin.', 'error');
      return;
    }

    try {
      const res = await fetch('/api/portfolio', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ symbol, buy_price, quantity })
      });

      const resData = await res.json();
      if (!res.ok || !resData.success) {
        throw new Error(resData.error || 'İşlem eklenemedi.');
      }

      window.StockPilot.showToast(resData.mesaj, 'success');
      
      // Clear form
      symInput.value = '';
      priceInput.value = '';
      qtyInput.value = '';

      // Reload
      fetchAndRenderData();
    } catch (err) {
      window.StockPilot.showToast(err.message, 'error');
    }
  }

  /**
   * Handle delete action.
   */
  async function handleDelete(txId) {
    if (!confirm('Bu işlemi silmek istediğinize emin misiniz?')) return;

    try {
      const res = await fetch(`/api/portfolio/${txId}`, { method: 'DELETE' });
      const resData = await res.json();

      if (!res.ok || !resData.success) {
        throw new Error(resData.error || 'İşlem silinemedi.');
      }

      window.StockPilot.showToast(resData.mesaj, 'success');
      fetchAndRenderData();
    } catch (err) {
      window.StockPilot.showToast(err.message, 'error');
    }
  }

  /**
   * Format datetime string to Turkish layout.
   */
  function formatDateString(str) {
    if (!str) return '—';
    try {
      const parts = str.split(' ');
      if (parts.length >= 2) {
        // YYYY-MM-DD
        const dateParts = parts[0].split('-');
        // HH:MM:SS -> HH:MM
        const timeParts = parts[1].split(':');
        return `${dateParts[2]}.${dateParts[1]}.${dateParts[0]} ${timeParts[0]}:${timeParts[1]}`;
      }
      return str;
    } catch (e) {
      return str;
    }
  }

  return {
    renderPortfolioPage,
    handleAdd,
    handleDelete,
    refresh: fetchAndRenderData
  };
})();
