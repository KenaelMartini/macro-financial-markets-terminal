/* ── Main application: data fetching, WebSocket, init ─────── */

setInterval(updateClock, 1000);
updateClock();

async function refreshAll(){
  var results = await Promise.all([
    fetchJSON('/api/cb-states'),
    fetchJSON('/api/news?limit=1500'),
    fetchJSON('/api/calendar'),
    fetchJSON('/api/cb-events'),
    fetchJSON('/api/markets'),
  ]);
  var states=results[0], news=results[1], cal=results[2], events=results[3], mkt=results[4];

  if(states){
    cbStates = states;
    renderBankPills();
    notifyScreenData('cb', states);
  }
  if(news){
    newsArticles = news.articles || [];
    renderTicker();
    document.getElementById('statusArticles').textContent = '\u25C6 '+news.total+' articles (LIVE)';
    notifyScreenData('news', newsArticles);
  }
  if(cal){
    calendarEvents = cal;
    document.getElementById('statusCal').textContent = '\u25C6 '+cal.length+' cal events';
    notifyScreenData('calendar', cal);
  }
  if(events){
    cbEvents = events;
    var total = 0; for(var k in events) total += events[k].length;
    document.getElementById('statusEvents').textContent = '\u25C6 '+total+' CB events';
  }
  if(mkt){
    marketData = mkt;
    var instCount = (mkt.instruments||[]).length;
    document.getElementById('statusMarkets').textContent = '\u25C6 '+instCount+' instruments';
    notifyScreenData('markets', mkt);
  }
  var now = new Date();
  document.getElementById('lastRefresh').textContent =
    'Last refresh: '+String(now.getHours()).padStart(2,'0')+':'+String(now.getMinutes()).padStart(2,'0')+':'+String(now.getSeconds()).padStart(2,'0');
}

function connectWS(){
  var proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
  var qs = '';
  var k = localStorage.getItem('TERMINAL_API_KEY');
  if(k) qs = '?api_key='+encodeURIComponent(k);
  wsConn = new WebSocket(proto+'//'+location.host+'/ws'+qs);
  wsConn.onopen = function(){
    document.getElementById('connIndicator').className = 'indicator connected';
    document.getElementById('connLabel').textContent = 'Live';
    document.getElementById('liveDot').style.display = '';
  };
  wsConn.onmessage = function(evt){
    try{
      var data = JSON.parse(evt.data);
      if(data.cb_states){
        cbStates = data.cb_states;
        renderBankPills();
        notifyScreenData('cb', cbStates);
      }
      if(data.market_data){
        marketData = data.market_data;
        notifyScreenData('markets', marketData);
      }
      if(data.alerts){
        alertsList = data.alerts;
        notifyScreenData('alert', alertsList);
      }
    } catch(e){}
  };
  wsConn.onclose = function(){
    document.getElementById('connIndicator').className = 'indicator disconnected';
    document.getElementById('connLabel').textContent = 'Reconnecting...';
    document.getElementById('liveDot').style.display = 'none';
    setTimeout(connectWS, 5000);
  };
  wsConn.onerror = function(){ wsConn.close(); };
}

(async function main(){
  initRouter();
  await refreshAll();
  connectWS();
  setInterval(refreshAll, REFRESH_MS);
})();
