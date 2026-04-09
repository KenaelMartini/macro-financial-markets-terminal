/* ── Constants & lookup tables ────────────────────────────── */

var API_BASE = '';
var REFRESH_MS = 15000;

var BANK_ORDER = ['fed','ecb','boe','boj','boc','rba','rbnz','snb'];

var BANK_LABELS = {
  fed:'FED', ecb:'ECB', boe:'BOE', boj:'BOJ',
  boc:'BOC', rba:'RBA', rbnz:'RBNZ', snb:'SNB'
};

var BANK_FLAGS = {
  fed:'\u{1F1FA}\u{1F1F8}', ecb:'\u{1F1EA}\u{1F1FA}', boe:'\u{1F1EC}\u{1F1E7}', boj:'\u{1F1EF}\u{1F1F5}',
  boc:'\u{1F1E8}\u{1F1E6}', rba:'\u{1F1E6}\u{1F1FA}', rbnz:'\u{1F1F3}\u{1F1FF}', snb:'\u{1F1E8}\u{1F1ED}'
};

var BANK_CCYS = {
  fed:'USD', ecb:'EUR', boe:'GBP', boj:'JPY',
  boc:'CAD', rba:'AUD', rbnz:'NZD', snb:'CHF'
};

var EVENT_BANK_MAP = {
  'fed':'fed','ecb':'ecb','european central bank':'ecb','european_central_bank':'ecb',
  'boe':'boe','bank of england':'boe','bank_of_england':'boe',
  'boj':'boj','bank of japan':'boj','bank_of_japan':'boj',
  'boc':'boc','rba':'rba','rbnz':'rbnz','snb':'snb'
};

var IMPACT_STARS = {
  High:'\u2605\u2605\u2605',
  Medium:'\u2605\u2605',
  Low:'\u2605',
  Holiday:'\u2298'
};

var FX8 = ['USD','EUR','GBP','JPY','CAD','AUD','NZD','CHF'];

var SCREEN_DEFS = [
  {id:'home',    label:'HOME',    key:'F1', desc:'Overview Dashboard'},
  {id:'wire',    label:'WIRE',    key:'F2', desc:'News Wire'},
  {id:'cenb',    label:'CENB',    key:'F3', desc:'Central Banks'},
  {id:'ecfc',    label:'ECFC',    key:'F4', desc:'Economic Calendar'},
  {id:'mktm',    label:'MKTM',    key:'F5', desc:'Market Monitor'},
  {id:'fxdash',  label:'FXDASH',  key:'F6', desc:'FX Dashboard'},
  {id:'signals', label:'SIGNALS', key:'F7', desc:'Macro Signals'},
  {id:'pricein', label:'PRICEIN', key:'F8', desc:'Price-In Analysis'},
  {id:'intel',   label:'INTEL',   key:'F9', desc:'AI Intelligence'},
  {id:'alert',   label:'ALERT',   key:'F10',desc:'Alert System'},
  {id:'risk',    label:'RISK',    key:'F11',desc:'Risk — VaR/CVaR, VIX, taille FX'},
  {id:'ylds',   label:'YLDS',    key:'F12',desc:'Yields (FRED) & Fed proxy'},
];

/* ── Shared mutable state ────────────────────────────────── */

var cbStates = {};
var cbEvents = {};
var newsArticles = [];
var calendarEvents = [];
var marketData = {};
var alertsList = [];
var wsConn = null;
