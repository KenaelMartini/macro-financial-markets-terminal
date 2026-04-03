/* ── RISK: VaR/CVaR calc, VIX, F&G, FX sizing avec paire ─────── */

(function(){
  var el;
  var _riskData = null;

  /* $/pip approximatif pour 1.00 lot standard (100k) — indicatif */
  var FX_PAIRS = [
    {label:'EUR/USD', pip:10},
    {label:'GBP/USD', pip:10},
    {label:'USD/JPY', pip:9.2},
    {label:'GBP/JPY', pip:6.8},
    {label:'EUR/JPY', pip:6.8},
    {label:'AUD/USD', pip:10},
    {label:'NZD/USD', pip:10},
    {label:'USD/CHF', pip:11},
    {label:'USD/CAD', pip:7.6},
    {label:'EUR/GBP', pip:13},
    {label:'XAU/USD (oz)', pip:1},
    {label:'Custom (manual $/pip)', pip:null}
  ];

  function init(container){
    el = container;
    var pairOpts = '';
    for(var i=0;i<FX_PAIRS.length;i++){
      var p = FX_PAIRS[i];
      pairOpts += '<option value="'+i+'">'+escHtml(p.label)+'</option>';
    }
    el.innerHTML =
      '<div class="risk-layout risk-layout-wide">'+
        '<div class="risk-col">'+
          '<div class="risk-card"><div class="risk-card-head">Market stress</div><div class="risk-card-body" id="riskStress"></div></div>'+
          '<div class="risk-card"><div class="risk-card-head">Référence SPY — IBKR (95% — lecture seule)</div><div class="risk-card-body" id="riskVar"></div></div>'+
        '</div>'+
        '<div class="risk-col">'+
          '<div class="risk-card">'+
            '<div class="risk-card-head">Calculateur VaR / CVaR (historique 1 jour)</div>'+
            '<div class="risk-card-body risk-calc">'+
              '<div class="risk-chip">Daily risk snapshot</div>'+
              '<p class="risk-fine">Méthode : quantile des rendements journaliers <strong>simples</strong> (historique IBKR). TWS doit être connecté. Ce n’est pas une prédiction.</p>'+
              '<label>Symbole (liste terminal / IBKR)</label>'+
              '<input type="text" id="riskVarSym" placeholder="SPY, AAPL, EURUSD=X, ES=F…" value="SPY">'+
              '<label>Portefeuille (USD)</label>'+
              '<input type="number" id="riskVarPort" value="100000" step="1000" min="1">'+
              '<label>Niveau de confiance</label>'+
              '<select id="riskVarConf">'+
                '<option value="0.90">90%</option>'+
                '<option value="0.95" selected>95%</option>'+
                '<option value="0.99">99%</option>'+
              '</select>'+
              '<label>Fenêtre (jours ouvrés env.)</label>'+
              '<input type="number" id="riskVarLb" value="252" min="30" max="2000" step="1">'+
              '<button type="button" class="risk-btn" id="riskVarBtn">Calculer VaR / CVaR</button>'+
              '<div class="risk-out" id="riskVarCalcOut"></div>'+
            '</div>'+
          '</div>'+
          '<div class="risk-card">'+
            '<div class="risk-card-head">Taille de position FX (choisir la paire)</div>'+
            '<div class="risk-card-body risk-calc">'+
              '<div class="risk-chip">Execution sizing</div>'+
              '<label>Paire tradée</label>'+
              '<select id="riskPairSel">'+pairOpts+'</select>'+
              '<label>Compte (USD)</label><input type="number" id="riskAcct" value="100000" step="1000">'+
              '<label>Risque % par trade</label><input type="number" id="riskPct" value="1" step="0.1" min="0.1">'+
              '<label>Stop (pips)</label><input type="number" id="riskPips" value="25" step="1" min="1">'+
              '<label>$/pip par 1.00 lot</label><input type="number" id="riskPipVal" value="10" step="0.1" min="0.1">'+
              '<div class="risk-out" id="riskLotOut"></div>'+
              '<p class="risk-fine">Lots ≈ (Compte × Risque%) ÷ (Stop pips × $/pip). Ajustez $/pip si lot micro/mini.</p>'+
            '</div>'+
          '</div>'+
        '</div>'+
      '</div>';

    document.getElementById('riskPairSel').addEventListener('change', onPairChange);
    document.getElementById('riskAcct').addEventListener('input', calcLots);
    document.getElementById('riskPct').addEventListener('input', calcLots);
    document.getElementById('riskPips').addEventListener('input', calcLots);
    document.getElementById('riskPipVal').addEventListener('input', calcLots);
    document.getElementById('riskVarBtn').addEventListener('click', runVarCalc);
    onPairChange();
  }

  function onPairChange(){
    var idx = parseInt(document.getElementById('riskPairSel').value, 10);
    var p = FX_PAIRS[idx];
    var inp = document.getElementById('riskPipVal');
    if(p && p.pip != null){
      inp.value = String(p.pip);
      inp.readOnly = true;
    } else {
      inp.readOnly = false;
    }
    calcLots();
  }

  function calcLots(){
    var acct = parseFloat(document.getElementById('riskAcct').value) || 0;
    var pct = parseFloat(document.getElementById('riskPct').value) || 0;
    var pips = parseFloat(document.getElementById('riskPips').value) || 1;
    var pp = parseFloat(document.getElementById('riskPipVal').value) || 1;
    var riskUsd = acct * (pct / 100);
    var denom = pips * pp;
    var lots = denom > 0 ? riskUsd / denom : 0;
    var pairLab = FX_PAIRS[parseInt(document.getElementById('riskPairSel').value,10)] || {};
    document.getElementById('riskLotOut').innerHTML =
      '<div class="risk-kpi"><span class="k">Pair</span><span class="v">'+escHtml(pairLab.label||'Pair')+'</span></div>'+
      '<div class="risk-kpi"><span class="k">Risk $</span><span class="v">$ '+riskUsd.toFixed(0)+'</span></div>'+
      '<div class="risk-kpi"><span class="k">Lots</span><span class="v">'+lots.toFixed(2)+' std</span></div>';
  }

  function runVarCalc(){
    var out = document.getElementById('riskVarCalcOut');
    out.innerHTML = 'Calcul…';
    var sym = document.getElementById('riskVarSym').value.trim();
    var port = parseFloat(document.getElementById('riskVarPort').value);
    var conf = parseFloat(document.getElementById('riskVarConf').value);
    var lb = parseInt(document.getElementById('riskVarLb').value, 10);
    fetch(API_BASE+'/api/risk/var-calc', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({symbol:sym, portfolio_usd:port, confidence:conf, lookback_days:lb})
    }).then(function(r){return r.json();}).then(function(d){
      if(d.error){
        out.innerHTML = '<span class="chg down">'+escHtml(d.detail||d.error)+'</span>';
        return;
      }
      out.innerHTML =
        '<div class="risk-line"><span class="lab">Sous-jacent</span><span class="val">'+escHtml(d.symbol)+'</span></div>'+
        '<div class="risk-line"><span class="lab">VaR 1j (perte)</span><span class="val chg down">$ '+d.var_1d_usd+'</span><span class="meta">('+d.var_loss_pct_1d+'% du portef.)</span></div>'+
        '<div class="risk-line"><span class="lab">CVaR 1j (perte moy. queue)</span><span class="val chg down">$ '+d.cvar_1d_usd+'</span><span class="meta">('+d.cvar_loss_pct_1d+'%)</span></div>'+
        '<div class="risk-line"><span class="lab">Rendements seuil</span><span class="meta">VaR '+d.var_return_pct+'% / CVaR '+d.cvar_return_pct+'% (1j)</span></div>'+
        '<div class="risk-line"><span class="lab">Obs.</span><span class="meta">'+d.observations+' jours — '+escHtml(d.method||'')+'</span></div>';
    }).catch(function(){
      out.innerHTML = '<span class="chg down">Erreur réseau</span>';
    });
  }

  function renderStress(){
    var box = document.getElementById('riskStress');
    if(!box) return;
    if(!_riskData){
      box.innerHTML = '<div class="empty-state">Chargement…</div>';
      return;
    }
    var vix = _riskData.vix;
    var fg = _riskData.fear_greed;
    var html = '';
    if(vix){
      var vc = vix.change_pct >= 0 ? 'up' : 'down';
      html += '<div class="risk-line"><span class="lab">VIX (IBKR)</span><span class="val">'+vix.price+'</span><span class="chg '+vc+'">'+(vix.change_pct>=0?'+':'')+vix.change_pct.toFixed(2)+'%</span></div>';
    } else html += '<div class="risk-line">VIX (IBKR): — <span class="meta">droits marché / TWS</span></div>';
    if(fg && fg.score != null){
      html += '<div class="risk-line"><span class="lab">Fear &amp; Greed</span><span class="val">'+fg.score+'</span><span class="meta">'+escHtml(fg.rating||'')+' · '+escHtml(fg.source||'')+'</span></div>';
    } else html += '<div class="risk-line">Fear &amp; Greed: —</div>';
    box.innerHTML = html;
  }

  function renderVar(){
    var box = document.getElementById('riskVar');
    if(!box) return;
    if(_riskData && _riskData.source === 'ibkr_offline'){
      box.innerHTML = '<div class="empty-state">IBKR hors ligne — lance TWS / Gateway (paper).</div>';
      return;
    }
    var vc = _riskData && _riskData.var_cvar;
    if(!vc){
      box.innerHTML = '<div class="empty-state">Indisponible — connecte TWS / IBKR pour l’historique SPY.</div>';
      return;
    }
    box.innerHTML =
      '<p style="font-size:10px;color:var(--text-dim);margin-bottom:8px">'+escHtml(vc.note||'')+'</p>'+
      '<div class="risk-line"><span class="lab">VaR 1j (rendement)</span><span class="val">'+vc.var_return_pct+'%</span></div>'+
      '<div class="risk-line"><span class="lab">CVaR 1j</span><span class="val">'+vc.cvar_return_pct+'%</span></div>'+
      '<div class="risk-line"><span class="lab">n</span><span class="meta">'+vc.observations+' · '+escHtml(vc.benchmark)+'</span></div>';
  }

  function load(){
    fetchJSON('/api/risk').then(function(data){
      _riskData = data;
      renderStress();
      renderVar();
      calcLots();
    });
  }

  function render(){ load(); }

  registerScreen('risk', {init:init, render:render});
})();
