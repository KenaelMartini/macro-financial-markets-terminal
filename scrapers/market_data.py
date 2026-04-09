# -*- coding: utf-8 -*-
"""
Live market data scraper via yfinance.
Background thread polls prices every MARKET_REFRESH_SEC.
"""

import time
import logging
from typing import List, Dict, Any, Optional

log = logging.getLogger("terminal.markets")

MARKET_REFRESH_SEC = 60

# Expanded universe: FX, crypto, rates, equities, commodities
INSTRUMENTS = [
    # FX majors & crosses
    {"symbol": "EURUSD=X", "name": "EUR/USD", "asset_class": "FX"},
    {"symbol": "GBPUSD=X", "name": "GBP/USD", "asset_class": "FX"},
    {"symbol": "JPY=X", "name": "USD/JPY", "asset_class": "FX"},
    {"symbol": "CHF=X", "name": "USD/CHF", "asset_class": "FX"},
    {"symbol": "AUDUSD=X", "name": "AUD/USD", "asset_class": "FX"},
    {"symbol": "NZDUSD=X", "name": "NZD/USD", "asset_class": "FX"},
    {"symbol": "CAD=X", "name": "USD/CAD", "asset_class": "FX"},
    {"symbol": "EURGBP=X", "name": "EUR/GBP", "asset_class": "FX"},
    {"symbol": "EURJPY=X", "name": "EUR/JPY", "asset_class": "FX"},
    {"symbol": "GBPJPY=X", "name": "GBP/JPY", "asset_class": "FX"},
    {"symbol": "EURCHF=X", "name": "EUR/CHF", "asset_class": "FX"},
    {"symbol": "AUDJPY=X", "name": "AUD/JPY", "asset_class": "FX"},
    {"symbol": "USDMXN=X", "name": "USD/MXN", "asset_class": "FX"},
    {"symbol": "USDZAR=X", "name": "USD/ZAR", "asset_class": "FX"},
    {"symbol": "USDCNH=X", "name": "USD/CNH", "asset_class": "FX"},
    {"symbol": "DX-Y.NYB", "name": "DXY", "asset_class": "FX"},
    # Crypto (USD)
    {"symbol": "BTC-USD", "name": "BTC/USD", "asset_class": "Crypto"},
    {"symbol": "ETH-USD", "name": "ETH/USD", "asset_class": "Crypto"},
    {"symbol": "SOL-USD", "name": "SOL/USD", "asset_class": "Crypto"},
    {"symbol": "XRP-USD", "name": "XRP/USD", "asset_class": "Crypto"},
    # Rates
    {"symbol": "^TNX", "name": "UST 10Y", "asset_class": "Rates"},
    {"symbol": "^FVX", "name": "UST 5Y", "asset_class": "Rates"},
    {"symbol": "^IRX", "name": "UST 13W", "asset_class": "Rates"},
    {"symbol": "^VIX", "name": "VIX", "asset_class": "Rates"},
    # Equities / indices
    {"symbol": "ES=F", "name": "S&P 500 F", "asset_class": "Equities"},
    {"symbol": "SPY", "name": "SPY", "asset_class": "Equities"},
    {"symbol": "NQ=F", "name": "Nasdaq F", "asset_class": "Equities"},
    {"symbol": "^GSPC", "name": "S&P 500", "asset_class": "Equities"},
    {"symbol": "^NDX", "name": "Nasdaq 100", "asset_class": "Equities"},
    {"symbol": "^STOXX50E", "name": "STOXX 50", "asset_class": "Equities"},
    {"symbol": "^N225", "name": "Nikkei 225", "asset_class": "Equities"},
    {"symbol": "^FTSE", "name": "FTSE 100", "asset_class": "Equities"},
    {"symbol": "AAPL", "name": "Apple", "asset_class": "Equities"},
    {"symbol": "MSFT", "name": "Microsoft", "asset_class": "Equities"},
    {"symbol": "NVDA", "name": "NVIDIA", "asset_class": "Equities"},
    # Commodities
    {"symbol": "GC=F", "name": "Gold", "asset_class": "Commodities"},
    {"symbol": "CL=F", "name": "WTI Oil", "asset_class": "Commodities"},
    {"symbol": "SI=F", "name": "Silver", "asset_class": "Commodities"},
    {"symbol": "NG=F", "name": "Nat Gas", "asset_class": "Commodities"},
    {"symbol": "HG=F", "name": "Copper", "asset_class": "Commodities"},
]

live_market_data: Dict[str, Any] = {"instruments": [], "last_refresh": ""}

_yf_available = False
try:
    import yfinance as yf

    _yf_available = True
except ImportError:
    log.warning("yfinance not installed -- market data will be empty. Run: pip install yfinance")


def _one_batch(symbols: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not _yf_available or not symbols:
        return []
    import yfinance as yf

    results = []
    tickers_str = " ".join(inst["symbol"] for inst in symbols)
    try:
        # Daily closes for robust "day vs day-1" % change (not a random 5d window).
        daily = yf.download(
            tickers_str,
            period="10d",
            interval="1d",
            group_by="ticker",
            progress=False,
            threads=True,
        )
        # Intraday last price (near real-time; Yahoo may still be delayed by symbol/exchange).
        intra = yf.download(
            tickers_str,
            period="1d",
            interval="5m",
            group_by="ticker",
            progress=False,
            threads=True,
        )
        for inst in symbols:
            sym = inst["symbol"]
            try:
                if len(symbols) == 1:
                    dfd = daily
                    dfi = intra
                else:
                    dfd = daily[sym] if sym in daily.columns.get_level_values(0) else None
                    dfi = intra[sym] if sym in intra.columns.get_level_values(0) else None
                if dfd is None or dfd.empty:
                    continue
                dfd = dfd.dropna(subset=["Close"])
                if dfd.empty:
                    continue

                # "Daily change" = last close vs previous close (close-to-close).
                last_close = float(dfd["Close"].iloc[-1])
                prev_close = float(dfd["Close"].iloc[-2]) if len(dfd) > 1 else last_close
                change_pct = ((last_close - prev_close) / prev_close * 100) if prev_close else 0.0

                # Current "price" = latest intraday close if available, else last daily close.
                current = last_close
                history = []
                if dfi is not None and not dfi.empty:
                    dfi = dfi.dropna(subset=["Close"])
                    if not dfi.empty:
                        current = float(dfi["Close"].iloc[-1])
                        history = dfi["Close"].tail(48).tolist()
                if not history:
                    history = dfd["Close"].tail(24).tolist()
                results.append(
                    {
                        "symbol": sym,
                        "name": inst["name"],
                        "asset_class": inst["asset_class"],
                        "price": round(current, 6),
                        "change_pct": round(change_pct, 4),
                        "history": [round(h, 6) for h in history],
                    }
                )
            except Exception as e:
                log.debug(f"Skipping {sym}: {e}")
    except Exception as e:
        log.warning(f"yfinance batch download failed: {e}")
    return results


def _fetch_quotes() -> List[Dict[str, Any]]:
    if not _yf_available:
        return []
    chunk = 22
    all_results: List[Dict[str, Any]] = []
    for i in range(0, len(INSTRUMENTS), chunk):
        batch = INSTRUMENTS[i : i + chunk]
        all_results.extend(_one_batch(batch))
    return all_results


def fetch_ohlc_candles(
    symbol: str,
    period: str = "6mo",
    interval: str = "1d",
) -> Optional[Dict[str, Any]]:
    """Daily (or hourly) OHLC for charting — used by /api/markets/candles."""
    if not _yf_available:
        return None
    import yfinance as yf

    try:
        t = yf.Ticker(symbol)
        df = t.history(period=period, interval=interval)
        if df is None or df.empty:
            return None
        candles = []
        for idx, row in df.iterrows():
            ts = idx
            if hasattr(ts, "strftime"):
                tstr = ts.strftime("%Y-%m-%d")
            else:
                tstr = str(idx)[:10]
            try:
                o = float(row["Open"])
                h = float(row["High"])
                l = float(row["Low"])
                c = float(row["Close"])
            except (TypeError, ValueError):
                continue
            if any(x != x for x in (o, h, l, c)):  # NaN
                continue
            hi = max(o, h, l, c)
            lo = min(o, h, l, c)
            candles.append(
                {
                    "time": tstr,
                    "open": round(o, 6),
                    "high": round(hi, 6),
                    "low": round(lo, 6),
                    "close": round(c, 6),
                }
            )
        # Chronologie strictement croissante + un seul point par jour (lightweight-charts)
        seen = set()
        uniq = []
        for bar in candles:
            k = bar["time"]
            if k in seen:
                continue
            seen.add(k)
            uniq.append(bar)
        uniq.sort(key=lambda x: x["time"])
        candles = uniq
        meta = next((x for x in INSTRUMENTS if x["symbol"] == symbol), None)
        return {
            "symbol": symbol,
            "name": (meta or {}).get("name", symbol),
            "interval": interval,
            "candles": candles,
        }
    except Exception as e:
        log.warning(f"OHLC {symbol}: {e}")
        return None


def refresh_loop():
    """Background thread: fetch market data every MARKET_REFRESH_SEC."""
    global live_market_data
    while True:
        try:
            instruments = _fetch_quotes()
            if instruments:
                live_market_data = {
                    "instruments": instruments,
                    "last_refresh": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                }
                log.info(f"Market refresh: {len(instruments)} instruments")
            elif not live_market_data.get("instruments"):
                log.info("Market data: yfinance returned no data (market may be closed)")
        except Exception as e:
            log.error(f"Market refresh error: {e}")
        time.sleep(MARKET_REFRESH_SEC)
