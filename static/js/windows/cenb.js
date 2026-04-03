/* ── CENB screen: central bank deep-dive + all-CB overview ─── */

(function(){
  var el;
  var _selectedBank = 'fed';
  var _bankHistory = {};
  var _sidebarBound = false;

  function init(container){
    el = container;
    el.innerHTML =
      '<div class="cenb-layout">'+
        '<div class="cenb-sidebar" id="cenbSidebar"></div>'+
        '<div class="cenb-main">'+
          '<div class="cenb-overview" id="cenbOverview"></div>'+
          '<div class="cenb-heatmap-section" id="cenbHeatmap"></div>'+
          '<div class="cenb-header" id="cenbHeader"></div>'+
          '<div class="cenb-content" id="cenbContent"></div>'+
        '</div>'+
      '</div>';
    bindSidebarOnce();
    renderSidebar();
    renderAllBanksOverview();
    loadBankHistory(_selectedBank);
  }

  function bindSidebarOnce(){
    if(_sidebarBound) return;
    _sidebarBound = true;
    document.getElementById('cenbSidebar').addEventListener('click', function(e){
      var item = e.target.closest('.cenb-bank-item');
      if(item){
        _selectedBank = item.getAttribute('data-bank');
        renderSidebar();
        loadBankHistory(_selectedBank);
      }
    });
  }

  function eventsForBank(bid){
    var merged = [];
    for(var key in cbEvents){
      var normKey = EVENT_BANK_MAP[key] || key;
      if(normKey === bid){
        merged = merged.concat(cbEvents[key]);
      }
    }
    return merged;
  }

  function netHawkFromEvent(ev){
    if(!ev || !ev.analysis || !ev.analysis.scores || ev.analysis.scores.length < 3) return null;
    var d = ev.analysis.scores[0] || 0;
    var n = ev.analysis.scores[1] || 0;
    var h = ev.analysis.scores[2] || 0;
    var t = d + n + h;
    if(t <= 0) return null;
    return (h - d) / t;
  }

  function renderAllBanksOverview(){
    var box = document.getElementById('cenbOverview');
    if(!box) return;
    var html = '<div class="cenb-section-title">All central banks — lexicon on latest poll title</div>';
    html += '<p class="cenb-hint" style="margin-bottom:8px">Chaque colonne vient du <strong>dernier titre</strong> récupéré sur le site/RSS (mots-clés type « rate cut », « inflation », etc.). Ce n’est <strong>pas</strong> le ton implicite du marché (courbes de taux, FX, probas de hike).</p>';
    html += '<table class="cenb-all-table"><thead><tr><th>Bank</th><th>Net</th><th>Dov%</th><th>Neu%</th><th>Haw%</th><th>Latest poll title</th></tr></thead><tbody>';
    for(var i=0;i<BANK_ORDER.length;i++){
      var bid = BANK_ORDER[i];
      var st = cbStates[bid] || {};
      var wl = st.wire_lexicon;
      var d = '—', n = '—', h = '—', nhStr = '—', nh = null, title = '—';
      if(wl && wl.triplet_dnh){
        d = String(wl.triplet_dnh[0]); n = String(wl.triplet_dnh[1]); h = String(wl.triplet_dnh[2]);
        nh = wl.net_hawk;
        nhStr = nh != null ? (nh >= 0 ? '+' : '') + nh.toFixed(2) : '—';
        title = (st.last_title || '').substring(0,48);
      } else {
        var evts = eventsForBank(bid);
        var hist = _bankHistory[bid];
        var pool = (hist && hist.length) ? hist : evts;
        var last = pool && pool.length ? pool[pool.length-1] : null;
        var scores = last && last.analysis ? (last.analysis.scores || []) : [];
        if(scores.length >= 3){
          d = scores[0] != null ? scores[0].toFixed(0) : '—';
          n = scores[1] != null ? scores[1].toFixed(0) : '—';
          h = scores[2] != null ? scores[2].toFixed(0) : '—';
          nh = netHawkFromEvent(last);
          nhStr = nh != null ? (nh >= 0 ? '+' : '') + nh.toFixed(2) : '—';
        }
        title = last ? (last.title || '').substring(0,48) : (st.last_title||'').substring(0,48) || '—';
      }
      html += '<tr data-bank="'+bid+'">'+
        '<td>'+(BANK_FLAGS[bid]||'')+' '+escHtml(BANK_LABELS[bid]||bid)+'</td>'+
        '<td class="'+(nh!=null && nh>0.1?'up':nh!=null && nh<-0.1?'down':'flat')+'">'+nhStr+'</td>'+
        '<td>'+d+'</td><td>'+n+'</td><td>'+h+'</td>'+
        '<td style="font-size:9px;color:var(--text-dim)">'+escHtml(title)+'</td>'+
      '</tr>';
    }
    html += '</tbody></table>';
    html += '<p class="cenb-hint">Les entrées « démo » dans les fichiers history JSONL sont filtrées. Cliquez une ligne pour le détail.</p>';
    box.innerHTML = html;
    renderHeatmap();
    var rows = box.querySelectorAll('tbody tr');
    for(var r=0;r<rows.length;r++){
      (function(row){
        row.style.cursor = 'pointer';
        row.addEventListener('click', function(){
          _selectedBank = row.getAttribute('data-bank');
          renderSidebar();
          loadBankHistory(_selectedBank);
        });
      })(rows[r]);
    }
  }

  function renderHeatmap(){
    var box = document.getElementById('cenbHeatmap');
    if(!box) return;
    var html = '<div class="cenb-section-title">Desk heatmap (tone · net hawk · shift · forward guidance)</div>';
    html += '<table class="cb-heatmap"><thead><tr><th>Bank</th><th>Tone</th><th>Net H</th><th>Shift Δ</th><th>Fwd guid.</th></tr></thead><tbody>';
    for(var i=0;i<BANK_ORDER.length;i++){
      var bid = BANK_ORDER[i];
      var st = cbStates[bid] || {};
      var wl = st.wire_lexicon || {};
      var ts = st.tone_shift || {};
      var dp = st.desk_preview || {};
      var tone = wl.tone ? String(wl.tone) : '—';
      var nh = wl.net_hawk;
      var nhStr = nh != null ? (nh >= 0 ? '+' : '') + nh.toFixed(2) : '—';
      var dlt = ts.delta_net_hawk;
      var dStr = dlt != null ? (dlt >= 0 ? '+' : '') + dlt.toFixed(2) : '—';
      var fg = dp.forward_guidance;
      var fgStr = fg != null ? fg.toFixed(2) : '—';
      var nhCls = nh!=null && nh>0.08?'hm-hawk':nh!=null && nh<-0.08?'hm-dove':'hm-flat';
      var dCls = dlt!=null && dlt>0.05?'hm-hawk':dlt!=null && dlt<-0.05?'hm-dove':'hm-flat';
      var fgCls = fg!=null && fg>0.2?'hm-hawk':fg!=null && fg<-0.2?'hm-dove':'hm-flat';
      html += '<tr data-bank="'+bid+'">'+
        '<td>'+(BANK_FLAGS[bid]||'')+' '+escHtml(BANK_LABELS[bid]||bid)+'</td>'+
        '<td class="hm-tone">'+escHtml(tone)+'</td>'+
        '<td class="'+nhCls+'">'+nhStr+'</td>'+
        '<td class="'+dCls+'">'+dStr+'</td>'+
        '<td class="'+fgCls+'">'+fgStr+'</td>'+
      '</tr>';
    }
    html += '</tbody></table>';
    html += '<p class="cenb-hint">Shift Δ = net hawk vs moyenne SQLite (~30 derniers ticks). Fwd guid. = score mots-clés forward guidance.</p>';
    box.innerHTML = html;
    var hrows = box.querySelectorAll('tbody tr');
    for(var r=0;r<hrows.length;r++){
      (function(row){
        row.style.cursor = 'pointer';
        row.addEventListener('click', function(){
          _selectedBank = row.getAttribute('data-bank');
          renderSidebar();
          loadBankHistory(_selectedBank);
        });
      })(hrows[r]);
    }
  }

  function renderSidebar(){
    var sb = document.getElementById('cenbSidebar');
    if(!sb) return;
    var html = '';
    for(var i=0;i<BANK_ORDER.length;i++){
      var bid = BANK_ORDER[i];
      var st = cbStates[bid];
      var sel = bid === _selectedBank ? ' selected' : '';
      var flag = BANK_FLAGS[bid] || '';
      var name = st ? (st.bank_name||BANK_LABELS[bid]) : BANK_LABELS[bid];
      var ccy = BANK_CCYS[bid] || '';
      var statusDot = '';
      if(st && st.last_run_ts){
        var age = (Date.now()/1000) - st.last_run_ts;
        var dotColor = age < 7200 ? 'var(--green)' : age < 86400 ? 'var(--yellow)' : 'var(--red)';
        statusDot = '<span style="width:6px;height:6px;border-radius:50%;background:'+dotColor+';flex-shrink:0"></span>';
      }
      html += '<div class="cenb-bank-item'+sel+'" data-bank="'+bid+'">'+
        '<span class="flag">'+flag+'</span>'+
        '<div class="info"><div class="bname">'+name+'</div><div class="bccy">'+ccy+'</div></div>'+
        statusDot+
      '</div>';
    }
    sb.innerHTML = html;
  }

  function loadBankHistory(bid){
    fetchJSON('/api/cb/'+bid+'/history?limit=80').then(function(data){
      if(data) _bankHistory[bid] = data;
      renderDetail();
      renderAllBanksOverview();
    });
  }

  function renderHistogramBars(d, n, haw, subtitle){
    var mx = Math.max(d,n,haw,1);
    var html = '<div class="cenb-histo"><div class="cenb-histo-title">'+subtitle+'</div><div class="cenb-histo-bars">';
    var labs = [['Dovish', d, 'var(--green)'],['Neutral', n, 'var(--yellow)'],['Hawkish', haw, 'var(--red)']];
    for(var j=0;j<labs.length;j++){
      var lab = labs[j][0], val = labs[j][1], col = labs[j][2];
      var ht = Math.round((val/mx)*72);
      html += '<div class="cenb-bar-wrap"><div class="cenb-bar" style="height:'+ht+'px;background:'+col+'"></div><div class="cenb-bar-lab">'+lab+'</div><div class="cenb-bar-val">'+(typeof val==='number'?val.toFixed(0):val)+'</div></div>';
    }
    html += '</div></div>';
    return html;
  }

  function renderHistogram(events, bid){
    var st = cbStates[bid] || {};
    var wl = st.wire_lexicon;
    if(wl && wl.triplet_dnh){
      var t = wl.triplet_dnh;
      var kw = (wl.keywords && wl.keywords.length) ? '<div class="cenb-hint">Hits: '+escHtml(wl.keywords.slice(0,8).join(', '))+'</div>' : '';
      return renderHistogramBars(t[0], t[1], t[2], 'Live poll title — keyword mix (not OIS/FX)') + kw;
    }
    var last = null;
    for(var i=events.length-1;i>=0;i--){
      if(events[i].analysis && events[i].analysis.scores && events[i].analysis.scores.length >= 3){
        last = events[i];
        break;
      }
    }
    if(!last) return '<div class="cenb-hint">Pas encore d’historique NLP filtré — le histogramme utilisera le titre du poll dès qu’il est analysable.</div>';
    var s = last.analysis.scores;
    var d = Math.max(0, s[0]||0), n = Math.max(0, s[1]||0), h = Math.max(0, s[2]||0);
    return renderHistogramBars(d, n, h, 'Dernière entrée history (scores stockés)');
  }

  function renderDetail(){
    var bid = _selectedBank;
    var st = cbStates[bid] || {};
    var header = document.getElementById('cenbHeader');
    var content = document.getElementById('cenbContent');
    if(!header || !content) return;

    var flag = BANK_FLAGS[bid] || '';
    var name = st.bank_name || BANK_LABELS[bid] || bid.toUpperCase();
    var ccy = BANK_CCYS[bid] || '';
    var polled = st.last_run_ts ? tsToReadable(st.last_run_ts) : '--';
    var latency = st.latency_ms ? st.latency_ms+'ms' : '--';

    var disc = '';
    if(st.wire_lexicon && st.wire_lexicon.disclaimer){
      disc = '<div class="cenb-hint" style="margin-top:6px">'+escHtml(st.wire_lexicon.disclaimer)+'</div>';
    }
    header.innerHTML =
      '<h2>'+flag+' '+name+'</h2>'+
      '<div class="meta">'+ccy+' | Last polled: '+polled+' | Latency: '+latency+'</div>'+
      (st.tone_unchanged ? '<div class="meta" style="color:var(--yellow)">Tone daily: inchangé (pas de nouvelle indication)</div>' : '')+
      '<div class="meta" style="margin-top:4px;color:var(--text)">Latest wire: '+escHtml(st.last_title||'--')+'</div>'+
      (st.last_link ? '<div class="meta"><a href="'+st.last_link+'" target="_blank" rel="noopener" style="color:var(--accent)">Open latest publication</a></div>' : '')+
      disc;

    var events = _bankHistory[bid] || [];
    var merged = eventsForBank(bid);
    if(!events.length) events = merged.slice();

    var html = '';

    html += '<div class="cenb-section">'+renderHistogram(events, bid)+'</div>';

    if(events.length){
      html += '<div class="cenb-section"><div class="cenb-section-title">Tone trend (net hawk)</div>';
      html += renderToneChart(events);
      html += '</div>';
    }

    html += '<div class="cenb-section"><div class="cenb-section-title">Historique stocké (démo filtrée — anciens scores NLP / GPT si présents)</div>';
    html += '<table class="cenb-nlp-table"><thead><tr><th>Date</th><th>Title</th><th>Dov</th><th>Neu</th><th>Haw</th><th>Net</th><th>Label</th></tr></thead><tbody>';
    if(!events.length){
      html += '<tr><td colspan="7" class="cenb-hint">Aucune ligne retenue après filtre — seul le bloc ci-dessus (poll live) compte pour la tonalité.</td></tr>';
    }
    for(var i=events.length-1;i>=0;i--){
      var ev = events[i];
      var dateStr = ev.timestamp || ev.ts || '';
      if(dateStr){ try{ dateStr = new Date(dateStr).toISOString().substring(0,16).replace('T',' '); }catch(e){} }
      var tone = ev.analysis ? (ev.analysis.tone || ev.analysis.tone_abs_no_context || '') : '';
      var scores = ev.analysis ? (ev.analysis.scores || []) : [];
      var d = scores.length ? (scores[0]||0).toFixed(0) : '—';
      var neu = scores.length > 1 ? (scores[1]||0).toFixed(0) : '—';
      var haw = scores.length > 2 ? (scores[2]||0).toFixed(0) : '—';
      var nh = netHawkFromEvent(ev);
      var nhStr = nh != null ? nh.toFixed(2) : '—';
      html += '<tr>'+
        '<td class="nlp-d">'+dateStr+'</td>'+
        '<td class="nlp-t">'+escHtml((ev.title||'').substring(0,56))+'</td>'+
        '<td>'+d+'</td><td>'+neu+'</td><td>'+haw+'</td>'+
        '<td class="'+(nh!=null && nh>0.05?'up':nh!=null && nh<-0.05?'down':'')+'">'+nhStr+'</td>'+
        '<td>'+(tone ? '<span class="tone-badge '+tone.toLowerCase()+'">'+tone+'</span>' : '—')+'</td>'+
      '</tr>';
    }
    html += '</tbody></table></div>';

    content.innerHTML = html;
  }

  function renderToneChart(events){
    var pts = [];
    for(var i=0;i<events.length;i++){
      var ev = events[i];
      if(ev.analysis && ev.analysis.scores && ev.analysis.scores.length >= 3){
        var dov = ev.analysis.scores[0] || 0;
        var haw = ev.analysis.scores[2] || 0;
        var total = dov + (ev.analysis.scores[1]||0) + haw || 1;
        pts.push({idx:i, score: (haw - dov) / total});
      }
    }
    if(pts.length < 2) return '<div class="cenb-hint">Not enough NLP data for trend line.</div>';

    var w = 400, h = 70, pad = 5;
    var xStep = (w - 2*pad) / (pts.length - 1);
    var yMid = h / 2;
    var yScale = (h - 2*pad) / 2;

    var pathD = '';
    for(var j=0;j<pts.length;j++){
      var x = pad + j * xStep;
      var y = yMid - pts[j].score * yScale;
      pathD += (j===0?'M':'L') + x.toFixed(1) + ',' + y.toFixed(1);
    }

    return '<div class="tone-chart"><svg viewBox="0 0 '+w+' '+h+'" preserveAspectRatio="none">'+
      '<line x1="'+pad+'" y1="'+yMid+'" x2="'+(w-pad)+'" y2="'+yMid+'" stroke="var(--border)" stroke-width="0.5"/>'+
      '<text x="2" y="12" fill="var(--red)" font-size="8">HAWK</text>'+
      '<text x="2" y="'+(h-4)+'" fill="var(--green)" font-size="8">DOVE</text>'+
      '<path d="'+pathD+'" fill="none" stroke="var(--accent)" stroke-width="1.5"/>'+
    '</svg></div>';
  }

  function render(){
    renderSidebar();
    renderAllBanksOverview();
    renderDetail();
  }
  function onData(type){
    if(type==='cb'){ renderSidebar(); renderAllBanksOverview(); renderDetail(); }
  }

  registerScreen('cenb', {init:init, render:render, onData:onData});
})();
