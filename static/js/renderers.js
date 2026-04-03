/* ── UI rendering functions ───────────────────────────────── */

function renderBankPills(){
  var el = document.getElementById('bankPills');
  var html = '';
  for(var i=0;i<BANK_ORDER.length;i++){
    var bid = BANK_ORDER[i];
    var st = cbStates[bid];
    var cls = '';
    if(st){
      var lastTs = st.last_run_ts;
      if(lastTs){
        var age = (Date.now()/1000) - lastTs;
        cls = age < 7200 ? 'ok' : age < 86400 ? 'warn' : 'err';
      } else { cls = 'warn'; }
    }
    html += '<div class="bank-pill '+cls+'"><span class="dot"></span>'+(BANK_LABELS[bid]||bid.toUpperCase())+'</div>';
  }
  el.innerHTML = html;
}


function renderCBPanel(){
  var body = document.getElementById('cbBody');
  var allEvents = {};
  for(var rawKey in cbEvents){
    var normKey = EVENT_BANK_MAP[rawKey] || rawKey;
    if(!allEvents[normKey]) allEvents[normKey] = [];
    allEvents[normKey].push.apply(allEvents[normKey], cbEvents[rawKey]);
  }

  var html = '<div class="cb-section-label">Bank Status & Latest Events</div>';
  for(var i=0;i<BANK_ORDER.length;i++){
    var bid = BANK_ORDER[i];
    var st = cbStates[bid];
    var meta = { name: BANK_LABELS[bid], flag: BANK_FLAGS[bid], ccy: '' };
    if(st){ meta.name = st.bank_name || meta.name; meta.ccy = st.ccy || ''; }

    var lastTitle = st && st.last_link ? st.last_link.split('/').pop().substring(0,50) : '';
    var lastDate = (st && st.last_pubdate) || '';
    var lastTs = tsToReadable(st && st.last_run_ts);

    var bankEvents = (allEvents[bid] || []).slice(-3).reverse();
    var latestEvt = bankEvents[0];
    var tone = latestEvt && latestEvt.analysis ? (latestEvt.analysis.tone || latestEvt.analysis.tone_abs_no_context || '') : '';
    var scores = latestEvt && latestEvt.analysis ? (latestEvt.analysis.scores || []) : [];
    var evTitle = latestEvt ? (latestEvt.title || '') : '';

    var dov = scores[0] || 0;
    var neu = scores[1] || 0;
    var haw = scores[2] || 0;
    var total = dov+neu+haw || 1;

    var toneHtml = '';
    if(tone){
      toneHtml =
        '<div class="cb-card-tone">'+
          '<span class="tone-badge '+tone.toLowerCase()+'">'+tone+'</span>'+
          '<div class="tone-bar">'+
            '<div class="seg-d" style="width:'+(dov/total*100).toFixed(0)+'%"></div>'+
            '<div class="seg-n" style="width:'+(neu/total*100).toFixed(0)+'%"></div>'+
            '<div class="seg-h" style="width:'+(haw/total*100).toFixed(0)+'%"></div>'+
          '</div>'+
        '</div>';
    }

    html +=
      '<div class="cb-card">'+
        '<div class="cb-card-head">'+
          '<div class="bank-label">'+
            '<span class="bank-flag">'+meta.flag+'</span>'+
            '<span class="bank-name">'+meta.name+'</span>'+
          '</div>'+
          '<span class="ccy">'+meta.ccy+'</span>'+
        '</div>'+
        '<div class="cb-card-meta">'+(lastDate ? '\u{1F4C5} '+lastDate : '')+(lastTs ? ' \u2014 polled '+lastTs : '')+'</div>'+
        (st && st.last_link ? '<div class="cb-card-meta"><a href="'+st.last_link+'" target="_blank" rel="noopener">'+lastTitle+'</a></div>' : '')+
        toneHtml+
        (evTitle ? '<div class="cb-event-title">\u25B8 '+evTitle+'</div>' : '')+
      '</div>';
  }
  body.innerHTML = html;
  document.getElementById('cbCount').textContent = Object.keys(cbStates).length + ' banks';
}


function renderNews(){
  var body = document.getElementById('newsBody');
  if(!newsArticles.length){
    body.innerHTML = '<div class="empty-state">No articles loaded. Waiting for news collector...</div>';
    return;
  }
  var html = '';
  for(var i=0;i<newsArticles.length;i++){
    var art = newsArticles[i];
    var t = timeAgo(art.published_utc);
    var src = shortSource(art.source);
    var title = art.title || '(no title)';
    var url = art.url || '#';
    var summary = (art.summary && art.summary !== title) ? art.summary : '';
    html +=
      '<div class="news-item">'+
        '<div class="news-time">'+t+'</div>'+
        '<div class="news-content">'+
          '<div class="news-source">'+src+'</div>'+
          '<div class="news-title"><a href="'+url+'" target="_blank" rel="noopener">'+escHtml(title)+'</a></div>'+
          (summary ? '<div class="news-summary">'+escHtml(summary)+'</div>' : '')+
        '</div>'+
      '</div>';
  }
  body.innerHTML = html;
  document.getElementById('newsCount').textContent = newsArticles.length + ' articles';
}


function renderTicker(){
  var track = document.getElementById('tickerTrack');
  var headlines = newsArticles.slice(0,40);
  if(!headlines.length){
    track.innerHTML = '<span class="item">Waiting for data...</span>';
    return;
  }
  var html = '';
  for(var i=0;i<headlines.length;i++){
    var art = headlines[i];
    var src = shortSource(art.source);
    html += '<span class="item"><span class="src">'+src+'</span>'+escHtml(art.title||'')+'</span>';
  }
  track.innerHTML = html + html;
}


function renderCalendar(){
  var body = document.getElementById('calBody');
  if(!calendarEvents.length){
    body.innerHTML = '<div class="empty-state">No calendar data. Waiting for calendar refresh...</div>';
    return;
  }
  var sorted = calendarEvents.slice().sort(function(a,b){
    var da = (a.date||''), db = (b.date||'');
    if(da !== db) return da.localeCompare(db);
    return impactRank(b.impact) - impactRank(a.impact);
  });

  var html = '';
  var lastDateLabel = '';
  for(var i=0;i<sorted.length;i++){
    var ev = sorted[i];
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
    var evTime = formatCalTime(ev.date);
    html +=
      '<div class="cal-item">'+
        '<div class="cal-time">'+evTime+'</div>'+
        '<div class="cal-impact '+impactClass(imp)+'">'+stars+'</div>'+
        '<div class="cal-ccy '+ccyClass+'">'+ccy+'</div>'+
        '<div class="cal-event" title="'+escHtml(title)+'">'+escHtml(title)+'</div>'+
        '<div class="cal-values">'+
          '<span class="val">'+(forecast ? 'F:'+forecast : '')+'</span>'+
          '<span class="val">'+(previous ? 'P:'+previous : '')+'</span>'+
        '</div>'+
      '</div>';
  }
  body.innerHTML = html;
  document.getElementById('calCount').textContent = sorted.length + ' events';
}
