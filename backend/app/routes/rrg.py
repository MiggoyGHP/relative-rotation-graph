from __future__ import annotations

from typing import Any

import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from app.services.cache import get_weekly_batch
from app.services.fundamentals import get_fundamentals, is_etf, point_in_time_score
from app.services.rrg_engine import compute_rrg_series
from app.services.volume import clip_rvol, weekly_rvol

router = APIRouter()


def _build_point(
    date: pd.Timestamp,
    rs_ratio: float,
    rs_mom: float,
    quadrant: str,
    rvol: float | None,
    fund_score: float | None,
) -> dict[str, Any]:
    return {
        "date": str(date.date()),
        "rs_ratio": None if pd.isna(rs_ratio) else round(float(rs_ratio), 3),
        "rs_momentum": None if pd.isna(rs_mom) else round(float(rs_mom), 3),
        "quadrant": quadrant,
        "rvol": None if rvol is None or pd.isna(rvol) else round(float(rvol), 3),
        "fund_score": None if fund_score is None else round(float(fund_score), 2),
    }


def _compute_series_for(
    tickers: list[str],
    benchmark: str,
    n: int,
    start: str,
    end: str | None,
    tail: int | None,
) -> dict[str, Any]:
    universe_and_bench = list(dict.fromkeys(tickers + [benchmark]))
    data = get_weekly_batch(universe_and_bench, start=start)

    if benchmark not in data or data[benchmark].empty:
        raise HTTPException(status_code=400, detail=f"No data for benchmark {benchmark}")

    bench_close = data[benchmark]["Close"]
    end_ts = pd.Timestamp(end) if end else None

    series_out = []
    as_of = None

    for t in tickers:
        if t not in data or data[t].empty:
            continue
        tdf = data[t]
        rrg = compute_rrg_series(tdf["Close"], bench_close, n=n)
        if rrg.empty:
            continue
        rvol_series = clip_rvol(weekly_rvol(tdf["Volume"], n=20))
        rvol_aligned = rvol_series.reindex(rrg.index)

        fund_df = get_fundamentals(t) if not is_etf(t) else None

        if end_ts is not None:
            rrg = rrg.loc[rrg.index <= end_ts]
        rrg = rrg.dropna(subset=["rs_ratio", "rs_momentum"])
        if rrg.empty:
            continue
        if tail is not None and tail > 0:
            rrg = rrg.tail(tail)

        points = []
        for idx, row in rrg.iterrows():
            rvol_val = rvol_aligned.get(idx, None)
            if rvol_val is not None and pd.isna(rvol_val):
                rvol_val = None
            fund_val = point_in_time_score(fund_df, idx) if fund_df is not None else None
            points.append(
                _build_point(
                    idx, row["rs_ratio"], row["rs_momentum"], row["quadrant"],
                    rvol_val, fund_val,
                )
            )

        if points:
            as_of = points[-1]["date"] if as_of is None else max(as_of, points[-1]["date"])
            series_out.append({
                "ticker": t,
                "is_etf": is_etf(t),
                "points": points,
            })

    return {
        "benchmark": benchmark,
        "n": n,
        "asOf": as_of,
        "series": series_out,
    }


@router.get("/api/rrg")
def get_rrg(
    universe: str = Query(..., description="Comma-separated tickers"),
    benchmark: str = Query("SPY"),
    n: int = Query(14, ge=2, le=52),
    tail: int = Query(10, ge=1, le=100),
    end: str | None = Query(None, description="ISO date; defaults to latest"),
    start: str = Query("2016-01-01"),
):
    tickers = [t.strip().upper() for t in universe.split(",") if t.strip()]
    if not tickers:
        raise HTTPException(status_code=400, detail="universe is empty")
    return _compute_series_for(tickers, benchmark.upper(), n, start, end, tail)


@router.get("/api/rrg/range")
def get_rrg_range(
    universe: str = Query(...),
    benchmark: str = Query("SPY"),
    n: int = Query(14, ge=2, le=52),
    start: str = Query("2016-01-01"),
    end: str | None = Query(None),
):
    """Full weekly series from `start` to `end`; used by slider / playback."""
    tickers = [t.strip().upper() for t in universe.split(",") if t.strip()]
    if not tickers:
        raise HTTPException(status_code=400, detail="universe is empty")
    return _compute_series_for(tickers, benchmark.upper(), n, start, end, tail=None)
