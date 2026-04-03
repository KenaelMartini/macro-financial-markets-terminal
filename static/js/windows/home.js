/* ── HOME screen: overview dashboard ──────────────────────── */

(function(){
  var el;

  function init(container){
    el = container;
    el.innerHTML =
      '<div class="home-grid">'+
        '<div class="home-tile" id="homeCB">'+
          '<div class="home-tile-head"><span>Central Banks</span><span class="tile-badge" id="homeCBBadge">--</span></div>'+
          '<div class="home-tile-body" id="homeCBBody"></div>'+
        '</div>'+
        '<div class="home-tile" id="homeNews">'+
          '<div class="home-tile-head"><span>Breaking News</span><span class="tile-badge" id="homeNewsBadge">--</span></div>'+
          '<div class="home-tile-body" id="homeNewsBody"></div>'+
        '</div>'+
        '<div class="home-tile" id="homeCal">'+
          '<div class="home-tile-head"><span>Next Events</span><span class="tile-badge" id="homeCalBadge">--</span></div>'+
          '<div class="home-tile-body" id="homeCalBody"></div>'+
        '</div>'+
        '<div class="home-tile" id="homeMkt">'+
          '<div class="home-tile-head"><span>Markets</span><span class="tile-badge" id="homeMktBadge">--</span></div>'+
          '<div class="home-tile-body" id="homeMktBody"></div>'+
        '</div>'+
        '<div class="home-tile" id="homeFX">'+
          '<div class="home-tile-head"><span>FX Snapshot</span></div>'+
          '<div class="home-tile-body" id="homeFXBody"></div>'+
        '</div>'+
        '<div class="home-tile" id="homeAlerts">'+
          '<div class="home-tile-head"><span>Alerts & Signals</span><span class="tile-badge" id="homeAlertBadge">--</span></div>'+
          '<div class="home-tile-body" id="homeAlertBody"></div>'+
        '</div>'+
      '</div>';
  }

  function render(){
    renderCBTile();
    renderNewsTile();
    renderCalTile();
    renderMktTile();
    renderFXTile();
    renderAlertTile();
  }

  function renderCBTile(){
    var body = document.getElementById('homeCBBody');
    if(!body) return;
    var html = '';
    for(var i=0;i<BANK_ORDER.length;i++){
      var bid = BANK_ORDER[i];
      var st = cbStates[bid];
      var flag = BANK_FLAGS[bid] || '';
      var label = BANK_LABELS[bid] || bid.toUpperCase();
      var title = st ? (st.last_title||'').substring(0,50) : '--';
      var age = st && st.last_run_ts ? Math.floor((Date.now()/1000 - st.last_run_ts)/60)+'m ago' : '--';
      var cls = st && st.last_run_ts && (Date.now()/1000 - st.last_run_ts) < 7200 ? 'up' : 'flat';
      html += '<div class="mini-row"><span class="label">'+flag+' '+label+'</span><span class="value" style="font-size:9px;flex:1;margin:0 8px;color:var(--text-sec);overflow:hidden;text-overflow:ellipsis;white-space:nowrap">'+escHtml(title)+'</span><span class="chg '+cls+'">'+age+'</span></div>';
    }
    body.innerHTML = html;
    var badge = document.getElementById('homeCBBadge');
    if(badge) badge.textContent = Object.keys(cbStates).length+' banks';
  }

  function renderNewsTile(){
    var body = document.getElementById('homeNewsBody');
    if(!body) return;
    var top = newsArticles.slice(0,8);
    var html = '';
    for(var i=0;i<top.length;i++){
      var a = top[i];
      var src = shortSource(a.source);
      var t = timeAgo(a.published_utc);
      html += '<div class="mini-row"><span class="label" style="color:var(--cyan);min-width:60px">'+src+'</span><span class="value" style="font-size:10px;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-weight:400">'+escHtml(a.title||'')+'</span><span class="chg flat">'+t+'</span></div>';
    }
    body.innerHTML = html || '<div class="empty-state">Waiting for news...</div>';
    var badge = document.getElementById('homeNewsBadge');
    if(badge) badge.textContent = newsArticles.length+' articles';
  }

  function renderCalTile(){
    var body = document.getElementById('homeCalBody');
    if(!body) return;
    var now = new Date().toISOString();
    var upcoming = calendarEvents.filter(function(e){return (e.date||'') >= now && e.impact !== 'Low';});
    upcoming.sort(function(a,b){return (a.date||'').localeCompare(b.date||'');});
    var top = upcoming.slice(0,8);
    var html = '';
    for(var i=0;i<top.length;i++){
      var ev = top[i];
      var stars = IMPACT_STARS[ev.impact] || '';
      var ccy = (ev.country||'').toUpperCase();
      var t = formatCalTime(ev.date);
      var day = formatCalDay(ev.date);
      html += '<div class="mini-row"><span class="label" style="min-width:36px;color:'+(ev.impact==='High'?'var(--red)':'var(--yellow)')+'">'+stars+'</span><span class="label" style="min-width:30px">'+ccy+'</span><span class="value" style="flex:1;font-weight:400;font-size:10px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">'+escHtml(ev.title||'')+'</span><span class="chg flat">'+day+' '+t+'</span></div>';
    }
    body.innerHTML = html || '<div class="empty-state">No upcoming events</div>';
    var badge = document.getElementById('homeCalBadge');
    if(badge) badge.textContent = calendarEvents.length+' events';
  }

  function renderMktTile(){
    var body = document.getElementById('homeMktBody');
    if(!body) return;
    var instruments = marketData.instruments || [];
    if(!instruments.length){
      body.innerHTML = '<div class="empty-state">Waiting for market data...</div>';
      return;
    }
    var show = instruments.slice(0,10);
    var html = '';
    for(var i=0;i<show.length;i++){
      var m = show[i];
      var chgCls = m.change_pct > 0 ? 'up' : m.change_pct < 0 ? 'down' : 'flat';
      var chgStr = (m.change_pct >= 0 ? '+' : '') + (m.change_pct||0).toFixed(2) + '%';
      html += '<div class="mini-row"><span class="label">'+escHtml(m.symbol||'')+'</span><span class="value">'+(m.price||0).toFixed(m.price>100?2:4)+'</span><span class="chg '+chgCls+'">'+chgStr+'</span></div>';
    }
    body.innerHTML = html;
    var badge = document.getElementById('homeMktBadge');
    if(badge) badge.textContent = instruments.length+' instruments';
  }

  function renderFXTile(){
    var body = document.getElementById('homeFXBody');
    if(!body) return;
    var instruments = marketData.instruments || [];
    var fxInst = instruments.filter(function(m){return m.asset_class === 'FX';});
    if(!fxInst.length){
      body.innerHTML = '<div class="empty-state">Waiting for FX data...</div>';
      return;
    }
    var html = '';
    for(var i=0;i<fxInst.length;i++){
      var m = fxInst[i];
      var chgCls = m.change_pct > 0 ? 'up' : m.change_pct < 0 ? 'down' : 'flat';
      var chgStr = (m.change_pct >= 0 ? '+' : '') + (m.change_pct||0).toFixed(2) + '%';
      html += '<div class="mini-row"><span class="label">'+escHtml(m.name||m.symbol)+'</span><span class="value">'+(m.price||0).toFixed(4)+'</span><span class="chg '+chgCls+'">'+chgStr+'</span></div>';
    }
    body.innerHTML = html;
  }

  function renderAlertTile(){
    var body = document.getElementById('homeAlertBody');
    if(!body) return;
    if(!alertsList.length){
      body.innerHTML = '<div class="empty-state">No active alerts. Configure in ALERT screen.</div>';
      return;
    }
    var html = '';
    var recent = alertsList.slice(0,6);
    for(var i=0;i<recent.length;i++){
      var a = recent[i];
      html += '<div class="mini-row"><span class="label" style="color:var(--accent)">'+escHtml(a.type||'ALERT')+'</span><span class="value" style="flex:1;font-weight:400;font-size:10px">'+escHtml(a.message||'')+'</span></div>';
    }
    body.innerHTML = html;
    var badge = document.getElementById('homeAlertBadge');
    if(badge) badge.textContent = alertsList.length+' alerts';
  }

  function onData(type){
    if(type==='cb') renderCBTile();
    if(type==='news') renderNewsTile();
    if(type==='calendar') renderCalTile();
    if(type==='markets') { renderMktTile(); renderFXTile(); }
  }

  registerScreen('home', {init:init, render:render, onData:onData});
})();
