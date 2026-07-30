import json, urllib.request, urllib.parse, datetime

WATCHLIST = [
    ("NVDA", "NVIDIA Corp", "Equity", "Semis"),
    ("AAPL", "Apple Inc", "Equity", "Hardware"),
    ("MSFT", "Microsoft Corp", "Equity", "Software"),
    ("TSLA", "Tesla Inc", "Equity", "Auto / EV"),
    ("AMD", "Advanced Micro Devices", "Equity", "Semis"),
    ("META", "Meta Platforms", "Equity", "Internet"),
    ("JPM", "JPMorgan Chase", "Equity", "Financials"),
    ("XOM", "Exxon Mobil", "Equity", "Energy"),
    ("ES=F", "E-mini S&P 500 Future", "Index Future", "Index Future"),
    ("NQ=F", "E-mini Nasdaq 100 Future", "Index Future", "Index Future"),
    ("YM=F", "E-mini Dow Future", "Index Future", "Index Future"),
    ("RTY=F", "E-mini Russell 2000 Future", "Index Future", "Index Future"),
    ("GC=F", "Gold Future", "Commodity", "Metals"),
    ("SI=F", "Silver Future", "Commodity", "Metals"),
    ("CL=F", "WTI Crude Oil Future", "Commodity", "Energy"),
    ("NG=F", "Natural Gas Future", "Commodity", "Energy"),
    ("HG=F", "Copper Future", "Commodity", "Metals"),
    ("EURUSD=X", "Euro / US Dollar", "Forex", "Forex"),
    ("GBPUSD=X", "British Pound / US Dollar", "Forex", "Forex"),
    ("USDJPY=X", "US Dollar / Japanese Yen", "Forex", "Forex"),
    ("AUDUSD=X", "Australian Dollar / US Dollar", "Forex", "Forex"),
    ("USDCAD=X", "US Dollar / Canadian Dollar", "Forex", "Forex"),
]
INDICES = [("^GSPC", "SPX"), ("^NDX", "NDX"), ("^DJI", "DJI"), ("^VIX", "VIX")]

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; research-fetch/1.0)"}

def fetch_chart(symbol, rng="6mo", interval="1d"):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(symbol)}?interval={interval}&range={rng}"
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())

def ema(values, period):
    k = 2 / (period + 1)
    e = values[0]
    out = [e]
    for v in values[1:]:
        e = v * k + e * (1 - k)
        out.append(e)
    return out

def rsi(closes, period=14):
    if len(closes) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, len(closes)):
        d = closes[i] - closes[i - 1]
        gains.append(max(d, 0))
        losses.append(max(-d, 0))
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def atr(highs, lows, closes, period=14):
    trs = []
    for i in range(1, len(closes)):
        tr = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
        trs.append(tr)
    if len(trs) < period:
        return sum(trs) / len(trs)
    return sum(trs[-period:]) / period

def get_decimals(symbol):
    if symbol == "USDJPY=X":
        return 3
    if symbol.endswith("=X"):
        return 4
    if symbol == "NG=F":
        return 3
    if symbol == "HG=F":
        return 4
    return 2

def intraday_session_stats(symbol, gmtoffset, period=14):
    """Real intraday ATR + today's (most recent local session's) high/low, from 15-min bars.
    Day-trade sizing needs intraday-scaled numbers, not a multi-day swing range."""
    data = fetch_chart(symbol, rng="5d", interval="15m")
    result = data["chart"]["result"][0]
    quote = result["indicators"]["quote"][0]
    ts = result["timestamp"]
    closes, highs, lows, dates = [], [], [], []
    for i in range(len(ts)):
        if quote["close"][i] is None or quote["high"][i] is None or quote["low"][i] is None:
            continue
        closes.append(quote["close"][i])
        highs.append(quote["high"][i])
        lows.append(quote["low"][i])
        dates.append(datetime.datetime.fromtimestamp(ts[i] + gmtoffset, tz=datetime.timezone.utc).date())

    atr_intraday = atr(highs[-60:], lows[-60:], closes[-60:], period=period) if len(closes) > period else None

    # Bucket by local exchange date; use the latest date with enough bars, else fold in the prior session too.
    if not dates:
        return atr_intraday, None, None
    latest_date = dates[-1]
    idx = [i for i, d in enumerate(dates) if d == latest_date]
    if len(idx) < 4 and len(set(dates)) > 1:
        prior_dates = sorted(set(dates))[-2:]
        idx = [i for i, d in enumerate(dates) if d in prior_dates]
    session_hi = max(highs[i] for i in idx)
    session_lo = min(lows[i] for i in idx)
    return atr_intraday, session_hi, session_lo

def analyze(symbol, name, asset_class, sector):
    data = fetch_chart(symbol)
    result = data["chart"]["result"][0]
    meta = result["meta"]
    quote = result["indicators"]["quote"][0]
    closes = [c for c in quote["close"] if c is not None]
    vols = [v for v in quote["volume"] if v is not None]
    dec = get_decimals(symbol)

    last_close = meta.get("regularMarketPrice", closes[-1])
    ema21 = ema(closes[-100:], 21)[-1] if len(closes) >= 21 else None
    ema50 = ema(closes[-150:], 50)[-1] if len(closes) >= 50 else None
    rsi14 = rsi(closes[-40:])
    vol20 = sum(vols[-20:]) / 20 if len(vols) >= 20 else None
    last_vol = vols[-1] if vols else None
    prev_close = closes[-2] if len(closes) >= 2 else last_close
    chg_pct = (last_close - prev_close) / prev_close * 100
    has_volume = vol20 is not None and vol20 > 0

    atr_intraday, session_hi, session_lo = intraday_session_stats(symbol, meta.get("gmtoffset", 0))

    display_symbol = symbol.replace("=F", "").replace("=X", "")

    return {
        "symbol": display_symbol, "name": name, "assetClass": asset_class, "sector": sector,
        "decimals": dec,
        "last": round(last_close, dec),
        "chg_pct": round(chg_pct, 2),
        "ema21": round(ema21, dec) if ema21 else None,
        "ema50": round(ema50, dec) if ema50 else None,
        "rsi14": round(rsi14, 1) if rsi14 else None,
        "atrIntraday": round(atr_intraday, dec) if atr_intraday else None,
        "vol_ratio": round(last_vol / vol20, 2) if has_volume else None,
        "sessionHi": round(session_hi, dec) if session_hi else None,
        "sessionLo": round(session_lo, dec) if session_lo else None,
        "exch_time": meta.get("regularMarketTime"),
    }

def build_snapshot():
    out = {"fetched_utc": datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z"), "watchlist": [], "indices": []}

    for sym, name, asset_class, sector in WATCHLIST:
        try:
            out["watchlist"].append(analyze(sym, name, asset_class, sector))
        except Exception as e:
            out["watchlist"].append({"symbol": sym, "error": str(e)})

    for sym, label in INDICES:
        try:
            data = fetch_chart(sym, rng="5d")
            result = data["chart"]["result"][0]
            meta = result["meta"]
            closes = [c for c in result["indicators"]["quote"][0]["close"] if c is not None]
            last = meta.get("regularMarketPrice", closes[-1])
            prev = meta.get("chartPreviousClose", closes[-2] if len(closes) > 1 else last)
            out["indices"].append({
                "label": label, "last": round(last, 2),
                "chg_pct": round((last - prev) / prev * 100, 2)
            })
        except Exception as e:
            out["indices"].append({"label": label, "error": str(e)})

    return out

if __name__ == "__main__":
    print(json.dumps(build_snapshot(), indent=2))
