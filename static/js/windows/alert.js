/* ── ALERT screen: alert system ───────────────────────────── */

(function(){
  var el;

  function init(container){
    el = container;
    el.innerHTML =
      '<div class="alert-layout">'+
        '<div class="alert-panel">'+
          '<div class="alert-panel-head">Active Alerts</div>'+
          '<div class="alert-panel-body" id="alertListBody"></div>'+
        '</div>'+
        '<div class="alert-panel">'+
          '<div class="alert-panel-head">Configure Alert</div>'+
          '<div class="alert-panel-body">'+
            '<div class="alert-config-form">'+
              '<label>Alert Type</label>'+
              '<select id="alertType">'+
                '<option value="cb_new">CB New Publication</option>'+
                '<option value="cal_high">High-Impact Event (countdown)</option>'+
                '<option value="news_keyword">News Keyword Match</option>'+
                '<option value="market_move">Market Move Threshold</option>'+
              '</select>'+
              '<label>Bank / Currency</label>'+
              '<select id="alertBank">'+
                '<option value="">Any</option>'+
                '<option value="fed">FED</option><option value="ecb">ECB</option>'+
                '<option value="boe">BOE</option><option value="boj">BOJ</option>'+
                '<option value="boc">BOC</option><option value="rba">RBA</option>'+
                '<option value="rbnz">RBNZ</option><option value="snb">SNB</option>'+
              '</select>'+
              '<label>Keyword / Threshold</label>'+
              '<input type="text" id="alertValue" placeholder="e.g. rate cut, 0.5%">'+
              '<button id="alertAdd">Add Alert</button>'+
            '</div>'+
            '<div class="alert-panel-head" style="margin-top:1px">Alert History</div>'+
            '<div id="alertHistoryBody" style="flex:1;overflow-y:auto;padding:0"></div>'+
          '</div>'+
        '</div>'+
      '</div>';

    document.getElementById('alertAdd').addEventListener('click', addAlert);
    loadAlerts();
  }

  function loadAlerts(){
    fetchJSON('/api/alerts').then(function(data){
      if(data){
        alertsList = data.alerts || [];
        renderAlerts();
      }
    });
  }

  function addAlert(){
    var type = document.getElementById('alertType').value;
    var bank = document.getElementById('alertBank').value;
    var value = document.getElementById('alertValue').value;
    fetch(API_BASE+'/api/alerts', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({type:type, bank:bank, value:value})
    }).then(function(r){return r.json();}).then(function(data){
      if(data && data.alerts) alertsList = data.alerts;
      document.getElementById('alertValue').value = '';
      renderAlerts();
    });
  }

  function renderAlerts(){
    var body = document.getElementById('alertListBody');
    if(!body) return;
    if(!alertsList.length){
      body.innerHTML = '<div class="empty-state">No active alerts.<br>Configure alerts using the panel on the right.</div>';
      return;
    }
    var html = '';
    for(var i=0;i<alertsList.length;i++){
      var a = alertsList[i];
      var triggered = a.triggered ? ' triggered' : '';
      html += '<div class="alert-item'+triggered+'">'+
        '<div class="alert-title">'+escHtml(a.type||'ALERT')+' '+(a.bank ? '('+a.bank.toUpperCase()+')' : '')+'</div>'+
        '<div class="alert-meta">'+escHtml(a.value || a.message || '--')+' | Created: '+(a.created||'--')+'</div>'+
      '</div>';
    }
    body.innerHTML = html;
  }

  function render(){ loadAlerts(); }
  function onData(type){
    if(type==='alert') loadAlerts();
  }

  registerScreen('alert', {init:init, render:render, onData:onData});
})();
