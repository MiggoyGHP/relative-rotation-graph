# RRG — Relative Rotation Graph

Personal interactive Relative Rotation Graph viewer. Weekly cadence, history back to 2016, multi-session, with **volume-weighted tails** and **fundamental colorimetric overlay**.

## What it does

Plot tickers on the JdK RS-Ratio / RS-Momentum plane relative to any benchmark. Each ticker draws a historical tail where:

- **Tail width** encodes relative volume (RVOL) — thick tails = institutional participation expanding.
- **Tail color** encodes EPS + revenue growth *acceleration* on an RdYlGn gradient — red = contracting, green = accelerating. Red tail in Leading = technical rotation without fundamental backing. Green tail hooking into Leading = CANSLIM-style aligned rotation.

## Sessions

Each open tab is an independent session saved to `localStorage`, so refreshing or closing the browser preserves your setup. Three ways to launch a session:

1. **Sectors vs SPY** preset — 11 SPDR sector ETFs (XLK, XLC, XLE, XLF, XLI, XLV, XLU, XLP, XLY, XLRE, XLB).
2. **Drill-down** — click any sector dot in the Sectors chart; a new session opens where that sector becomes the benchmark and its top holdings become the universe.
3. **Custom watchlist** — upload a TradingView watchlist export (`.txt`/`.csv`); parsed symbols are plotted against a benchmark of your choice (default SPY).

## Math

JdK-style normalized formulas on weekly W-FRI bars:

```
RS           = ticker_close / benchmark_close
RS-Ratio     = 100 + zscore(RS,    rolling n)
RS-Momentum  = 100 + zscore(ΔRS-Ratio, rolling n)
```

`n` defaults to 14 weeks and is tunable from the UI (4–26). Values cluster around 100 by construction; the four quadrants are the standard Leading / Weakening / Lagging / Improving split.

RVOL is `weekly_volume / trailing_20w_mean_excl_current`, clipped to `[0.3, 4.0]`.

Fundamentals come from **SEC EDGAR Company Facts** (XBRL quarterly 10-Q filings). EPS and revenue YoY growth are computed by matching each fiscal period end to the same quarter one year prior (`±30 day window`), then acceleration is the change in YoY rate from the previous quarter. The composite score is `clip(50·eps_accel + 50·rev_accel, [-100, +100])` and is looked up point-in-time by the SEC filing date (not fiscal period end) to avoid lookahead.

## Architecture

```
RRG/
├── backend/        FastAPI + pandas + SQLite cache (data/prices.sqlite)
│   └── app/
│       ├── services/   data, cache, rrg_engine, volume, fundamentals, tv_watchlist
│       ├── routes/     /api/rrg, /api/rrg/range, /api/sectors, /api/watchlist/parse, /api/history
│       └── config/     sectors.json (editable)
└── frontend/       Next.js 16 App Router + React 19 + Plotly.js + Zustand
    ├── app/
    │   ├── page.tsx            # session launcher (sectors + watchlist)
    │   └── session/[id]/       # session viewer
    ├── components/
    │   ├── RRGChart.tsx        # per-segment tail traces, RVOL width, fund color
    │   ├── TailControls.tsx    # tail length, n, RVOL/color/label toggles
    │   ├── DateSlider.tsx      # history scrub + playback
    │   ├── SessionTabs.tsx     # persistent tab bar
    │   └── WatchlistUploader.tsx
    └── lib/        api.ts, sessionStore.ts (zustand persist), types.ts
```

Data path: `yfinance` was replaced by a direct Yahoo chart API client (`requests` + browser UA) because curl_cffi auth was failing in late 2025. Fundamentals use SEC EDGAR instead of yfinance for the same reason — and SEC is a strictly better source anyway (authoritative, point-in-time by filing date, no consent wall).

## Running

### Backend (FastAPI)

```bash
cd backend
python -m venv .venv
.venv/Scripts/python.exe -m pip install -e .     # or install deps listed in pyproject.toml
.venv/Scripts/python.exe -m uvicorn app.main:app --port 8000 --reload
```

First call to `/api/rrg` with a new universe will fetch + cache weekly bars and fundamentals, which takes ~1s per ticker. Run the warmup once to prime:

```bash
.venv/Scripts/python.exe -m scripts.warmup
```

### Frontend (Next.js)

```bash
cd frontend
npm install
npm run dev       # http://localhost:3000
```

`frontend/.env.local` sets `NEXT_PUBLIC_API_BASE=http://localhost:8000`.

### Tests

```bash
cd backend
.venv/Scripts/python.exe -m pytest tests/ -v
```

## Caveats

- **Survivorship bias**: `config/sectors.json` holds today's top sector components. Historical drill-down (e.g. XLK components in 2016) uses today's list, which misses past leaders that dropped out.
- **Partial-week bias**: The most recent bar is a partial week (resampled volume is smaller than a full week), so its RVOL will appear low until the week closes on Friday.
- **Fundamental coverage**: SEC EDGAR only covers US-filing issuers and quarterly 10-Q filings. ADRs, foreign issuers, and private-to-public transitions may return `null`. ETFs are hardcoded to `null` fundamentals.
- **Yahoo rate limits**: The direct chart-API client paces batch fetches at ~6 req/sec. First-time warmup for ~120 tickers takes 20–30 seconds of network time.

## Editing the universe

To change which stocks appear in a sector drill-down, edit `backend/app/config/sectors.json` and restart the backend. The format is:

```json
{
  "benchmark": "SPY",
  "sectors": {
    "XLK": { "name": "Technology", "components": ["AAPL", "MSFT", "NVDA", ...] }
  }
}
```
