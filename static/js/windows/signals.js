/* ── SIGNALS screen: macro signals + explanations ─────────── */

(function(){
  var el;
  var _signals = [];

  function init(container){
    el = container;
    el.innerHTML =
      '<div class="signals-wrap">'+
        '<p class="signals-legend">Direction = LONG/SHORT the pair from <strong>hawk/dove keyword</strong> hits in headlines that mention each currency. Conviction scales with the gap between base and quote scores (not a model forecast).</p>'+
        '<div class="panel-head"><span>Macro signals</span><span class="badge" id="sigCount">--</span></div>'+
        '<div class="signals-body" id="signalsBody"></div>'+
      '</div>';
    loadSignals();
  }

  function loadSignals(){
    fetchJSON('/api/signals').then(function(data){
      if(data && data.signals) _signals = data.signals;
      renderSignals();
    });
  }

  function renderSignals(){
    var body = document.getElementById('signalsBody');
    if(!body) return;
    if(!_signals.length){
      body.innerHTML = '<div class="empty-state">No signals yet — need recent news mentioning G10 currencies.</div>';
      return;
    }
    var html = '<div class="signal-row signal-head">'+
      '<span class="pair">PAIR</span>'+
      '<span class="dir">DIR</span>'+
      '<span class="conv">CONV</span>'+
      '<span class="why-dir">Why direction?</span>'+
      '<span class="why-conv">Why conviction?</span>'+
      '<span class="driver">Driver</span>'+
    '</div>';
    for(var i=0;i<_signals.length;i++){
      var s = _signals[i];
      var dirCls = (s.direction||'').toLowerCase() === 'long' ? 'long' : 'short';
      var conv = (s.conviction || 0);
      var convPct = Math.min(conv * 100, 100);
      var de = s.direction_explanation || '';
      var ce = s.conviction_explanation || '';
      html +=
        '<div class="signal-row">'+
          '<span class="pair">'+escHtml(s.pair||'--')+'</span>'+
          '<span class="dir '+dirCls+'">'+(s.direction||'--').toUpperCase()+'</span>'+
          '<span class="conv-cell"><span style="font-size:10px;color:var(--text-sec)">'+(conv*100).toFixed(0)+'%</span>'+
            '<div class="conviction-bar"><div class="conviction-fill" style="width:'+convPct+'%"></div></div></span>'+
          '<span class="why-dir" title="'+escHtml(de)+'">'+escHtml(de.substring(0,72))+(de.length>72?'…':'')+'</span>'+
          '<span class="why-conv" title="'+escHtml(ce)+'">'+escHtml(ce.substring(0,72))+(ce.length>72?'…':'')+'</span>'+
          '<span class="driver">'+escHtml(s.driver||'--')+'</span>'+
        '</div>';
    }
    body.innerHTML = html;
    var badge = document.getElementById('sigCount');
    if(badge) badge.textContent = _signals.length+' signals';
  }

  function render(){ loadSignals(); }
  function onData(type){ if(type==='signals') loadSignals(); }

  registerScreen('signals', {init:init, render:render, onData:onData});
})();
