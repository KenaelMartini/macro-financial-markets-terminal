/* ── YLDS: courbes / spreads FRED + proxy Fed funds ───────── */

(function(){
  var el;

  function init(container){
    el = container;
    el.innerHTML =
      '<div class="yields-head">'+
        '<span class="yields-title">YIELDS</span>'+
        '<span class="yields-sub" id="yieldsAsOf">—</span>'+
      '</div>'+
      '<div class="yields-grid" id="yieldsGrid"></div>'+
      '<div class="yields-fed" id="yieldsFed">—</div>';
  }

  function renderBlock(title, data){
    if(!data || data.error){
      var hint = (data && data.hint) ? escHtml(data.hint) : 'Configurez FRED_API_KEY pour les séries Treasury.';
      return '<div class="yields-card"><h3>'+escHtml(title)+'</h3><p class="yields-err">'+hint+'</p></div>';
    }
    var rows = '';
    var inst = data.instruments || [];
    for(var i=0;i<inst.length;i++){
      var it = inst[i];
      var y = it.yield_pct;
      rows += '<tr><td>'+escHtml(it.tenor)+'</td><td>'+(y!=null? String(y) : '—')+'</td><td class="dim">'+escHtml(it.fred_id||'')+'</td></tr>';
    }
    var sp = data.spreads || {};
    var s2 = sp['2s10s_bp'];
    var s5 = sp['5s30s_bp'];
    rows += '<tr class="yields-spread"><td>2s10s (bp)</td><td>'+(s2!=null? String(s2) : '—')+'</td><td></td></tr>';
    rows += '<tr class="yields-spread"><td>5s30s (bp)</td><td>'+(s5!=null? String(s5) : '—')+'</td><td></td></tr>';
    return '<div class="yields-card"><h3>'+escHtml(title)+'</h3><table class="yields-table">'+rows+'</table></div>';
  }

  async function load(){
    var g = document.getElementById('yieldsGrid');
    var fedEl = document.getElementById('yieldsFed');
    var asOf = document.getElementById('yieldsAsOf');
    if(!g) return;
    var curve = await fetchJSON('/api/yields/curve');
    var ff = await fetchJSON('/api/yields/fedfunds-implied');
    if(asOf && curve && curve.as_of_utc) asOf.textContent = curve.as_of_utc.substring(0,19)+'Z';
    g.innerHTML = renderBlock('US Treasury (FRED)', curve);
    if(fedEl && ff){
      var m = ff.method || '—';
      var v = ff.implied_policy_rate_pct;
      fedEl.innerHTML = '<strong>Fed funds proxy</strong> — '+escHtml(m)+
        (v!=null ? ' — <code>'+escHtml(String(v))+'%</code>' : '')+
        '<div class="dim" style="margin-top:6px">'+escHtml(ff.future_formula_note||'')+'</div>';
    }
  }

  function render(){ load(); }

  registerScreen('ylds', {init:init, render:render});
})();
