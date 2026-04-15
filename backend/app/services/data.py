from __future__ import annotations

import time
from datetime import date, datetime, timezone
from typing import Any

import pandas as pd
import requests

_YAHOO_CHART = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
_BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

_session = requests.Session()
_session.headers.update({"User-Agent": _BROWSER_UA, "Accept": "application/json"})


def _to_ts(d: str | date) -> int:
    if isinstance(d, str):
        dt = datetime.fromisoformat(d)
    elif isinstance(d, datetime):
        dt = d
    else:
        dt = datetime.combine(d, datetime.min.time())
    return int(dt.replace(tzinfo=timezone.utc).timestamp())


def _parse_chart(payload: dict[str, Any]) -> pd.DataFrame:
    try:
        result = payload["chart"]["result"]
    except (KeyError, TypeError):
        return pd.DataFrame()
    if not result:
        return pd.DataFrame()
    r = result[0]
    ts = r.get("timestamp") or []
    if not ts:
        return pd.DataFrame()
    ind = r.get("indicators", {})
    quote = (ind.get("quote") or [{}])[0]
    adj = ind.get("adjclose")
    adj_close = adj[0].get("adjclose") if adj else None

    close = adj_close if adj_close is not None else quote.get("close") or []
    open_ = quote.get("open") or []
    high = quote.get("high") or []
    low = quote.get("low") or []
    volume = quote.get("volume") or []

    df = pd.DataFrame(
        {
            "Open": open_,
            "High": high,
            "Low": low,
            "Close": close,
            "Volume": volume,
        },
        index=pd.to_datetime(ts, unit="s").normalize(),
    )
    df.index.name = "date"
    df = df.dropna(subset=["Close"])
    if df.empty:
        return df

    # If using adj_close, proportionally back out the ratio on OHLC so everything
    # is on the same adjusted basis.
    raw_close = quote.get("close") or []
    if adj_close is not None and raw_close and len(raw_close) == len(ts):
        raw_close_s = pd.Series(raw_close, index=df.index.union(df.index).sort_values())
        ratio_series = df["Close"] / pd.Series(raw_close, index=df.index).replace(0, pd.NA)
        ratio_series = ratio_series.reindex(df.index)
        df["Open"] = df["Open"] * ratio_series
        df["High"] = df["High"] * ratio_series
        df["Low"] = df["Low"] * ratio_series

    df["Volume"] = df["Volume"].fillna(0).astype("int64")
    return df


def fetch_ohlcv_daily(
    ticker: str,
    start: str | date = "2016-01-01",
    end: str | date | None = None,
    retries: int = 3,
) -> pd.DataFrame:
    """Fetch daily OHLCV from Yahoo's chart API. Returns DataFrame with DatetimeIndex."""
    params = {
        "interval": "1d",
        "period1": _to_ts(start),
        "period2": _to_ts(end) if end else int(datetime.now(tz=timezone.utc).timestamp()),
        "events": "div,splits",
        "includeAdjustedClose": "true",
    }
    url = _YAHOO_CHART.format(symbol=ticker)
    last_exc: Exception | None = None
    for attempt in range(retries):
        try:
            resp = _session.get(url, params=params, timeout=15)
            if resp.status_code == 429:
                time.sleep(2 * (attempt + 1))
                continue
            resp.raise_for_status()
            return _parse_chart(resp.json())
        except requests.RequestException as e:
            last_exc = e
            time.sleep(1.5 * (attempt + 1))
    if last_exc:
        print(f"[data] {ticker}: {last_exc}")
    return pd.DataFrame()


def fetch_ohlcv_batch_daily(
    tickers: list[str],
    start: str | date = "2016-01-01",
    end: str | date | None = None,
) -> dict[str, pd.DataFrame]:
    """Batch = sequential single-ticker calls with small delay to stay under rate limits."""
    result: dict[str, pd.DataFrame] = {}
    for i, t in enumerate(tickers):
        df = fetch_ohlcv_daily(t, start=start, end=end)
        if not df.empty:
            result[t] = df
        # Pace ourselves: 6 req/sec is safely under Yahoo's public limits.
        if i < len(tickers) - 1:
            time.sleep(0.15)
    return result


def resample_weekly(daily: pd.DataFrame) -> pd.DataFrame:
    """Resample daily OHLCV to weekly (W-FRI) bars."""
    if daily.empty:
        return daily
    weekly = daily.resample("W-FRI").agg(
        {
            "Open": "first",
            "High": "max",
            "Low": "min",
            "Close": "last",
            "Volume": "sum",
        }
    )
    return weekly.dropna(subset=["Close"])
