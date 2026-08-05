# A+ DESK

A multi-agent day-trading terminal. Four agent roles — Technical Analyst, Macro/Policy Analyst,
Risk Manager and Chief/Arbiter — grade setups across 22 instruments (equities, index futures,
commodities, forex) from real market data. Every number on the page is fetched, not fabricated.

**Live:** https://terfatsen-jpg.github.io/a-plus-desk/

## What it does

- **Deterministic, auditable grading.** Expand any agent row to see the full derivation: every
  scoring rule with its individual contribution, the raw inputs behind it, and which rung of the
  grade ladder fired. Grading is fixed rules, not a language model's opinion — so it is
  reproducible and inspectable.
- **Day-trade sizing.** Stops are 1.2x the *intraday* (15-min) ATR and targets reference the
  current session high/low, not a multi-day swing range. Only setups in a **1–3 reward-to-risk**
  band clear the Risk Manager; the floor tightens to 1.5 when VIX signals a cautious regime.
- **Policy-maker tracking.** Pulls the official Federal Reserve (speeches + monetary press), ECB
  and Bank of England feeds, identifies which named official is speaking, and weights them by
  seniority — a Chair or Vice Chair moves markets in a way a regional president does not.
  Instruments are mapped to the currencies whose policy actually bears on them, with direction:
  a hawkish Fed is USD-positive, which is EURUSD-*negative* but USDJPY-*positive*.
- **Event-risk blackout.** Pulls the scheduled US macro calendar and classifies each release by
  severity. A severity-3 print (Nonfarm Payrolls, CPI, PCE, an FOMC decision) inside **90 minutes**
  is a hard veto no matter how good the setup looks — an intraday stop cannot survive the gap
  through a payrolls print, so the measured R:R is fiction. Anything severity-2 or worse inside
  4 hours raises the R:R floor to 1.8 instead. The Risk Manager shows the full queue of what is
  coming and how far away it is.
- **CFTC net speculative positioning** for gold, silver, copper, crude, natural gas and the index
  futures — who is already leaning which way. Labelled with its real vintage: the figure is the
  previous report, and CFTC positions are as of the Tuesday before that.
- **Headline sentiment** per instrument, with the matched keywords shown so a score can be audited.
- **Charts.** TradingView Lightweight Charts, vendored locally, with entry/stop/target plotted.
- **Trade journal.** Tick a setup you actually took; it auto-resolves to WIN/LOSS against real
  prices on the next refresh and rolls into a win rate. Stored in your browser only.

## Honesty constraints (deliberate)

- Policy tone is scored by **literal phrase matching with word boundaries**. Naive substring
  matching is actively wrong here — "release", "increase" and "decrease" all contain "ease", so
  an *increase* in rates would score as dovish.
- When a headline contains no policy language, tone is reported as **"not stated in headlines"**
  rather than defaulting to a neutral score. Central-bank RSS titles are often bare
  ("Cook, Economic Outlook"); inventing a reading the text doesn't support would be fake precision.
- If the data worker is unreachable the page shows an error rather than stale numbers.

## Architecture

```
Cloudflare Worker (a-plus-desk-data)          GitHub Pages (this repo)
  :00 cron -> market data  -> KV "snapshot"     index.html fetches the merged
  :30 cron -> context      -> KV "context"      JSON on every page load
  GET /   -> merged snapshot + context
```

The two cron passes are split deliberately: Cloudflare's free plan allows **50 subrequests per
invocation** and the market pass alone uses 48 (22 instruments x 2 timeframes + 4 indices), so the
central-bank and news fetches cannot share that invocation.

Worker source lives in a sibling directory (`a-plus-desk-worker`), not in this repo.

## Data sources

| Layer | Source | Credentials |
|---|---|---|
| Prices, EMA/RSI/ATR, intraday bars | Yahoo Finance public chart endpoint | none |
| Fed speeches + monetary press | federalreserve.gov RSS | none |
| ECB releases | ecb.europa.eu RSS | none |
| Bank of England | bankofengland.co.uk RSS | none |
| Per-instrument headlines | Yahoo Finance search | none |
| Economic calendar + CFTC positioning | Nasdaq calendar API | none |
| Forward Fed speeches / FOMC dates | federalreserve.gov calendar JSON | none |
| Congress/Senate disclosures | Financial Modeling Prep | **`FMP_API_KEY` worker secret** |

Two traps in those feeds, both handled in `fetchEconCalendar`:

- Nasdaq's `date=X` returns the events for **X-1**. Verified against two known releases.
- Its time column is labelled `gmt` but carries **New York** time. Taking the label at face value
  would put every event 4–5 hours early; the offset is resolved from the tz database, not hardcoded,
  so the DST switchover doesn't silently shift the whole calendar.

Congressional trading is the one layer that needs a key — the free public S3 mirrors that used to
serve STOCK Act filings now return 403. Without the key that layer reports itself as disabled and
everything else runs. On FMP's free tier `limit` must be **≤ 25**; asking for more returns HTTP 402
rather than clamping, which fails the whole layer.

Disclosures are surfaced per instrument in the Macro/Policy Analyst, labelled with both the trade
date and the filing date. The STOCK Act allows weeks of lag, so this is positioning context — who
is already leaning which way — and deliberately not presented as an entry trigger.

Not investment advice — an algorithmic technical/risk scan for demonstration.

## Desktop app

`A+ DESK.app` is a native macOS bundle — own Dock icon, own window, no browser
chrome. Build it from the sibling `a-plus-desk-app` directory:

```bash
cd ../a-plus-desk-app && ./build.sh && cp -R "dist/A+ DESK.app" /Applications/
```

It wraps a dedicated Chrome app-mode window with an isolated `--user-data-dir`, so
it does not touch your normal browsing profile. There is deliberately no Electron
or Tauri step: a 100MB bundled runtime buys nothing for a single page that has to
be online to have real prices, and esbuild's native binary hangs on this machine.

The page is also an installable **PWA** — "Install" in Chrome or "Add to Dock" in
Safari works from any machine, no build required.

**The service worker caches the shell only.** Market data is network-only with no
fallback, because a cache-first rule over the data worker would serve last night's
prices as if they were live — exactly the failure the rest of the desk is built to
avoid. Offline, the shell launches and the page shows its normal "data worker
unreachable" error rather than stale numbers.
