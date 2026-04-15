from __future__ import annotations

import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

from app.services.data import (
    fetch_ohlcv_batch_daily,
    fetch_ohlcv_daily,
    resample_weekly,
)


DB_PATH = Path(__file__).resolve().parents[2] / "data" / "prices.sqlite"


def _get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS price_data (
            ticker TEXT,
            date TEXT,
            interval TEXT,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume INTEGER,
            PRIMARY KEY (ticker, date, interval)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS cache_meta (
            ticker TEXT,
            interval TEXT,
            last_fetched TEXT,
            first_date TEXT,
            last_date TEXT,
            PRIMARY KEY (ticker, interval)
        )
        """
    )
    conn.commit()
    return conn


def is_cache_fresh(ticker: str, interval: str = "D", max_age_hours: int = 16) -> bool:
    conn = _get_conn()
    row = conn.execute(
        "SELECT last_fetched FROM cache_meta WHERE ticker = ? AND interval = ?",
        (ticker, interval),
    ).fetchone()
    conn.close()
    if row is None:
        return False
    last = datetime.fromisoformat(row[0])
    return (datetime.now() - last) < timedelta(hours=max_age_hours)


def load_from_cache(ticker: str, interval: str = "D") -> pd.DataFrame | None:
    conn = _get_conn()
    df = pd.read_sql_query(
        "SELECT date, open, high, low, close, volume FROM price_data "
        "WHERE ticker = ? AND interval = ? ORDER BY date",
        conn,
        params=(ticker, interval),
    )
    conn.close()
    if df.empty:
        return None
    df["date"] = pd.to_datetime(df["date"])
    df.set_index("date", inplace=True)
    df.columns = ["Open", "High", "Low", "Close", "Volume"]
    return df


def save_to_cache(ticker: str, df: pd.DataFrame, interval: str = "D") -> None:
    if df is None or df.empty:
        return
    conn = _get_conn()
    conn.execute(
        "DELETE FROM price_data WHERE ticker = ? AND interval = ?",
        (ticker, interval),
    )
    records = []
    for idx, row in df.iterrows():
        records.append(
            (
                ticker,
                str(idx.date()) if hasattr(idx, "date") else str(idx),
                interval,
                float(row["Open"]) if pd.notna(row["Open"]) else None,
                float(row["High"]) if pd.notna(row["High"]) else None,
                float(row["Low"]) if pd.notna(row["Low"]) else None,
                float(row["Close"]),
                int(row["Volume"]) if pd.notna(row["Volume"]) else 0,
            )
        )
    conn.executemany(
        "INSERT OR REPLACE INTO price_data "
        "(ticker, date, interval, open, high, low, close, volume) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        records,
    )
    dates = df.index
    conn.execute(
        "INSERT OR REPLACE INTO cache_meta "
        "(ticker, interval, last_fetched, first_date, last_date) "
        "VALUES (?, ?, ?, ?, ?)",
        (
            ticker,
            interval,
            datetime.now().isoformat(),
            str(dates[0].date()),
            str(dates[-1].date()),
        ),
    )
    conn.commit()
    conn.close()


def get_weekly(
    ticker: str,
    start: str | date = "2016-01-01",
    refresh: bool = False,
) -> pd.DataFrame | None:
    """Return weekly OHLCV from cache, fetching + resampling from daily if needed."""
    if not refresh and is_cache_fresh(ticker, "W"):
        cached = load_from_cache(ticker, "W")
        if cached is not None and not cached.empty:
            return cached

    daily = fetch_ohlcv_daily(ticker, start=start)
    if daily is None or daily.empty:
        return None
    save_to_cache(ticker, daily, "D")
    weekly = resample_weekly(daily)
    if weekly.empty:
        return None
    save_to_cache(ticker, weekly, "W")
    return weekly


def get_weekly_batch(
    tickers: list[str],
    start: str | date = "2016-01-01",
    refresh: bool = False,
) -> dict[str, pd.DataFrame]:
    """Batch version: returns {ticker: weekly_df}. Uses cache where fresh."""
    result: dict[str, pd.DataFrame] = {}
    to_fetch: list[str] = []
    for t in tickers:
        if not refresh and is_cache_fresh(t, "W"):
            cached = load_from_cache(t, "W")
            if cached is not None and not cached.empty:
                result[t] = cached
                continue
        to_fetch.append(t)

    if to_fetch:
        daily_batch = fetch_ohlcv_batch_daily(to_fetch, start=start)
        for t, daily in daily_batch.items():
            if daily.empty:
                continue
            save_to_cache(t, daily, "D")
            weekly = resample_weekly(daily)
            if weekly.empty:
                continue
            save_to_cache(t, weekly, "W")
            result[t] = weekly

    return result
