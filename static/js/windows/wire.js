/* ── WIRE screen: full news wire with filters ────────────── */

(function(){
  var el;
  var _filter = {search:'', source:'', ccy:'', regexMode:false, bank:''};

  var WIRE_BANK_KW = {
    fed: ['fed','fomc','powell','federal reserve','treasury'],
    ecb: ['ecb','lagarde','eurozone','european central'],
    boe: ['boe','bank of england','bailey','sterling'],
    boj: ['boj','bank of japan','kuroda','ueda','yen'],
    boc: ['boc','bank of canada'],
    rba: ['rba','reserve bank of australia'],
    rbnz: ['rbnz','reserve bank of new zealand'],
    snb: ['snb','swiss national']
  };

  function stripHtml(s){
    if(!s) return '';
    var d = document.createElement('div');
    d.innerHTML = s;
    return (d.textContent || d.innerText || '').toLowerCase();
  }

  function searchHaystack(a){
    return (
      stripHtml(a.title) + ' ' +
      stripHtml(a.summary) + ' ' +
      (a.source || '').toLowerCase()
    );
  }

  function tokensMatch(hay, q){
    if(!q) return true;
    var parts = q.toLowerCase().trim().split(/\s+/).filter(Boolean);
    if(!parts.length) return true;
    for(var i=0;i<parts.length;i++){
      if(hay.indexOf(parts[i]) === -1) return false;
    }
    return true;
  }

  function regexMatch(hay, pattern){
    if(!pattern) return true;
    try{
      return new RegExp(pattern, 'i').test(hay);
    } catch(e){
      return false;
    }
  }

  function searchMatches(hay, q){
    if(!q) return true;
    if(_filter.regexMode) return regexMatch(hay, q);
    return tokensMatch(hay, q);
  }

  function loadPrefs(){
    try{
      var raw = localStorage.getItem('terminal_wire_v1');
      if(raw){
        var o = JSON.parse(raw);
        if(typeof o.search === 'string') _filter.search = o.search;
        if(typeof o.source === 'string') _filter.source = o.source;
        if(typeof o.ccy === 'string') _filter.ccy = o.ccy;
        if(typeof o.regexMode === 'boolean') _filter.regexMode = o.regexMode;
        if(typeof o.bank === 'string') _filter.bank = o.bank;
      }
    } catch(e){}
    if(location.hash && location.hash.indexOf('wire&') === 1){
      try{
        var qs = location.hash.slice(1).replace(/^wire&/, '');
        var p = new URLSearchParams(qs);
        if(p.has('q')) _filter.search = p.get('q') || '';
        if(p.has('src')) _filter.source = (p.get('src') || '').toLowerCase();
        if(p.has('ccy')) _filter.ccy = (p.get('ccy') || '').toUpperCase();
        if(p.has('rx')) _filter.regexMode = p.get('rx') === '1';
        if(p.has('bk')) _filter.bank = (p.get('bk') || '').toLowerCase();
      } catch(e2){}
    }
  }

  function savePrefs(){
    try{
      localStorage.setItem('terminal_wire_v1', JSON.stringify(_filter));
      var p = new URLSearchParams();
      if(_filter.search) p.set('q', _filter.search);
      if(_filter.source) p.set('src', _filter.source);
      if(_filter.ccy) p.set('ccy', _filter.ccy);
      if(_filter.regexMode) p.set('rx', '1');
      if(_filter.bank) p.set('bk', _filter.bank);
      var frag = 'wire&' + p.toString();
      if(window.history && window.history.replaceState){
        window.history.replaceState(null, '', '#' + frag);
      }
    } catch(e){}
  }

  function syncInputs(){
    var s = document.getElementById('wireSearch');
    var src = document.getElementById('wireSource');
    var ccy = document.getElementById('wireCcy');
    var rx = document.getElementById('wireRegex');
    var bk = document.getElementById('wireBank');
    if(s) s.value = _filter.search;
    if(src){
      src.value = _filter.source || '';
    }
    if(ccy) ccy.value = _filter.ccy || '';
    if(rx) rx.checked = !!_filter.regexMode;
    if(bk) bk.value = _filter.bank || '';
  }

  function init(container){
    el = container;
    loadPrefs();
    var bankOpts = '<option value="">All</option>';
    for(var i=0;i<BANK_ORDER.length;i++){
      var b = BANK_ORDER[i];
      bankOpts += '<option value="'+b+'">'+escHtml(BANK_LABELS[b]||b)+'</option>';
    }
    el.innerHTML =
      '<div class="wire-toolbar">'+
        '<label>Search</label>'+
        '<input type="text" id="wireSearch" placeholder="keyword or /regex/">'+
        '<label><input type="checkbox" id="wireRegex"> Regex</label>'+
        '<label>Macro CB</label>'+
        '<select id="wireBank">'+bankOpts+'</select>'+
        '<label>Source</label>'+
        '<select id="wireSource"><option value="">All</option><option value="reuters">Reuters</option><option value="bloomberg">Bloomberg</option><option value="ft">FT</option><option value="wsj">WSJ</option><option value="bbc">BBC</option><option value="cnbc">CNBC</option><option value="ecb">ECB</option><option value="fed">FED</option><option value="imf">IMF</option></select>'+
        '<label>Currency</label>'+
        '<select id="wireCcy"><option value="">All</option><option value="USD">USD</option><option value="EUR">EUR</option><option value="GBP">GBP</option><option value="JPY">JPY</option><option value="CAD">CAD</option><option value="AUD">AUD</option><option value="NZD">NZD</option><option value="CHF">CHF</option></select>'+
        '<span style="margin-left:auto;font-size:10px;color:var(--text-dim)" id="wireCount">--</span>'+
      '</div>'+
      '<div class="wire-feed" id="wireFeed"></div>';

    syncInputs();

    document.getElementById('wireSearch').addEventListener('input', function(e){
      _filter.search = e.target.value;
      savePrefs();
      renderFeed();
    });
    document.getElementById('wireRegex').addEventListener('change', function(e){
      _filter.regexMode = !!e.target.checked;
      savePrefs();
      renderFeed();
    });
    document.getElementById('wireBank').addEventListener('change', function(e){
      _filter.bank = (e.target.value || '').toLowerCase();
      savePrefs();
      renderFeed();
    });
    document.getElementById('wireSource').addEventListener('change', function(e){
      _filter.source = e.target.value.toLowerCase();
      savePrefs();
      renderFeed();
    });
    document.getElementById('wireCcy').addEventListener('change', function(e){
      _filter.ccy = e.target.value.toUpperCase();
      savePrefs();
      renderFeed();
    });
  }

  function bankMatchesArticle(a){
    if(!_filter.bank) return true;
    var kws = WIRE_BANK_KW[_filter.bank];
    if(!kws) return true;
    var hay = searchHaystack(a);
    for(var i=0;i<kws.length;i++){
      if(hay.indexOf(kws[i]) !== -1) return true;
    }
    return false;
  }

  function filterArticles(){
    return newsArticles.filter(function(a){
      if(_filter.search){
        var hay = searchHaystack(a);
        if(!searchMatches(hay, _filter.search)) return false;
      }
      if(!bankMatchesArticle(a)) return false;
      if(_filter.source){
        if(shortSource(a.source).toLowerCase().indexOf(_filter.source)===-1) return false;
      }
      if(_filter.ccy){
        var hay2 = ((a.title||'')+(a.summary||'')).toUpperCase();
        if(hay2.indexOf(_filter.ccy)===-1) return false;
      }
      return true;
    });
  }

  function renderFeed(){
    var body = document.getElementById('wireFeed');
    if(!body) return;
    var filtered = filterArticles();
    if(!filtered.length){
      body.innerHTML = '<div class="empty-state">No articles matching filters</div>';
      document.getElementById('wireCount').textContent = '0 / '+newsArticles.length;
      return;
    }
    var html = '';
    for(var i=0;i<filtered.length;i++){
      var art = filtered[i];
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
    document.getElementById('wireCount').textContent = filtered.length+' / '+newsArticles.length;
  }

  function render(){ syncInputs(); renderFeed(); }
  function onData(type){ if(type==='news') renderFeed(); }

  registerScreen('wire', {init:init, render:render, onData:onData});
})();
