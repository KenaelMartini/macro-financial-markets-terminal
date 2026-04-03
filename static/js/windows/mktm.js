/* ── MKTM screen: chart + instrument grid (click = candles) ─ */

(function(){
  var el;
  var _chart = null;
  var _series = null;
  var _selectedSymbol = 'EURUSD=X';
  var _selectedInterval = '1d';
  var _selectedPeriod = '5y';
  var _resizeBound = false;
  var _liveTimer = null;
  var _lastCandleTime = null;

  function init(container){
    el = container;
    el.innerHTML =
      '<div class="mktm-wrap">'+
        '<div class="mktm-chart-panel">'+
          '<div class="mktm-chart-head">'+
            '<span id="mktmChartTitle">EUR/USD</span>'+
            '<span class="mktm-chart-hint">IBKR chandeliers — focus prix + timeframe</span>'+
            '<span style="margin-left:auto;font-size:10px;color:var(--text-dim)">TF</span>'+
            '<select id="mktmTfSel" style="height:22px;background:#0d141d;color:#c4d4e5;border:1px solid #1f3346;border-radius:4px">'+
              '<option value="1h">H1</option><option value="4h">H4</option><option value="8h">H8</option><option value="1d" selected>D1</option>'+
            '</select>'+
          '</div>'+
          '<div id="mktmChartEl" class="mktm-chart-el"></div>'+
        '</div>'+
        '<div class="mktm-grid" id="mktmGrid"></div>'+
      '</div>';
    if(!_resizeBound){
      _resizeBound = true;
      window.addEventListener('resize', function(){
        if(_chart && document.getElementById('mktmChartEl')){
          _chart.applyOptions({ width: document.getElementById('mktmChartEl').clientWidth });
        }
      });
    }
    var tfSel = document.getElementById('mktmTfSel');
    if(tfSel){
      tfSel.addEventListener('change', function(e){
        _selectedInterval = e.target.value || '1d';
        _selectedPeriod = (_selectedInterval === '1d') ? '5y' : '1y';
        loadCandles(_selectedSymbol);
      });
    }
  }

  function ensureChart(){
    if(typeof LightweightCharts === 'undefined'){
      document.getElementById('mktmChartEl').innerHTML =
        '<div class="empty-state" style="padding:24px">Chart library failed to load. Check network / CDN.</div>';
      return false;
    }
    var box = document.getElementById('mktmChartEl');
    if(!box) return false;
    if(_chart) return true;
    var defs = window.terminalChartDefaults;
    var opts = defs && defs.createChartOptions
      ? defs.createChartOptions(box.clientWidth || 800, 280)
      : {
          layout: { backgroundColor: '#060a10', textColor: '#8a9bb0' },
          grid: { vertLines: { color: '#1c2a3a' }, horzLines: { color: '#1c2a3a' } },
          width: box.clientWidth || 800,
          height: 280
        };
    _chart = LightweightCharts.createChart(box, opts);
    _series = _chart.addCandlestickSeries(seriesOptionsForSymbol(_selectedSymbol));
    return true;
  }

  function seriesOptionsForSymbol(symbol){
    var defs = window.terminalChartDefaults;
    var base = defs && defs.candlestickSeriesOptions
      ? defs.candlestickSeriesOptions(symbol)
      : {
          upColor: '#00d68f',
          downColor: '#ff4757',
          borderVisible: true,
          borderUpColor: '#00d68f',
          borderDownColor: '#ff4757',
          wickUpColor: '#b8f5d9',
          wickDownColor: '#ffb3bc'
        };
    base.lastValueVisible = true;
    base.priceLineVisible = true;
    return base;
  }

  function normalizeCandles(candles){
    var out = [];
    for(var i=0;i<candles.length;i++){
      var c = candles[i];
      var t = c.time;
      if(typeof t === 'string' && _selectedInterval !== '1d'){
        var dt = new Date(t);
        if(!isNaN(dt.getTime())) t = Math.floor(dt.getTime()/1000);
      }
      out.push({ time: t, open: c.open, high: c.high, low: c.low, close: c.close });
    }
    return out;
  }

  function focusLatest(candles){
    if(!_chart || !candles || !candles.length) return;
    var n = candles.length;
    var k = Math.min(140, Math.max(60, n - 1));
    _chart.timeScale().setVisibleLogicalRange({ from: n - 1 - k, to: n - 1 + 2 });
    _chart.timeScale().scrollToRealTime();
  }

  function startLivePolling(){
    stopLivePolling();
    _liveTimer = setInterval(function(){
      if(!_selectedSymbol) return;
      fetchJSON('/api/markets/candles/last?symbol='+encodeURIComponent(_selectedSymbol)+'&interval='+encodeURIComponent(_selectedInterval)).then(function(data){
        if(!data || data.error || !_series || !data.candles || !data.candles.length) return;
        var arr = normalizeCandles(data.candles);
        for(var i=0;i<arr.length;i++){
          var c = arr[i];
          if(_lastCandleTime == null || c.time >= _lastCandleTime){
            _series.update(c);
            _lastCandleTime = c.time;
          }
        }
      });
    }, 6000);
  }

  function stopLivePolling(){
    if(_liveTimer){
      clearInterval(_liveTimer);
      _liveTimer = null;
    }
  }

  function loadCandles(symbol){
    _selectedSymbol = symbol;
    _lastCandleTime = null;
    var titleEl = document.getElementById('mktmChartTitle');
    fetchJSON('/api/markets/candles?symbol='+encodeURIComponent(symbol)+'&period='+encodeURIComponent(_selectedPeriod)+'&interval='+encodeURIComponent(_selectedInterval)+'&source=auto').then(function(data){
      if(!data || data.error || !data.candles || !data.candles.length){
        if(titleEl){
          titleEl.textContent = symbol + (data && data.error === 'ibkr_disconnected' ? ' (TWS / IBKR off)' : ' (no data)');
        }
        return;
      }
      if(!ensureChart() || !_series) return;
      _series.applyOptions(seriesOptionsForSymbol(symbol));
      if(titleEl) titleEl.textContent = (data.name || symbol);
      var candles = normalizeCandles(data.candles);
      _series.setData(candles);
      if(candles.length) _lastCandleTime = candles[candles.length-1].time;
      focusLatest(candles);
      startLivePolling();
    });
  }

  function render(){
    var grid = document.getElementById('mktmGrid');
    if(!grid) return;
    var instruments = marketData.instruments || [];
    if(!instruments.length){
      grid.innerHTML = '<div class="empty-state" style="grid-column:1/-1">Waiting for market data...</div>';
      return;
    }

    var groups = {FX:[], Rates:[], Crypto:[], Equities:[], Commodities:[]};
    for(var i=0;i<instruments.length;i++){
      var m = instruments[i];
      var cls = m.asset_class || 'Other';
      if(!groups[cls]) groups[cls] = [];
      groups[cls].push(m);
    }

    var html = '';
    var order = ['FX','Crypto','Rates','Equities','Commodities'];
    for(var g=0;g<order.length;g++){
      var gName = order[g];
      var items = groups[gName] || [];
      if(!items.length) continue;
      html += '<div class="mktm-section"><div class="mktm-section-head">'+gName+'</div>';
      for(var j=0;j<items.length;j++){
        var m = items[j];
        var chgCls = m.change_pct > 0.001 ? 'up' : m.change_pct < -0.001 ? 'down' : 'flat';
        var chgStr = (m.change_pct >= 0 ? '+' : '') + (m.change_pct||0).toFixed(2) + '%';
        var decimals = m.price > 100 ? 2 : m.price > 10 ? 3 : 4;
        var sparkSvg = renderSparkline(m.history || []);
        var sym = m.symbol || '';
        var sel = sym === _selectedSymbol ? ' mktm-row-selected' : '';
        html +=
          '<div class="mktm-row'+sel+'" data-symbol="'+escHtml(sym)+'" title="Click for chart">'+
            '<div class="inst">'+escHtml(m.name||m.symbol)+'</div>'+
            '<div class="price">'+(m.price||0).toFixed(decimals)+'</div>'+
            '<div class="chg '+chgCls+'">'+chgStr+'</div>'+
            '<div class="spark">'+sparkSvg+'</div>'+
          '</div>';
      }
      html += '</div>';
    }
    grid.innerHTML = html;

    var rows = grid.querySelectorAll('.mktm-row');
    for(var i=0;i<rows.length;i++){
      (function(row){
        row.addEventListener('click', function(){
          var sym = row.getAttribute('data-symbol');
          if(!sym) return;
          var all = grid.querySelectorAll('.mktm-row');
          for(var j=0;j<all.length;j++) all[j].classList.remove('mktm-row-selected');
          row.classList.add('mktm-row-selected');
          loadCandles(sym);
        });
      })(rows[i]);
    }

    loadCandles(_selectedSymbol);
  }

  function renderSparkline(hist){
    if(!hist || hist.length < 2) return '';
    var w=60, h=20, pad=1;
    var min=Infinity, max=-Infinity;
    for(var i=0;i<hist.length;i++){
      if(hist[i]<min) min=hist[i];
      if(hist[i]>max) max=hist[i];
    }
    var range = max-min || 1;
    var step = (w-2*pad)/(hist.length-1);
    var d = '';
    for(var j=0;j<hist.length;j++){
      var x = pad + j*step;
      var y = h - pad - (hist[j]-min)/range*(h-2*pad);
      d += (j===0?'M':'L')+x.toFixed(1)+','+y.toFixed(1);
    }
    var color = hist[hist.length-1] >= hist[0] ? 'var(--green)' : 'var(--red)';
    return '<svg viewBox="0 0 '+w+' '+h+'"><path d="'+d+'" fill="none" stroke="'+color+'" stroke-width="1"/></svg>';
  }

  function onData(type){ if(type==='markets') render(); }

  function destroy(){
    stopLivePolling();
    if(_chart){
      try{ _chart.remove(); }catch(e){}
      _chart = null;
      _series = null;
    }
  }

  registerScreen('mktm', {init:init, render:render, onData:onData, destroy:destroy});
})();
