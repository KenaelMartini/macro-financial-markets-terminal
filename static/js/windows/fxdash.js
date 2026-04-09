/* ── FXDASH screen: FX dashboard + chandeliers (OHLC) ─────── */

(function(){
  var el;
  var _fxChart = null;
  var _fxSeries = null;
  var _fxResizeBound = false;
  var _fxInterval = '1d';
  var _fxPeriod = '5y';
  var _fxLastTime = null;
  var _fxLiveTimer = null;

  var FX_CHART_CHOICES = [
    {label:'EUR/USD', sym:'EURUSD=X'},
    {label:'GBP/USD', sym:'GBPUSD=X'},
    {label:'USD/JPY', sym:'JPY=X'},
    {label:'AUD/USD', sym:'AUDUSD=X'},
    {label:'USD/CAD', sym:'CAD=X'},
    {label:'USD/CHF', sym:'CHF=X'},
    {label:'NZD/USD', sym:'NZDUSD=X'},
    {label:'EUR/JPY', sym:'EURJPY=X'},
    {label:'GBP/JPY', sym:'GBPJPY=X'},
  ];

  function init(container){
    el = container;
    var selOpts = '';
    for(var i=0;i<FX_CHART_CHOICES.length;i++){
      var c = FX_CHART_CHOICES[i];
      selOpts += '<option value="'+c.sym+'">'+escHtml(c.label)+'</option>';
    }
    el.innerHTML =
      '<div class="fxdash-wrap">'+
        '<div class="fxdash-chart-bar">'+
          '<div class="fxdash-panel-head">FX — chandeliers japonais (OHLC 1j)</div>'+
          '<div class="fxdash-chart-toolbar">'+
            '<label>Paire</label><select id="fxChartPairSel">'+selOpts+'</select>'+
            '<label>TF</label><select id="fxChartTfSel"><option value="1h">H1</option><option value="4h">H4</option><option value="8h">H8</option><option value="1d" selected>D1</option></select>'+
            '<span class="fxdash-chart-hint">Données IBKR uniquement (TWS connecté). Choisis une paire pour afficher les bougies.</span>'+
          '</div>'+
          '<div id="fxChartEl" class="fxdash-chart-el"></div>'+
        '</div>'+
        '<div class="fxdash-legend">'+
          '<strong>How to read this screen</strong>'+
          '<ul>'+
            '<li><em>Chart</em> — Japanese candlesticks (daily OHLC) for the selected pair.</li>'+
            '<li><em>Scorecard</em> — Spot vs % change, wire headline counts, last CB NLP tone when available.</li>'+
            '<li><em>Cross matrix</em> — Daily % change of row CCY vs column CCY (green = row outperformed).</li>'+
            '<li><em>CB tone</em> — Latest publication title + tone from stored CB events.</li>'+
            '<li><em>News flow</em> — Mentions in the live RSS set.</li>'+
          '</ul>'+
        '</div>'+
        '<div class="fxdash-layout">'+
          '<div class="fxdash-panel"><div class="fxdash-panel-head">Currency scorecard</div><div class="fxdash-panel-body" id="fxScoreBody"></div></div>'+
          '<div class="fxdash-panel"><div class="fxdash-panel-head">FX cross matrix (% change today)</div><div class="fxdash-panel-body" id="fxMatrixBody"></div></div>'+
          '<div class="fxdash-panel"><div class="fxdash-panel-head">CB tone by bank</div><div class="fxdash-panel-body" id="fxCBBody"></div></div>'+
          '<div class="fxdash-panel"><div class="fxdash-panel-head">Headline flow by currency</div><div class="fxdash-panel-body" id="fxNewsBody"></div></div>'+
        '</div>'+
      '</div>';

    document.getElementById('fxChartPairSel').addEventListener('change', loadFxCandlesForSelection);
    document.getElementById('fxChartTfSel').addEventListener('change', function(e){
      _fxInterval = e.target.value || '1d';
      _fxPeriod = _fxInterval === '1d' ? '5y' : '1y';
      loadFxCandlesForSelection();
    });
    if(!_fxResizeBound){
      _fxResizeBound = true;
      window.addEventListener('resize', function(){
        var b = document.getElementById('fxChartEl');
        if(_fxChart && b) _fxChart.applyOptions({ width: Math.max(b.clientWidth, 400) });
      });
    }
  }

  function loadFxCandlesForSelection(){
    var sel = document.getElementById('fxChartPairSel');
    if(!sel) return;
    loadFxCandles(sel.value);
  }

  function ensureFxChart(){
    if(typeof LightweightCharts === 'undefined'){
      var b = document.getElementById('fxChartEl');
      if(b) b.innerHTML = '<div class="empty-state" style="padding:16px">Librairie graphique indisponible (CDN).</div>';
      return false;
    }
    var box = document.getElementById('fxChartEl');
    if(!box) return false;
    if(_fxChart) return true;
    var stub = box.querySelector('.empty-state');
    if(stub) box.removeChild(stub);
    var defs = window.terminalChartDefaults;
    var opts = defs && defs.createChartOptions
      ? defs.createChartOptions(Math.max(box.clientWidth, 400), 260)
      : {
          layout: { backgroundColor: '#060a10', textColor: '#8a9bb0' },
          grid: { vertLines: { color: '#1c2a3a' }, horzLines: { color: '#1c2a3a' } },
          width: Math.max(box.clientWidth, 400),
          height: 260
        };
    _fxChart = LightweightCharts.createChart(box, opts);
    _fxSeries = _fxChart.addCandlestickSeries(seriesOptionsForFx());
    return true;
  }

  function seriesOptionsForFx(){
    var defs = window.terminalChartDefaults;
    var symbol = (document.getElementById('fxChartPairSel') || {}).value || 'EURUSD=X';
    var out = defs && defs.candlestickSeriesOptions
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
    out.lastValueVisible = true;
    out.priceLineVisible = true;
    return out;
  }

  function normalizeFxCandles(candles){
    var out = [];
    for(var i=0;i<candles.length;i++){
      var c = candles[i];
      var t = c.time;
      if(typeof t === 'string' && _fxInterval !== '1d'){
        var dt = new Date(t);
        if(!isNaN(dt.getTime())) t = Math.floor(dt.getTime()/1000);
      }
      out.push({ time: t, open: c.open, high: c.high, low: c.low, close: c.close });
    }
    return out;
  }

  function focusFxLatest(candles){
    if(!_fxChart || !candles || !candles.length) return;
    var n = candles.length;
    var k = Math.min(140, Math.max(60, n - 1));
    _fxChart.timeScale().setVisibleLogicalRange({ from: n - 1 - k, to: n - 1 + 2 });
    _fxChart.timeScale().scrollToRealTime();
  }

  function stopFxLive(){
    if(_fxLiveTimer){
      clearInterval(_fxLiveTimer);
      _fxLiveTimer = null;
    }
  }

  function startFxLive(symbol){
    stopFxLive();
    _fxLiveTimer = setInterval(function(){
      fetchJSON('/api/markets/candles/last?symbol='+encodeURIComponent(symbol)+'&interval='+encodeURIComponent(_fxInterval)).then(function(data){
        if(!data || data.error || !_fxSeries || !data.candles || !data.candles.length) return;
        var arr = normalizeFxCandles(data.candles);
        for(var i=0;i<arr.length;i++){
          var c = arr[i];
          if(_fxLastTime == null || c.time >= _fxLastTime){
            _fxSeries.update(c);
            _fxLastTime = c.time;
          }
        }
      });
    }, 6000);
  }

  function loadFxCandles(symbol){
    var box = document.getElementById('fxChartEl');
    if(!box) return;
    _fxLastTime = null;
    fetchJSON('/api/markets/candles?symbol='+encodeURIComponent(symbol)+'&period='+encodeURIComponent(_fxPeriod)+'&interval='+encodeURIComponent(_fxInterval)+'&source=auto').then(function(data){
      if(!data || data.error || !data.candles || !data.candles.length){
        if(_fxSeries) _fxSeries.setData([]);
        var head = document.querySelector('.fxdash-chart-hint');
        if(head && data && data.error === 'ibkr_disconnected'){
          head.textContent = 'IBKR déconnecté — lance TWS / Gateway (paper) pour les bougies.';
        }
        return;
      }
      if(!ensureFxChart() || !_fxSeries) return;
      _fxSeries.applyOptions(seriesOptionsForFx());
      var headOk = document.querySelector('.fxdash-chart-hint');
      if(headOk) headOk.textContent = 'Données IBKR uniquement (TWS connecté). Choisis une paire pour afficher les bougies.';
      _fxChart.applyOptions({ width: Math.max(box.clientWidth, 400) });
      var candles = normalizeFxCandles(data.candles);
      _fxSeries.setData(candles);
      if(candles.length) _fxLastTime = candles[candles.length-1].time;
      focusFxLatest(candles);
      startFxLive(symbol);
    });
  }

  function render(){
    loadFxCandlesForSelection();
    renderScorecard();
    renderMatrix();
    renderCBTone();
    renderNewsFlow();
  }

  function renderScorecard(){
    var body = document.getElementById('fxScoreBody');
    if(!body) return;
    var instruments = marketData.instruments || [];
    var fxInst = instruments.filter(function(m){return m.asset_class === 'FX';});

    var html = '<div class="fx-score-row" style="font-weight:700;color:var(--text-dim)"><span>CCY</span><span>Rate</span><span>Chg%</span><span>News</span><span>CB Tone</span></div>';
    for(var i=0;i<FX8.length;i++){
      var ccy = FX8[i];
      var inst = null;
      for(var j=0;j<fxInst.length;j++){
        if(fxInst[j].symbol && fxInst[j].symbol.indexOf(ccy)!==-1){ inst=fxInst[j]; break; }
      }
      var newsCount = countNewsByCcy(ccy);
      var cbTone = getCBTone(ccy);
      var rate = inst ? (inst.price||0).toFixed(4) : '--';
      var chg = inst ? ((inst.change_pct>=0?'+':'')+(inst.change_pct||0).toFixed(2)+'%') : '--';
      var chgCls = inst && inst.change_pct > 0 ? 'up' : inst && inst.change_pct < 0 ? 'down' : 'flat';

      html += '<div class="fx-score-row">'+
        '<span class="ccy-label">'+ccy+'</span>'+
        '<span style="color:var(--text)">'+rate+'</span>'+
        '<span class="chg '+chgCls+'">'+chg+'</span>'+
        '<span style="color:var(--text-sec)">'+newsCount+'</span>'+
        '<span class="tone-badge '+(cbTone?cbTone.toLowerCase():'')+'">'+( cbTone || '--')+'</span>'+
      '</div>';
    }
    body.innerHTML = html;
  }

  function countNewsByCcy(ccy){
    var count = 0;
    for(var i=0;i<newsArticles.length;i++){
      var hay = ((newsArticles[i].title||'')+(newsArticles[i].summary||'')).toUpperCase();
      if(hay.indexOf(ccy)!==-1) count++;
    }
    return count;
  }

  function getCBTone(ccy){
    var bankForCcy = null;
    for(var bid in BANK_CCYS){
      if(BANK_CCYS[bid] === ccy){ bankForCcy = bid; break; }
    }
    if(!bankForCcy) return '';
    var evts = [];
    for(var key in cbEvents){
      var normKey = EVENT_BANK_MAP[key] || key;
      if(normKey === bankForCcy) evts = evts.concat(cbEvents[key]);
    }
    if(!evts.length) return '';
    var latest = evts[evts.length-1];
    if(latest && latest.analysis) return latest.analysis.tone || latest.analysis.tone_abs_no_context || '';
    return '';
  }

  function renderMatrix(){
    var body = document.getElementById('fxMatrixBody');
    if(!body) return;
    var instruments = marketData.instruments || [];
    if(!instruments.length){
      body.innerHTML = '<div class="empty-state">Waiting for FX data</div>';
      return;
    }
    var n = FX8.length + 1;
    var html = '<div class="fx-matrix" style="grid-template-columns:repeat('+n+',1fr)">';
    html += '<div class="cell header"></div>';
    for(var i=0;i<FX8.length;i++) html += '<div class="cell header">'+FX8[i]+'</div>';
    for(var r=0;r<FX8.length;r++){
      html += '<div class="cell header">'+FX8[r]+'</div>';
      for(var c=0;c<FX8.length;c++){
        if(r===c){ html += '<div class="cell" style="background:var(--bg-surface)">-</div>'; continue; }
        var val = getFXChange(FX8[r], FX8[c]);
        var cls2 = val > 0 ? 'positive' : val < 0 ? 'negative' : '';
        html += '<div class="cell '+cls2+'">'+(val!==null ? (val>=0?'+':'')+val.toFixed(2)+'%' : '--')+'</div>';
      }
    }
    html += '</div>';
    body.innerHTML = html;
  }

  function getFXChange(base, quote){
    var instruments = marketData.instruments || [];
    for(var i=0;i<instruments.length;i++){
      var sym = (instruments[i].symbol||'').toUpperCase();
      if(sym.indexOf(base)!==-1 && sym.indexOf(quote)!==-1){
        return instruments[i].change_pct || 0;
      }
    }
    return null;
  }

  function renderCBTone(){
    var body = document.getElementById('fxCBBody');
    if(!body) return;
    var html = '';
    for(var i=0;i<BANK_ORDER.length;i++){
      var bid = BANK_ORDER[i];
      var st = cbStates[bid] || {};
      var flag = BANK_FLAGS[bid] || '';
      var label = BANK_LABELS[bid];
      var wl = st.wire_lexicon;
      var tone = (wl && wl.tone) ? wl.tone : '';
      if(!tone){
        var evts = [];
        for(var key in cbEvents){
          var normKey = EVENT_BANK_MAP[key] || key;
          if(normKey === bid) evts = evts.concat(cbEvents[key]);
        }
        var latest = evts.length ? evts[evts.length-1] : null;
        tone = latest && latest.analysis ? (latest.analysis.tone||latest.analysis.tone_abs_no_context||'') : '';
      }
      var title = st.last_title || '--';
      var toneCls = (tone||'').toLowerCase().replace(/\s+/g,'');
      html += '<div class="mini-row">'+
        '<span class="label">'+flag+' '+label+'</span>'+
        '<span class="value" style="flex:1;font-size:9px;font-weight:400;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--text-sec);margin:0 8px">'+escHtml(title.substring(0,40))+'</span>'+
        (tone ? '<span class="tone-badge '+toneCls+'" title="Lexique sur titre du poll (pas le marché)">'+escHtml(tone)+'</span>' : '<span style="font-size:9px;color:var(--text-dim)">--</span>')+
      '</div>';
    }
    body.innerHTML = html;
  }

  function renderNewsFlow(){
    var body = document.getElementById('fxNewsBody');
    if(!body) return;
    var html = '';
    for(var i=0;i<FX8.length;i++){
      var ccy = FX8[i];
      var count = countNewsByCcy(ccy);
      var barWidth = Math.min(count, 100);
      html += '<div class="mini-row">'+
        '<span class="label" style="min-width:36px;font-weight:700">'+ccy+'</span>'+
        '<span style="flex:1;display:flex;align-items:center;gap:6px">'+
          '<span style="height:8px;width:'+barWidth+'%;background:var(--accent);border-radius:4px;display:inline-block"></span>'+
          '<span style="font-size:9px;color:var(--text-dim)">'+count+' articles</span>'+
        '</span>'+
      '</div>';
    }
    body.innerHTML = html;
  }

  function onData(type){
    if(type==='markets'){ renderScorecard(); renderMatrix(); loadFxCandlesForSelection(); }
    if(type==='cb'){ renderCBTone(); }
    if(type==='news'){ renderNewsFlow(); renderScorecard(); }
  }

  function destroy(){
    stopFxLive();
    if(_fxChart){
      try{ _fxChart.remove(); }catch(e){}
      _fxChart = null;
      _fxSeries = null;
    }
  }

  registerScreen('fxdash', {init:init, render:render, onData:onData, destroy:destroy});
})();
