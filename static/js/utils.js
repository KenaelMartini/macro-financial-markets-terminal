/* ── Helper / utility functions ───────────────────────────── */

function updateClock(){
  var now = new Date();
  var hh = String(now.getUTCHours()).padStart(2,'0');
  var mm = String(now.getUTCMinutes()).padStart(2,'0');
  var ss = String(now.getUTCSeconds()).padStart(2,'0');
  document.getElementById('clock').textContent = hh+':'+mm+':'+ss;
  var days = ['SUN','MON','TUE','WED','THU','FRI','SAT'];
  var months = ['JAN','FEB','MAR','APR','MAY','JUN','JUL','AUG','SEP','OCT','NOV','DEC'];
  document.getElementById('dateDisp').textContent =
    days[now.getUTCDay()]+' '+now.getUTCDate()+' '+months[now.getUTCMonth()]+' '+now.getUTCFullYear()+' UTC';
}

function timeAgo(isoStr){
  if(!isoStr) return '--';
  try{
    var d = new Date(isoStr);
    return String(d.getUTCHours()).padStart(2,'0')+':'+String(d.getUTCMinutes()).padStart(2,'0');
  } catch(e){ return '--'; }
}

function shortSource(src){
  if(!src) return 'NEWS';
  var s = src.toLowerCase();
  if(s.includes('reuters')) return 'REUTERS';
  if(s.includes('bloomberg')) return 'BLOOMBERG';
  if(s.includes('ft.com') || s.includes('financial times')) return 'FT';
  if(s.includes('wsj') || s.includes('wall street')) return 'WSJ';
  if(s.includes('cnbc')) return 'CNBC';
  if(s.includes('bbc')) return 'BBC';
  if(s.includes('investing')) return 'INVESTING';
  if(s.includes('ecb') || s.includes('european central')) return 'ECB';
  if(s.includes('bank of england') || s.includes('boe')) return 'BOE';
  if(s.includes('fed') || s.includes('federal')) return 'FED';
  if(s.includes('imf')) return 'IMF';
  if(s.includes('world bank')) return 'WORLD BANK';
  if(s.includes('rba')) return 'RBA';
  if(s.includes('boj') || s.includes('bank of japan')) return 'BOJ';
  if(s.includes('marketwatch')) return 'MKTWATCH';
  if(s.includes('google')) return 'GNEWS';
  if(src.length > 20) return src.substring(0,18).toUpperCase();
  return src.toUpperCase();
}

function tsToReadable(ts){
  if(!ts) return '';
  try{
    var d = new Date(ts * 1000);
    if(isNaN(d.getTime())) return '';
    return d.toISOString().replace('T',' ').substring(0,19)+' UTC';
  } catch(e){ return ''; }
}

function impactClass(imp){
  if(!imp) return 'low';
  var s = imp.toLowerCase();
  if(s === 'high') return 'high';
  if(s === 'medium') return 'medium';
  if(s === 'holiday') return 'holiday';
  return 'low';
}

function impactRank(imp){
  if(imp==='High') return 3;
  if(imp==='Medium') return 2;
  if(imp==='Holiday') return 1;
  return 0;
}

function escHtml(s){
  var d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}

function formatCalDay(iso){
  if(!iso) return '';
  try{
    var d = new Date(iso);
    var days = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'];
    var months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    return days[d.getUTCDay()]+' '+d.getUTCDate()+' '+months[d.getUTCMonth()];
  } catch(e){ return ''; }
}

function formatCalTime(iso){
  if(!iso) return '';
  try{
    var d = new Date(iso);
    var h = String(d.getUTCHours()).padStart(2,'0');
    var m = String(d.getUTCMinutes()).padStart(2,'0');
    return h+':'+m;
  } catch(e){ return ''; }
}

async function fetchJSON(url){
  try{
    var headers = {};
    var apiKey = localStorage.getItem('TERMINAL_API_KEY');
    if(apiKey) headers['X-API-Key'] = apiKey;
    var au = localStorage.getItem('TERMINAL_AUTH_USER');
    var ap = localStorage.getItem('TERMINAL_AUTH_PASSWORD');
    if(au != null && ap != null && String(au)+String(ap) !== ''){
      headers['Authorization'] = 'Basic '+btoa(String(au)+':'+String(ap));
    }
    var r = await fetch(API_BASE + url, {headers:headers, credentials:'same-origin'});
    if(!r.ok) return null;
    return await r.json();
  } catch(e){ return null; }
}
