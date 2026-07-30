# A+ DESK

A day-trading terminal where four agent roles (Technical Analyst, Macro/News Analyst, Risk Manager, Chief/Arbiter) grade setups across equities, index futures, commodities, and forex using real market data — no fabricated numbers.

- Prices, daily EMA/RSI, and intraday 15-min ATR + session high/low are pulled live from Yahoo Finance's public chart endpoint (no API key needed).
- Stops and targets are sized for day trading off intraday volatility, not swing-scale daily ranges.
- Only setups with a 1–3 reward-to-risk ratio clear the Risk Manager; everything else grades PASS.
- Tick a setup you actually took and its outcome auto-resolves against real prices on the next refresh, rolling into a win-rate stat (stored in your browser's local storage).

## How it stays live

`.github/workflows/hourly-refresh.yml` runs `update_snapshot.py` every hour via GitHub Actions, which re-fetches real data and commits the updated `index.html` — no server, no device that needs to stay on.

## Files

- `index.html` — the page itself (static HTML/CSS/JS, no build step)
- `fetch_real.py` — fetches and computes real EMA/RSI/ATR/session-range data
- `update_snapshot.py` — splices a fresh snapshot into `index.html` between the `SNAPSHOT_START`/`SNAPSHOT_END` markers

Not investment advice — an algorithmic technical/risk scan for demonstration.
