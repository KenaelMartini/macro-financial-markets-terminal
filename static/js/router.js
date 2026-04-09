/* ── Screen router / manager ──────────────────────────────── */

var SCREENS = {};
var _currentScreen = null;
var _screenEls = {};

function registerScreen(id, screenObj){
  SCREENS[id] = screenObj;
}

function buildNavTabs(){
  var el = document.getElementById('navTabs');
  var html = '';
  for(var i=0;i<SCREEN_DEFS.length;i++){
    var s = SCREEN_DEFS[i];
    html += '<div class="nav-tab" data-screen="'+s.id+'" title="'+s.desc+' ('+s.key+')">'+
      s.label+'<span class="tab-key">'+s.key+'</span></div>';
  }
  el.innerHTML = html;
  el.addEventListener('click', function(e){
    var tab = e.target.closest('.nav-tab');
    if(tab) switchScreen(tab.getAttribute('data-screen'));
  });
}

function switchScreen(id){
  if(!SCREENS[id]) return;
  var tabs = document.querySelectorAll('.nav-tab');
  for(var i=0;i<tabs.length;i++){
    tabs[i].classList.toggle('active', tabs[i].getAttribute('data-screen')===id);
  }
  if(_currentScreen && SCREENS[_currentScreen] && SCREENS[_currentScreen].destroy){
    SCREENS[_currentScreen].destroy();
  }
  for(var sid in _screenEls){
    _screenEls[sid].classList.remove('active');
  }
  if(!_screenEls[id]){
    var div = document.createElement('div');
    div.className = 'screen';
    div.id = 'screen-'+id;
    document.getElementById('screenContainer').appendChild(div);
    _screenEls[id] = div;
    if(SCREENS[id].init) SCREENS[id].init(div);
  }
  _screenEls[id].classList.add('active');
  _currentScreen = id;
  if(SCREENS[id].render) SCREENS[id].render();
}

function notifyScreenData(type, payload){
  if(_currentScreen && SCREENS[_currentScreen] && SCREENS[_currentScreen].onData){
    SCREENS[_currentScreen].onData(type, payload);
  }
}

function initRouter(){
  buildNavTabs();

  var cmdInput = document.getElementById('cmdInput');
  cmdInput.addEventListener('keydown', function(e){
    if(e.key === 'Enter'){
      var val = cmdInput.value.trim().toLowerCase();
      for(var i=0;i<SCREEN_DEFS.length;i++){
        if(SCREEN_DEFS[i].id === val || SCREEN_DEFS[i].label.toLowerCase() === val){
          switchScreen(SCREEN_DEFS[i].id);
          cmdInput.value = '';
          cmdInput.blur();
          return;
        }
      }
      cmdInput.value = '';
    }
    if(e.key === 'Escape'){
      cmdInput.value = '';
      cmdInput.blur();
    }
  });

  document.addEventListener('keydown', function(e){
    if(e.target === cmdInput) return;
    if(e.key === '/' || e.key === '`'){
      e.preventDefault();
      cmdInput.focus();
      return;
    }
    var fMap = {
      'F1':'home','F2':'wire','F3':'cenb','F4':'ecfc','F5':'mktm',
      'F6':'fxdash','F7':'signals','F8':'pricein','F9':'intel','F10':'alert','F11':'risk','F12':'ylds'
    };
    if(fMap[e.key]){
      e.preventDefault();
      switchScreen(fMap[e.key]);
    }
  });

  switchScreen('home');
}
