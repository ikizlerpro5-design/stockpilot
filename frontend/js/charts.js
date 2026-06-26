/* ============================================
   StockPilot — TradingView Lightweight Charts
   ============================================ */

window.StockPilotCharts = (function () {
  'use strict';

  const chartTheme = {
    layout: {
      background: { type: 'solid', color: 'transparent' },
      backgroundColor: 'transparent',
      textColor: '#8888a0',
      fontFamily: "'Inter', system-ui, sans-serif",
      fontSize: 12,
    },
    grid: {
      vertLines: { color: 'rgba(255,255,255,0.04)' },
      horzLines: { color: 'rgba(255,255,255,0.04)' },
    },
    crosshair: {
      vertLine: {
        color: 'rgba(255,255,255,0.15)',
        width: 1,
        style: 2,
        labelBackgroundColor: '#1a1a2e',
      },
      horzLine: {
        color: 'rgba(255,255,255,0.15)',
        width: 1,
        style: 2,
        labelBackgroundColor: '#1a1a2e',
      },
    },
    timeScale: {
      borderColor: 'rgba(255,255,255,0.06)',
      timeVisible: true,
      secondsVisible: false,
      rightOffset: 5,
      barSpacing: 8,
    },
    rightPriceScale: {
      borderColor: 'rgba(255,255,255,0.06)',
      scaleMargins: { top: 0.1, bottom: 0.2 },
    },
  };

  const miniChartTheme = {
    layout: {
      background: { type: 'solid', color: 'transparent' },
      textColor: 'transparent',
      fontFamily: "'Inter', system-ui, sans-serif",
    },
    grid: {
      vertLines: { visible: false },
      horzLines: { visible: false },
    },
    crosshair: {
      mode: 0,
      vertLine: { visible: false },
      horzLine: { visible: false },
    },
    timeScale: { visible: false },
    rightPriceScale: { visible: false },
    leftPriceScale: { visible: false },
    handleScroll: false,
    handleScale: false,
  };

  // Active chart instances for cleanup
  const activeCharts = {};

  /**
   * Create the main stock chart (candlestick + volume + SMA overlays).
   */
  function createStockChart(containerId, candleData, sma50Data, sma200Data) {
    const container = document.getElementById(containerId);
    if (!container) return null;

    if (typeof LightweightCharts === 'undefined') {
      container.innerHTML = `<div style="display:flex;flex-direction:column;align-items:center;justify-content:center;height:100%;color:var(--text-secondary);font-size:0.85rem;padding:12px;text-align:center;">
        <span style="font-size:1.2rem;margin-bottom:4px;">📉</span>
        <span>Grafik yüklenemedi. (İnternet bağlantısını kontrol edin)</span>
      </div>`;
      return null;
    }

    try {
      // Cleanup previous chart
      if (activeCharts[containerId]) {
        try {
          activeCharts[containerId].remove();
        } catch(e) {}
        delete activeCharts[containerId];
      }
      container.innerHTML = '';

      const width = container.clientWidth || 800;
      const height = container.clientHeight || 420;

      const chart = LightweightCharts.createChart(container, {
        ...chartTheme,
        width: width,
        height: height,
        localization: {
          locale: 'tr-TR',
          dateFormat: 'dd.MM.yyyy',
        },
      });

      activeCharts[containerId] = chart;

      // Candlestick series
      const candleSeries = chart.addCandlestickSeries({
        upColor: '#c5a880',
        downColor: '#718096',
        borderDownColor: '#718096',
        borderUpColor: '#c5a880',
        wickDownColor: '#718096',
        wickUpColor: '#c5a880',
      });

      let sortedCandles = [];
      const seenTimes = new Set();

      if (candleData && candleData.length > 0) {
        sortedCandles = [...candleData]
          .sort((a, b) => a.time.localeCompare(b.time))
          .filter(item => {
            if (!item.time) return false;
            if (seenTimes.has(item.time)) return false;
            seenTimes.add(item.time);
            return true;
          });
        
        candleSeries.setData(sortedCandles);
      }

      // Volume histogram (resilient overlay)
      if (sortedCandles.length > 0) {
        try {
          const volumeSeries = chart.addHistogramSeries({
            priceFormat: { type: 'volume' },
            priceScaleId: 'volume',
          });

          chart.priceScale('volume').applyOptions({
            scaleMargins: { top: 0.8, bottom: 0 },
          });

          const volumeData = sortedCandles.map((d) => ({
            time: d.time,
            value: d.volume || 0,
            color: d.close >= d.open ? 'rgba(0,212,170,0.2)' : 'rgba(255,71,87,0.2)',
          }));
          volumeSeries.setData(volumeData);
        } catch (volErr) {
          console.warn("Hacim grafigi cizilemedi:", volErr);
        }
      }

      // SMA 50
      if (sma50Data && sma50Data.length > 0) {
        try {
          const sma50Series = chart.addLineSeries({
            color: '#5352ed',
            lineWidth: 2,
            crosshairMarkerVisible: false,
            priceLineVisible: false,
            lastValueVisible: false,
          });
          
          const smaSeen = new Set();
          const sortedSma50 = [...sma50Data]
            .sort((a, b) => a.time.localeCompare(b.time))
            .filter(d => {
              if (smaSeen.has(d.time)) return false;
              smaSeen.add(d.time);
              return seenTimes.has(d.time); // ensure date exists in main candle data
            });
          
          sma50Series.setData(sortedSma50);
        } catch (smaErr) {
          console.warn("SMA 50 cizilemedi:", smaErr);
        }
      }

      // SMA 200
      if (sma200Data && sma200Data.length > 0) {
        try {
          const sma200Series = chart.addLineSeries({
            color: '#ffa502',
            lineWidth: 2,
            crosshairMarkerVisible: false,
            priceLineVisible: false,
            lastValueVisible: false,
          });
          
          const smaSeen2 = new Set();
          const sortedSma200 = [...sma200Data]
            .sort((a, b) => a.time.localeCompare(b.time))
            .filter(d => {
              if (smaSeen2.has(d.time)) return false;
              smaSeen2.add(d.time);
              return seenTimes.has(d.time);
            });
            
          sma200Series.setData(sortedSma200);
        } catch (sma200Err) {
          console.warn("SMA 200 cizilemedi:", sma200Err);
        }
      }

      // Fit content
      chart.timeScale().fitContent();

      // Responsive resize
      const resizeObserver = new ResizeObserver((entries) => {
        for (const entry of entries) {
          const { width, height } = entry.contentRect;
          if (width > 0 && height > 0) {
            chart.applyOptions({ width, height });
          }
        }
      });
      resizeObserver.observe(container);
      chart._resizeObserver = resizeObserver;

      return chart;
    } catch (e) {
      console.error("Grafik cizim ana hatasi:", e);
      container.innerHTML = `<div style="display:flex;align-items:center;justify-content:center;height:100%;color:var(--text-secondary);font-size:0.85rem;">Grafik Yuklenemedi: ${e.message}</div>`;
      return null;
    }
  }

  /**
   * Create a mini area chart for dashboards/cards.
   */
  function createMiniChart(containerId, data, isPositive) {
    const container = document.getElementById(containerId);
    if (!container) return null;

    if (typeof LightweightCharts === 'undefined') {
      container.innerHTML = `<div style="display:flex;align-items:center;justify-content:center;height:100%;color:var(--text-muted);font-size:0.75rem;">—</div>`;
      return null;
    }

    // Cleanup
    if (activeCharts[containerId]) {
      activeCharts[containerId].remove();
      delete activeCharts[containerId];
    }
    container.innerHTML = '';

    const positive = isPositive !== false;
    const color = positive ? '#c5a880' : '#718096';

    const chart = LightweightCharts.createChart(container, {
      ...miniChartTheme,
      width: container.clientWidth,
      height: container.clientHeight || 50,
    });

    activeCharts[containerId] = chart;

    const areaSeries = chart.addAreaSeries({
      lineColor: color,
      lineWidth: 1.5,
      topColor: positive ? 'rgba(197,168,128,0.25)' : 'rgba(113,128,150,0.25)',
      bottomColor: positive ? 'rgba(197,168,128,0.02)' : 'rgba(113,128,150,0.02)',
      crosshairMarkerVisible: false,
      priceLineVisible: false,
      lastValueVisible: false,
    });

    if (data && data.length > 0) {
      areaSeries.setData(data);
    }

    chart.timeScale().fitContent();

    // Responsive
    const resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width, height } = entry.contentRect;
        chart.applyOptions({ width, height });
      }
    });
    resizeObserver.observe(container);
    chart._resizeObserver = resizeObserver;

    return chart;
  }

  /**
   * Destroy a chart and clean up resources.
   */
  function destroyChart(containerId) {
    if (activeCharts[containerId]) {
      if (activeCharts[containerId]._resizeObserver) {
        activeCharts[containerId]._resizeObserver.disconnect();
      }
      activeCharts[containerId].remove();
      delete activeCharts[containerId];
    }
  }

  /**
   * Destroy all active charts.
   */
  function destroyAll() {
    Object.keys(activeCharts).forEach(destroyChart);
  }

  /**
   * Generate mock candlestick data for demo purposes.
   */
  function generateMockCandleData(days, startPrice) {
    const data = [];
    let price = startPrice || 50 + Math.random() * 100;
    const now = new Date();
    const startDate = new Date(now);
    startDate.setDate(startDate.getDate() - days);

    for (let i = 0; i < days; i++) {
      const date = new Date(startDate);
      date.setDate(date.getDate() + i);
      // Skip weekends
      if (date.getDay() === 0 || date.getDay() === 6) continue;

      const open = price;
      const volatility = price * 0.03;
      const change = (Math.random() - 0.48) * volatility;
      const close = open + change;
      const high = Math.max(open, close) + Math.random() * volatility * 0.5;
      const low = Math.min(open, close) - Math.random() * volatility * 0.5;
      const volume = Math.floor(1000000 + Math.random() * 5000000);

      data.push({
        time: date.toISOString().split('T')[0],
        open: parseFloat(open.toFixed(2)),
        high: parseFloat(high.toFixed(2)),
        low: parseFloat(low.toFixed(2)),
        close: parseFloat(close.toFixed(2)),
        volume: volume,
      });

      price = close;
    }
    return data;
  }

  /**
   * Generate SMA data from candle data.
   */
  function calculateSMA(candleData, period) {
    const result = [];
    for (let i = period - 1; i < candleData.length; i++) {
      let sum = 0;
      for (let j = 0; j < period; j++) {
        sum += candleData[i - j].close;
      }
      result.push({
        time: candleData[i].time,
        value: parseFloat((sum / period).toFixed(2)),
      });
    }
    return result;
  }

  /**
   * Generate mock line data for mini charts.
   */
  function generateMockLineData(days, startPrice, trend) {
    const data = [];
    let price = startPrice || 100;
    const now = new Date();
    const startDate = new Date(now);
    startDate.setDate(startDate.getDate() - days);

    for (let i = 0; i < days; i++) {
      const date = new Date(startDate);
      date.setDate(date.getDate() + i);
      if (date.getDay() === 0 || date.getDay() === 6) continue;

      const trendFactor = trend === 'up' ? 0.003 : trend === 'down' ? -0.003 : 0;
      price = price * (1 + trendFactor + (Math.random() - 0.5) * 0.02);

      data.push({
        time: date.toISOString().split('T')[0],
        value: parseFloat(price.toFixed(2)),
      });
    }
    return data;
  }

  return {
    createStockChart,
    createMiniChart,
    destroyChart,
    destroyAll,
    generateMockCandleData,
    calculateSMA,
    generateMockLineData,
  };
})();
