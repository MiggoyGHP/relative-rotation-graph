# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repo layout

Two independent apps in one repo, communicating over HTTP:

- [backend/](backend/) — FastAPI + pandas + SQLite price/fundamentals cache. Python ≥3.11, packaged via [pyproject.toml](backend/pyproject.toml).
- [frontend/](frontend/) — Next.js 16 App Router + React 19 + Plotly + Zustand. See [frontend/AGENTS.md](frontend/AGENTS.md) — this Next.js version has breaking changes from prior versions; consult `frontend/node_modules/next/dist/docs/` before writing Next-specific code.

## Common commands

Backend (run from [backend/](backend/)):

```bash
.venv/Scripts/python.exe -m uvicorn app.main:app --port 8000 --reload   # dev server
.venv/Scripts/python.exe -m pytest tests/ -v                            # all tests
.venv/Scripts/python.exe -m pytest tests/test_rrg_engine.py::test_rs_line_identity -v   # single test
.venv/Scripts/python.exe -m scripts.warmup                              # prime SQLite cache + fundamentals for default universe
```

Frontend (run from [frontend/](frontend/)):

```bash
npm run dev                                 # http://localhost:3000, expects backend on :8000
npm run build && npm run start              # production server build
STATIC_EXPORT=1 NEXT_PUBLIC_STATIC_MODE=1 npm run build   # static export to out/ for GitHub Pages
```

`frontend/.env.local` should set `NEXT_PUBLIC_API_BASE=http://localhost:8000` for local dev. There is no frontend lint or test script configured.

## Architecture

### Two execution modes

The frontend supports a **live mode** (talks to local FastAPI) and a **static mode** (`NEXT_PUBLIC_STATIC_MODE=1` + `STATIC_EXPORT=1`) where it reads pre-baked JSON snapshots from [frontend/public/snapshot/](frontend/public/snapshot/) instead of making API calls. [lib/api.ts](frontend/lib/api.ts) branches on `STATIC_MODE`. Snapshot keys are deterministic: `sectors`, `drill-XLK` etc., or arbitrary keys via `Session.snapshotKey`. The Macro preset uses `preset-macro` because its hand-curated universe doesn't match the algorithmic key. Watchlist upload is disabled in static mode.

When adding/changing a preset universe, the snapshot JSON in `public/snapshot/` must be regenerated to match — otherwise the static GitHub Pages build serves stale data.

### Backend data flow

Request → [routes/rrg.py](backend/app/routes/rrg.py) → [services/cache.py](backend/app/services/cache.py) (SQLite at `backend/data/prices.sqlite`) → on miss, [services/data.py](backend/app/services/data.py) hits Yahoo's chart API and resamples daily→weekly W-FRI bars → [services/rrg_engine.py](backend/app/services/rrg_engine.py) computes JdK RS-Ratio/Momentum (rolling z-scores centered at 100) → [services/volume.py](backend/app/services/volume.py) computes RVOL with **trailing mean excluding the current bar** (single-week spikes don't dilute themselves) → [services/fundamentals.py](backend/app/services/fundamentals.py) loads SEC EDGAR Company Facts, point-in-time aligned by filing date, not fiscal-period-end (avoids lookahead).

Two important data-source notes:

- `yfinance` is in `pyproject.toml` but **not used** for prices. [services/data.py](backend/app/services/data.py) calls Yahoo's chart endpoint directly with a browser UA because `curl_cffi` auth was failing in late 2025. Don't reintroduce yfinance for price data without re-validating.
- Fundamentals come from **SEC EDGAR** (`data.sec.gov`), not yfinance. EDGAR requires a descriptive `User-Agent` per their fair-use policy ([fundamentals.py:21](backend/app/services/fundamentals.py#L21)). Ticker→CIK is resolved via EDGAR full-text search and cached to `backend/data/sec_tickers.json`. ETFs (hardcoded set in [fundamentals.py:28](backend/app/services/fundamentals.py#L28)) and unresolvable tickers (ADRs, foreign issuers) return `null`.

### RRG math invariants

- All series are aligned on **W-FRI weekly bars**. The most recent bar is partial until Friday closes — RVOL will read low for it.
- `RS-Ratio = 100 + zscore(ticker_close/benchmark_close, n)` with `n` defaulting to 14, tunable 4–26 from the UI.
- `RS-Momentum = 100 + zscore(ΔRS-Ratio, n)`. Quadrants are split at 100/100 → Leading / Weakening / Lagging / Improving.
- Fundamental `fund_score = clip(50·eps_accel + 50·rev_accel, [-100, +100])` where `accel` is the row-to-row change in YoY growth rate. Looked up point-in-time by SEC filing date in [fundamentals.py:392](backend/app/services/fundamentals.py#L392).
- RVOL is clipped to `[0.3, 4.0]` for stable line-width rendering.

### Frontend session model

Each browser tab can hold multiple **sessions** stored in `localStorage` via [lib/sessionStore.ts](frontend/lib/sessionStore.ts) (Zustand `persist`). Three launchers in [app/page.tsx](frontend/app/page.tsx): SPDR sectors preset, Macro rotation preset (constant `MACRO_UNIVERSE` array), or TradingView watchlist upload.

Routing is intentionally **not** query-string based ([app/session/page.tsx:11-14](frontend/app/session/page.tsx#L11-L14)): GitHub Pages drops `?id=…` on some navigations under `trailingSlash: true` + static export, so the active session is read from `useSessionStore.activeId`. Don't switch session routing back to query strings.

### Sector drill-down

Clicking a sector dot in the Sectors chart creates a new session where that sector ETF becomes the benchmark and its components (from [backend/app/config/sectors.json](backend/app/config/sectors.json)) become the universe. The component list is current — historical drill-downs suffer survivorship bias.

## Editing the universes

- **Sector components**: edit [backend/app/config/sectors.json](backend/app/config/sectors.json) and restart backend.
- **Macro preset**: edit `MACRO_UNIVERSE` in [frontend/app/page.tsx](frontend/app/page.tsx). For static-mode parity, also regenerate `public/snapshot/preset-macro.json`.
