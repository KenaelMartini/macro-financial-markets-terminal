/* ── Shared Lightweight Charts options (MKTM, FXDASH, etc.) ─ */
(function (global) {
  var LAYOUT = {
    backgroundColor: '#060a10',
    textColor: '#8a9bb0',
  };
  var GRID = {
    vertLines: { color: '#1c2a3a' },
    horzLines: { color: '#1c2a3a' },
  };

  /** Same candlestick styling for all assets; FX needs finer priceFormat or bodies look like a line. */
  function candlestickSeriesOptions(symbol) {
    var o = {
      upColor: '#00d68f',
      downColor: '#ff4757',
      borderVisible: true,
      borderUpColor: '#00d68f',
      borderDownColor: '#ff4757',
      wickUpColor: '#b8f5d9',
      wickDownColor: '#ffb3bc',
    };
    var u = (symbol || '').toUpperCase();
    if (u.endsWith('=X')) {
      if (u.indexOf('JPY') !== -1) {
        o.priceFormat = { type: 'price', precision: 3, minMove: 0.001 };
      } else {
        o.priceFormat = { type: 'price', precision: 5, minMove: 0.00001 };
      }
    }
    return o;
  }

  function createChartOptions(width, height) {
    return {
      layout: LAYOUT,
      grid: GRID,
      width: width,
      height: height,
      rightPriceScale: {
        borderVisible: true,
        borderColor: '#1c2a3a',
        scaleMargins: { top: 0.08, bottom: 0.08 },
      },
      timeScale: {
        borderVisible: true,
        borderColor: '#1c2a3a',
      },
    };
  }

  global.terminalChartDefaults = {
    candlestickSeriesOptions: candlestickSeriesOptions,
    createChartOptions: createChartOptions,
  };
})(typeof window !== 'undefined' ? window : this);
