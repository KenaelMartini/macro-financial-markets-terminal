/* ── INTEL screen: AI intelligence reports ────────────────── */

(function(){
  var el;
  var _activeTab = 'brief';
  var _reports = {};

  function init(container){
    el = container;
    el.innerHTML =
      '<div class="intel-layout">'+
        '<div class="intel-tabs">'+
          '<div class="intel-tab active" data-tab="brief">Morning Brief</div>'+
          '<div class="intel-tab" data-tab="us">US</div>'+
          '<div class="intel-tab" data-tab="europe">Europe</div>'+
          '<div class="intel-tab" data-tab="asia">Asia</div>'+
          '<div class="intel-tab" data-tab="global">Global</div>'+
          '<div style="margin-left:auto"><button class="intel-generate" id="intelGenerate">Generate Report</button></div>'+
        '</div>'+
        '<div class="intel-body" id="intelBody"></div>'+
      '</div>';

    el.querySelector('.intel-tabs').addEventListener('click', function(e){
      var tab = e.target.closest('.intel-tab');
      if(tab){
        _activeTab = tab.getAttribute('data-tab');
        var tabs = el.querySelectorAll('.intel-tab');
        for(var i=0;i<tabs.length;i++) tabs[i].classList.toggle('active', tabs[i].getAttribute('data-tab')===_activeTab);
        renderBody();
      }
    });

    document.getElementById('intelGenerate').addEventListener('click', function(){
      generateReport();
    });

    loadBrief();
  }

  function loadBrief(){
    fetchJSON('/api/intel/brief').then(function(data){
      if(data){
        _reports = data;
        renderBody();
      }
    });
  }

  function generateReport(){
    var btn = document.getElementById('intelGenerate');
    btn.textContent = 'Generating...';
    btn.disabled = true;
    fetch(API_BASE+'/api/intel/generate', {method:'POST'}).then(function(r){return r.json();}).then(function(data){
      if(data) _reports = data;
      btn.textContent = 'Generate Report';
      btn.disabled = false;
      renderBody();
    }).catch(function(){
      btn.textContent = 'Generate Report';
      btn.disabled = false;
    });
  }

  function renderBody(){
    var body = document.getElementById('intelBody');
    if(!body) return;

    var content = _reports[_activeTab] || _reports.brief || null;
    if(!content){
      body.innerHTML = buildAutoBrief();
      return;
    }

    if(typeof content === 'string'){
      body.innerHTML = formatMarkdown(content);
    } else if(content.text){
      body.innerHTML = formatMarkdown(content.text);
    } else {
      body.innerHTML = '<pre style="white-space:pre-wrap;color:var(--text-sec)">'+JSON.stringify(content,null,2)+'</pre>';
    }
  }

  function buildAutoBrief(){
    var html = '<h3>Automated Morning Brief</h3>';
    html += '<p style="color:var(--text-dim)">Generated from live data at '+new Date().toUTCString()+'</p>';

    html += '<h3>Central Banks</h3>';
    for(var i=0;i<BANK_ORDER.length;i++){
      var bid = BANK_ORDER[i];
      var st = cbStates[bid];
      if(st && st.last_title){
        html += '<p><strong>'+BANK_FLAGS[bid]+' '+(st.bank_name||BANK_LABELS[bid])+'</strong>: '+escHtml(st.last_title)+'</p>';
      }
    }

    html += '<h3>Top Headlines</h3>';
    var top = newsArticles.slice(0,10);
    for(var j=0;j<top.length;j++){
      html += '<p style="font-size:11px">\u2022 <strong>'+shortSource(top[j].source)+'</strong>: '+escHtml(top[j].title)+'</p>';
    }

    var now = new Date().toISOString();
    var upcoming = calendarEvents.filter(function(e){return (e.date||'')>now && e.impact==='High';}).slice(0,5);
    if(upcoming.length){
      html += '<h3>Upcoming High-Impact Events</h3>';
      for(var k=0;k<upcoming.length;k++){
        var ev = upcoming[k];
        html += '<p style="font-size:11px">\u2022 '+(ev.country||'')+' '+escHtml(ev.title)+' ('+formatCalDay(ev.date)+' '+formatCalTime(ev.date)+' UTC)</p>';
      }
    }

    return html;
  }

  function formatMarkdown(text){
    return text
      .replace(/^### (.+)$/gm, '<h3>$1</h3>')
      .replace(/^## (.+)$/gm, '<h3 style="font-size:14px">$1</h3>')
      .replace(/^# (.+)$/gm, '<h3 style="font-size:16px">$1</h3>')
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/\n\n/g, '</p><p>')
      .replace(/\n/g, '<br>');
  }

  function render(){ loadBrief(); }

  registerScreen('intel', {init:init, render:render});
})();
