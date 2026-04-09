/* ── PRICEIN: narrative vs price + searchable agreement ───── */

(function(){
  var el;
  var _priceinData = null;
  var _filter = '';

  function init(container){
    el = container;
    el.innerHTML =
      '<div class="pricein-layout">'+
        '<div class="pricein-intro" id="priceinLegend"></div>'+
        '<div class="pricein-toolbar">'+
          '<label>Filter pairs</label>'+
          '<input type="text" id="priceinSearch" placeholder="e.g. EUR or USD/JPY" />'+
        '</div>'+
        '<div class="pricein-panels">'+
          '<div class="pricein-panel">'+
            '<div class="pricein-panel-head">Agreement score (news bias vs daily % move)</div>'+
            '<div class="pricein-panel-body" id="priceinMatrix"></div>'+
          '</div>'+
          '<div class="pricein-panel">'+
            '<div class="pricein-panel-head">Residual themes / watchlist</div>'+
            '<div class="pricein-panel-body" id="priceinResidual"></div>'+
          '</div>'+
        '</div>'+
      '</div>';
    document.getElementById('priceinSearch').addEventListener('input', function(e){
      _filter = e.target.value.trim().toLowerCase();
      renderMatrix();
      renderResidual();
    });
    loadPriceIn();
  }

  function loadPriceIn(){
    fetchJSON('/api/pricein').then(function(data){
      if(data) _priceinData = data;
      renderPriceIn();
    });
  }

  function renderPriceIn(){
    var leg = document.getElementById('priceinLegend');
    if(leg){
      leg.innerHTML = '<p>'+escHtml(_priceinData && _priceinData.legend ? _priceinData.legend : '')+'</p>';
    }
    renderMatrix();
    renderResidual();
  }

  function pairMatches(key){
    if(!_filter) return true;
    return key.toLowerCase().indexOf(_filter) !== -1;
  }

  function renderMatrix(){
    var body = document.getElementById('priceinMatrix');
    if(!body) return;
    if(!_priceinData || !_priceinData.agreement){
      body.innerHTML = '<div class="empty-state">Load market data and news, then refresh. Agreement compares signal direction with today’s FX % change.</div>';
      return;
    }
    var agr = _priceinData.agreement;
    var html = '<div class="mini-row" style="font-weight:700;color:var(--text-dim);font-size:9px"><span class="label">Pair</span><span>Score (−1…+1)</span><span>Read</span></div>';
    var any = false;
    for(var key in agr){
      if(!pairMatches(key)) continue;
      any = true;
      var val = agr[key];
      var cls = val > 0.25 ? 'up' : val < -0.25 ? 'down' : 'flat';
      var read = val > 0.25 ? 'Move aligned with bias' : val < -0.25 ? 'Move contra bias' : 'Flat / weak';
      var px = _priceinData.latest_prices && _priceinData.latest_prices[key] != null
        ? ('Px '+Number(_priceinData.latest_prices[key]).toFixed(5))
        : '';
      html += '<div class="mini-row"><span class="label">'+escHtml(key)+'</span><span class="chg '+cls+'">'+(val>=0?'+':'')+val.toFixed(2)+'</span><span style="font-size:9px;color:var(--text-dim)">'+read+'</span></div>';
      if(px){
        html += '<div class="mini-row" style="margin-top:-6px;margin-bottom:6px"><span></span><span></span><span style="font-size:9px;color:var(--text-dim)">'+px+'</span></div>';
      }
    }
    body.innerHTML = any ? html : '<div class="empty-state">No pairs match filter</div>';
  }

  function renderResidual(){
    var body = document.getElementById('priceinResidual');
    if(!body) return;
    if(!_priceinData || !_priceinData.residuals){
      body.innerHTML = '<div class="empty-state">No residual rows yet.</div>';
      return;
    }
    var res = _priceinData.residuals;
    var html = '';
    for(var i=0;i<res.length;i++){
      var r = res[i];
      if(_filter){
        var hay = ((r.pair||'')+' '+(r.theme||'')+' '+(r.description||'')).toLowerCase();
        if(hay.indexOf(_filter) === -1) continue;
      }
      html += '<div class="mini-row"><span class="label" style="color:var(--accent)">'+escHtml(r.pair||'')+'</span>'+
        '<span class="value" style="flex:1;font-weight:400;font-size:10px;color:var(--text-sec)">'+escHtml(r.description||'')+'</span>'+
        '<span class="chg '+(r.impact>0?'up':'down')+'">'+(r.impact>0?'+':'')+(r.impact!=null?r.impact.toFixed(2):'')+'</span></div>';
      if(r.argument){
        html += '<div class="mini-row"><span></span><span class="value" style="flex:1;font-weight:400;font-size:9px;color:var(--text-dim)">'+escHtml(r.argument)+'</span><span></span></div>';
      }
    }
    body.innerHTML = html || '<div class="empty-state">Nothing matches filter — clear the box to see all themes.</div>';
  }

  function render(){ loadPriceIn(); }
  function onData(type){ if(type==='markets') loadPriceIn(); }

  registerScreen('pricein', {init:init, render:render, onData:onData});
})();
