from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.services.cache import get_weekly

router = APIRouter()


@router.get("/api/history/{ticker}")
def get_history(
    ticker: str,
    start: str = Query("2016-01-01"),
) -> dict:
    df = get_weekly(ticker.upper(), start=start)
    if df is None or df.empty:
        raise HTTPException(status_code=404, detail=f"No data for {ticker}")
    return {
        "ticker": ticker.upper(),
        "interval": "W",
        "bars": [
            {
                "date": str(idx.date()),
                "open": float(row["Open"]),
                "high": float(row["High"]),
                "low": float(row["Low"]),
                "close": float(row["Close"]),
                "volume": int(row["Volume"]),
            }
            for idx, row in df.iterrows()
        ],
    }
