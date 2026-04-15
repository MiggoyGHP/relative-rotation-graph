from __future__ import annotations

import numpy as np
import pandas as pd


def rs_line(ticker_close: pd.Series, benchmark_close: pd.Series) -> pd.Series:
    """Raw relative strength: ticker / benchmark, aligned on dates."""
    df = pd.concat([ticker_close, benchmark_close], axis=1, join="inner").dropna()
    if df.empty:
        return pd.Series(dtype=float)
    return df.iloc[:, 0] / df.iloc[:, 1]


def jdk_rs_ratio(rs: pd.Series, n: int = 14) -> pd.Series:
    """JdK RS-Ratio: rolling z-score of RS line, shifted to center at 100."""
    mean = rs.rolling(n).mean()
    std = rs.rolling(n).std(ddof=0)
    z = (rs - mean) / std.replace(0, np.nan)
    return 100 + z


def jdk_rs_momentum(rs_ratio: pd.Series, n: int = 14) -> pd.Series:
    """JdK RS-Momentum: rolling z-score of RS-Ratio ROC, shifted to 100."""
    roc = rs_ratio.diff()
    mean = roc.rolling(n).mean()
    std = roc.rolling(n).std(ddof=0)
    z = (roc - mean) / std.replace(0, np.nan)
    return 100 + z


def classify_quadrant(rs_ratio: float, rs_mom: float) -> str:
    if pd.isna(rs_ratio) or pd.isna(rs_mom):
        return "Unknown"
    if rs_ratio >= 100 and rs_mom >= 100:
        return "Leading"
    if rs_ratio >= 100 and rs_mom < 100:
        return "Weakening"
    if rs_ratio < 100 and rs_mom < 100:
        return "Lagging"
    return "Improving"


def compute_rrg_series(
    ticker_close: pd.Series,
    benchmark_close: pd.Series,
    n: int = 14,
) -> pd.DataFrame:
    """Full RRG time series for one ticker vs benchmark.

    Returns DataFrame indexed by date with columns: rs_ratio, rs_momentum, quadrant.
    """
    rs = rs_line(ticker_close, benchmark_close)
    if rs.empty:
        return pd.DataFrame(columns=["rs_ratio", "rs_momentum", "quadrant"])
    ratio = jdk_rs_ratio(rs, n=n)
    mom = jdk_rs_momentum(ratio, n=n)
    out = pd.DataFrame({"rs_ratio": ratio, "rs_momentum": mom})
    out["quadrant"] = [
        classify_quadrant(r, m) for r, m in zip(out["rs_ratio"], out["rs_momentum"])
    ]
    return out
