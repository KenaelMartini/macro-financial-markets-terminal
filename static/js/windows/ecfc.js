/* ── ECFC screen: enhanced economic calendar ─────────────── */

(function(){
  var el;
  var _filter = {impact:'', ccy:'', search:'', includePast:false};
  var _countdownInterval = null;

  function init(container){
    el = container;
    el.innerHTML =
      '<div class="ecfc-toolbar">'+
        '<label>Impact</label>'+
        '<select id="ecfcImpact"><option value="">All</option><option value="High">High</option><option value="Medium">Medium</option><option value="Low">Low</option><option value="Holiday">Holiday</option></select>'+
        '<label>Currency</label>'+
        '<select id="ecfcCcy"><option value="">All</option><option value="USD">USD</option><option value="EUR">EUR</option><option value="GBP">GBP</option><option value="JPY">JPY</option><option value="CAD">CAD</option><option value="AUD">AUD</option><option value="NZD">NZD</option><option value="CHF">CHF</option><option value="CNY">CNY</option></select>'+
        '<label>Search</label>'+
        '<input type="text" id="ecfcSearch" placeholder="keyword..." style="width:140px">'+
        '<label style="display:flex;align-items:center;gap:6px"><input type="checkbox" id="ecfcPastTog">Past</label>'+
        '<div class="ecfc-countdown">'+
          '<span class="next-label">NEXT:</span>'+
          '<span class="next-event" id="ecfcNextEvent">--</span>'+
          '<span class="next-time" id="ecfcNextTime">--</span>'+
        '</div>'+
      '</div>'+
      '<p class="ecfc-hint">La colonne <strong>A (actual)</strong> est complétée côté serveur (Investing.com et/ou Finnhub si <code>FINNHUB_API_KEY</code> est défini) quand le JSON ForexFactory ne contient pas le champ.</p>'+
      '<div class="ecfc-body" id="ecfcBody"></div>';

    document.getElementById('ecfcImpact').addEventListener('change', function(e){_filter.impact=e.target.value;renderCal();});
    document.getElementById('ecfcCcy').addEventListener('change', function(e){_filter.ccy=e.target.value.toUpperCase();renderCal();});
    document.getElementById('ecfcSearch').addEventListener('input', function(e){_filter.search=e.target.value.toLowerCase();renderCal();});
    document.getElementById('ecfcPastTog').addEventListener('change', function(e){_filter.includePast=!!e.target.checked;renderCal();});
    startCountdown();
  }

  function startCountdown(){
    if(_countdownInterval) clearInterval(_countdownInterval);
    _countdownInterval = setInterval(updateCountdown, 1000);
    updateCountdown();
  }

  function updateCountdown(){
    var now = new Date();
    var nowISO = now.toISOString();
    var next = null;
    for(var i=0;i<calendarEvents.length;i++){
      var ev = calendarEvents[i];
      if((ev.date||'') > nowISO && (ev.impact==='High' || ev.impact==='Medium')){
        if(!next || ev.date < next.date) next = ev;
      }
    }
    var elEvt = document.getElementById('ecfcNextEvent');
    var elTime = document.getElementById('ecfcNextTime');
    if(!elEvt || !elTime) return;
    if(!next){
      elEvt.textContent = 'No upcoming';
      elTime.textContent = '';
      return;
    }
    var diff = new Date(next.date) - now;
    if(diff < 0){ elTime.textContent = 'NOW'; }
    else{
      var h = Math.floor(diff/3600000);
      var m = Math.floor((diff%3600000)/60000);
      var s = Math.floor((diff%60000)/1000);
      elTime.textContent = (h>0?h+'h ':'')+(m>0?m+'m ':'')+ s+'s';
    }
    var base = (next.country||'').toUpperCase()+' '+(next.title||'').substring(0,36);
    if(next.forecast) base += ' | fc '+String(next.forecast).substring(0,12);
    elEvt.textContent = base;
  }

  function tokensMatch(hay, q){
    if(!q) return true;
    var parts = q.trim().toLowerCase().split(/\s+/).filter(Boolean);
    if(!parts.length) return true;
    for(var i=0;i<parts.length;i++){
      if(hay.indexOf(parts[i]) === -1) return false;
    }
    return true;
  }

  function filterEvents(){
    var nowISO = new Date().toISOString();
    return calendarEvents.filter(function(ev){
      if(_filter.impact && ev.impact !== _filter.impact) return false;
      if(_filter.ccy && (ev.country||'').toUpperCase() !== _filter.ccy) return false;
      if(!_filter.includePast && (ev.date||'') < nowISO) return false;
      if(_filter.search){
        var hay = ((ev.title||'')+' '+(ev.country||'')+' '+(ev.forecast||'')+' '+(ev.previous||'')+' '+(ev.actual||'')).toLowerCase();
        if(!tokensMatch(hay, _filter.search)) return false;
      }
      return true;
    });
  }

  function renderCal(){
    var body = document.getElementById('ecfcBody');
    if(!body) return;
    var filtered = filterEvents();
    filtered.sort(function(a,b){
      var da = (a.date||''), db = (b.date||'');
      if(da !== db) return da.localeCompare(db);
      return impactRank(b.impact) - impactRank(a.impact);
    });

    if(!filtered.length){
      body.innerHTML = '<div class="empty-state">No events matching filters</div>';
      return;
    }

    var now = new Date().toISOString();
    var html = '';
    var lastDateLabel = '';
    for(var i=0;i<filtered.length;i++){
      var ev = filtered[i];
      var dayLabel = formatCalDay(ev.date);
      if(dayLabel && dayLabel !== lastDateLabel){
        html += '<div class="cal-date-separator">'+dayLabel+'</div>';
        lastDateLabel = dayLabel;
      }
      var imp = ev.impact || 'Low';
      var stars = IMPACT_STARS[imp] || '\u2605';
      var ccy = (ev.country || '').toUpperCase();
      var ccyClass = ccy.toLowerCase();
      var title = ev.title || '';
      var forecast = ev.forecast || '';
      var previous = ev.previous || '';
      var actual = ev.actual || '';
      var evTime = formatCalTime(ev.date);
      var isPast = (ev.date||'') < now;
      var rowStyle = isPast ? 'opacity:.5' : '';

      html +=
        '<div class="cal-item" style="'+rowStyle+'">'+
          '<div class="cal-time">'+evTime+'</div>'+
          '<div class="cal-impact '+impactClass(imp)+'">'+stars+'</div>'+
          '<div class="cal-ccy '+ccyClass+'">'+ccy+'</div>'+
          '<div class="cal-event" title="'+escHtml(title)+'">'+escHtml(title)+'</div>'+
          '<div class="cal-values ecfc-fpa">'+
            '<span class="val">F: '+escHtml(forecast !== '' && forecast != null ? String(forecast) : '—')+'</span>'+
            '<span class="val">P: '+escHtml(previous !== '' && previous != null ? String(previous) : '—')+'</span>'+
            '<span class="val '+(actual ? 'actual-ok':'')+'">A: '+escHtml(actual !== '' && actual != null ? String(actual) : '—')+'</span>'+
          '</div>'+
        '</div>';
    }
    body.innerHTML = html;
  }

  function render(){ renderCal(); updateCountdown(); }
  function onData(type){ if(type==='calendar') renderCal(); }
  function destroy(){ if(_countdownInterval) clearInterval(_countdownInterval); _countdownInterval=null; }

  registerScreen('ecfc', {init:init, render:render, onData:onData, destroy:destroy});
})();
