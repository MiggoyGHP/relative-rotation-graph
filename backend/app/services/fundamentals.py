"""Fundamentals via SEC EDGAR Company Facts.

Uses free, authoritative SEC filings as the source for quarterly EPS and revenue,
with point-in-time alignment on filing date (not fiscal period end). ETFs return
None; tickers not in the SEC ticker map (ADRs, foreign issuers) also return None.
"""
from __future__ import annotations

import json
import sqlite3
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests

from app.services.cache import DB_PATH

# Must identify ourselves per SEC policy. Any descriptive UA with contact works.
_UA = "rrg-research local-dev@localhost"
_FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik10}.json"
_SEARCH_URL = "https://efts.sec.gov/LATEST/search-index"

_session = requests.Session()
_session.headers.update({"User-Agent": _UA, "Accept": "application/json"})

ETF_SET = {
    "SPY", "QQQ", "DIA", "IWM", "VOO", "VTI",
    "XLK", "XLC", "XLE", "XLF", "XLI", "XLV",
    "XLU", "XLP", "XLY", "XLRE", "XLB",
    "SMH", "KRE", "XBI", "XOP", "ITB",
}

EPS_KEYS = ("EarningsPerShareDiluted", "EarningsPerShareBasic")
REV_KEYS = (
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "Revenues",
    "SalesRevenueNet",
)

_TICKER_CACHE_PATH = DB_PATH.parent / "sec_tickers.json"
_ticker_to_cik: dict[str, str] = {}
_ticker_cache_loaded = False


def _get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS fundamentals (
            ticker TEXT,
            report_date TEXT,
            fiscal_period_end TEXT,
            eps REAL,
            revenue REAL,
            eps_yoy REAL,
            rev_yoy REAL,
            eps_accel REAL,
            rev_accel REAL,
            fund_score REAL,
            PRIMARY KEY (ticker, report_date)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS fundamentals_meta (
            ticker TEXT PRIMARY KEY,
            last_fetched TEXT
        )
        """
    )
    conn.commit()
    return conn


def is_etf(ticker: str) -> bool:
    return ticker.upper() in ETF_SET


def _load_ticker_cache() -> None:
    global _ticker_to_cik, _ticker_cache_loaded
    if _ticker_cache_loaded:
        return
    if _TICKER_CACHE_PATH.exists():
        try:
            _ticker_to_cik = json.loads(_TICKER_CACHE_PATH.read_text())
        except Exception:
            _ticker_to_cik = {}
    _ticker_cache_loaded = True


def _save_ticker_cache() -> None:
    try:
        _TICKER_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _TICKER_CACHE_PATH.write_text(json.dumps(_ticker_to_cik))
    except Exception:
        pass


def _cik_for(ticker: str) -> str | None:
    """Resolve ticker → 10-digit zero-padded CIK, via EDGAR full-text search.

    Persists resolutions to a local JSON cache so we only hit the network once.
    """
    _load_ticker_cache()
    key = ticker.upper()
    if key in _ticker_to_cik:
        val = _ticker_to_cik[key]
        return val if val else None

    # EDGAR full-text search filtered to 10-K filings. Quoting the ticker forces
    # exact-token matches.
    params = {"q": f'"{key}"', "forms": "10-K"}
    for attempt in range(3):
        try:
            r = _session.get(_SEARCH_URL, params=params, timeout=20)
            if r.status_code == 429:
                time.sleep(2 * (attempt + 1))
                continue
            if r.status_code != 200:
                break
            data = r.json()
            hits = data.get("hits", {}).get("hits", [])
            for hit in hits:
                src = hit.get("_source", {})
                names = src.get("display_names", [])
                ciks = src.get("ciks", [])
                # Match the ticker inside the display_name parentheses
                # ("APPLE INC  (AAPL)  (CIK 0000320193)") to avoid collisions.
                if any(f"({key})" in n for n in names) and ciks:
                    cik10 = str(ciks[0]).zfill(10)
                    _ticker_to_cik[key] = cik10
                    _save_ticker_cache()
                    return cik10
            break
        except Exception:
            time.sleep(1.5 * (attempt + 1))
    # Mark as known-miss so we don't re-query every request.
    _ticker_to_cik[key] = ""
    _save_ticker_cache()
    return None


def _fetch_facts(cik10: str) -> dict | None:
    url = _FACTS_URL.format(cik10=cik10)
    for attempt in range(3):
        try:
            r = _session.get(url, timeout=25)
            if r.status_code == 429:
                time.sleep(2 * (attempt + 1))
                continue
            if r.status_code == 404:
                return None
            r.raise_for_status()
            return r.json()
        except Exception:
            time.sleep(1.5 * (attempt + 1))
    return None


def _extract_quarterly_series(facts: dict, keys: tuple[str, ...]) -> list[dict]:
    """Return [{filed, end, val}] rows for the first matching concept key,
    restricted to standalone quarterly (form=10-Q) filings."""
    us_gaap = facts.get("facts", {}).get("us-gaap", {})
    for key in keys:
        entry = us_gaap.get(key)
        if not entry:
            continue
        units = entry.get("units", {})
        # Pick the USD or USD/shares unit (the first available)
        unit_rows: list[dict] = []
        for u, rows in units.items():
            if "USD" in u.upper():
                unit_rows = rows
                break
        if not unit_rows:
            continue
        out = []
        for row in unit_rows:
            form = row.get("form", "")
            fp = row.get("fp")
            if form != "10-Q":
                continue
            if fp not in ("Q1", "Q2", "Q3"):
                continue
            val = row.get("val")
            filed = row.get("filed")
            end = row.get("end")
            if val is None or not filed or not end:
                continue
            out.append({"filed": filed, "end": end, "val": float(val)})
        if out:
            return out
    return []


def _safe_yoy(curr: float | None, prior: float | None) -> float | None:
    if curr is None or prior is None:
        return None
    if pd.isna(curr) or pd.isna(prior) or prior == 0:
        return None
    return (curr - prior) / abs(prior)


def fetch_fundamentals(ticker: str) -> pd.DataFrame:
    """Return DataFrame indexed by filing date (report_date) with computed growth stats."""
    if is_etf(ticker):
        return pd.DataFrame()
    cik = _cik_for(ticker)
    if cik is None:
        return pd.DataFrame()
    facts = _fetch_facts(cik)
    if facts is None:
        return pd.DataFrame()

    eps_rows = _extract_quarterly_series(facts, EPS_KEYS)
    rev_rows = _extract_quarterly_series(facts, REV_KEYS)

    def _df(rows: list[dict], col: str) -> pd.DataFrame:
        if not rows:
            return pd.DataFrame(columns=["filed", "end", col])
        df = pd.DataFrame(rows)
        df = df.rename(columns={"val": col})
        df["filed"] = pd.to_datetime(df["filed"])
        df["end"] = pd.to_datetime(df["end"])
        # Keep the FIRST filing for each fiscal period end (the initial 10-Q report).
        df = df.sort_values(["end", "filed"]).drop_duplicates(subset=["end"], keep="first")
        return df.reset_index(drop=True)

    eps_df = _df(eps_rows, "eps")
    rev_df = _df(rev_rows, "revenue")

    if eps_df.empty and rev_df.empty:
        return pd.DataFrame()

    merged = pd.merge(
        eps_df[["end", "filed", "eps"]] if not eps_df.empty else pd.DataFrame(columns=["end", "filed", "eps"]),
        rev_df[["end", "filed", "revenue"]] if not rev_df.empty else pd.DataFrame(columns=["end", "filed", "revenue"]),
        on="end",
        how="outer",
        suffixes=("_eps", "_rev"),
    )
    # Announcement date = latest of the two filings (since user only "knows" both after both are out).
    merged["filed"] = merged[["filed_eps", "filed_rev"]].max(axis=1)
    merged = merged.drop(columns=[c for c in ("filed_eps", "filed_rev") if c in merged.columns])
    merged = merged.sort_values("end").reset_index(drop=True)

    # YoY growth by matching each row to the prior-year same quarter by
    # fiscal_period_end (±30 day window). Row-offset matching breaks when Q4
    # is missing (10-Q-only filings), so we match by date.
    ends = pd.to_datetime(merged["end"]).tolist()

    def _match_prior_year(i: int) -> int | None:
        target = ends[i] - pd.Timedelta(days=365)
        best = None
        best_gap = pd.Timedelta(days=31)
        for j in range(i):
            gap = abs(ends[j] - target)
            if gap < best_gap:
                best_gap = gap
                best = j
        return best

    prior_idx = [_match_prior_year(i) for i in range(len(merged))]

    def yoy_for(col: str, i: int) -> float | None:
        if prior_idx[i] is None:
            return None
        curr = merged.iloc[i].get(col)
        prior = merged.iloc[prior_idx[i]].get(col)
        return _safe_yoy(
            None if pd.isna(curr) else float(curr),
            None if pd.isna(prior) else float(prior),
        )

    merged["eps_yoy"] = [yoy_for("eps", i) for i in range(len(merged))]
    merged["rev_yoy"] = [yoy_for("revenue", i) for i in range(len(merged))]

    # Acceleration = change in YoY vs the ROW immediately prior (sequential
    # in-time growth rate change). For sparse data, row-to-row is fine.
    def accel(col_vals, i):
        if i < 1 or col_vals[i] is None or col_vals[i - 1] is None:
            return None
        return col_vals[i] - col_vals[i - 1]

    eps_yoy_l = merged["eps_yoy"].tolist()
    rev_yoy_l = merged["rev_yoy"].tolist()
    merged["eps_accel"] = [accel(eps_yoy_l, i) for i in range(len(merged))]
    merged["rev_accel"] = [accel(rev_yoy_l, i) for i in range(len(merged))]

    def score(row):
        ea = row["eps_accel"]
        ra = row["rev_accel"]
        parts = [x for x in (ea, ra) if x is not None and not pd.isna(x)]
        if not parts:
            return None
        raw = sum(50 * p for p in parts)
        return max(-100.0, min(100.0, raw))

    merged["fund_score"] = merged.apply(score, axis=1)

    merged = merged.rename(columns={"end": "fiscal_period_end", "filed": "report_date"})
    merged = merged.set_index("report_date").sort_index()
    return merged[
        [
            "fiscal_period_end",
            "eps",
            "revenue",
            "eps_yoy",
            "rev_yoy",
            "eps_accel",
            "rev_accel",
            "fund_score",
        ]
    ]


def save_fundamentals(ticker: str, df: pd.DataFrame) -> None:
    if df is None or df.empty:
        return
    conn = _get_conn()
    conn.execute("DELETE FROM fundamentals WHERE ticker = ?", (ticker,))
    records = []
    for report_date, row in df.iterrows():
        records.append(
            (
                ticker,
                str(pd.Timestamp(report_date).date()),
                str(pd.Timestamp(row["fiscal_period_end"]).date()) if pd.notna(row["fiscal_period_end"]) else None,
                None if pd.isna(row["eps"]) else float(row["eps"]),
                None if pd.isna(row["revenue"]) else float(row["revenue"]),
                None if row["eps_yoy"] is None or pd.isna(row["eps_yoy"]) else float(row["eps_yoy"]),
                None if row["rev_yoy"] is None or pd.isna(row["rev_yoy"]) else float(row["rev_yoy"]),
                None if row["eps_accel"] is None or pd.isna(row["eps_accel"]) else float(row["eps_accel"]),
                None if row["rev_accel"] is None or pd.isna(row["rev_accel"]) else float(row["rev_accel"]),
                None if row["fund_score"] is None or pd.isna(row["fund_score"]) else float(row["fund_score"]),
            )
        )
    conn.executemany(
        "INSERT OR REPLACE INTO fundamentals "
        "(ticker, report_date, fiscal_period_end, eps, revenue, eps_yoy, rev_yoy, "
        " eps_accel, rev_accel, fund_score) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        records,
    )
    conn.execute(
        "INSERT OR REPLACE INTO fundamentals_meta (ticker, last_fetched) VALUES (?, ?)",
        (ticker, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()


def load_fundamentals(ticker: str) -> pd.DataFrame | None:
    conn = _get_conn()
    df = pd.read_sql_query(
        "SELECT report_date, eps, revenue, eps_yoy, rev_yoy, eps_accel, rev_accel, fund_score "
        "FROM fundamentals WHERE ticker = ? ORDER BY report_date",
        conn,
        params=(ticker,),
    )
    conn.close()
    if df.empty:
        return None
    df["report_date"] = pd.to_datetime(df["report_date"])
    df = df.set_index("report_date")
    return df


def get_fundamentals(ticker: str, refresh: bool = False) -> pd.DataFrame | None:
    """Return cached fundamentals; fetch on miss. ETFs return None."""
    if is_etf(ticker):
        return None
    if not refresh:
        cached = load_fundamentals(ticker)
        if cached is not None and not cached.empty:
            return cached
    try:
        df = fetch_fundamentals(ticker)
    except Exception as e:
        print(f"[fundamentals] {ticker}: {e}")
        return None
    if df is None or df.empty:
        return None
    save_fundamentals(ticker, df)
    return load_fundamentals(ticker)


def point_in_time_score(fund_df: pd.DataFrame | None, as_of: pd.Timestamp) -> float | None:
    if fund_df is None or fund_df.empty:
        return None
    sliced = fund_df.loc[fund_df.index <= as_of]
    if sliced.empty:
        return None
    val = sliced.iloc[-1]["fund_score"]
    if val is None or pd.isna(val):
        return None
    return float(val)
