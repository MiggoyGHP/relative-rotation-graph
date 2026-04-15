from __future__ import annotations

import numpy as np
import pandas as pd


def weekly_rvol(weekly_volume: pd.Series, n: int = 20) -> pd.Series:
    """Relative volume: weekly volume divided by trailing n-week mean.

    1.0 = average, 2.0 = double normal participation. NaN for the first n-1 bars.
    """
    if weekly_volume is None or weekly_volume.empty:
        return pd.Series(dtype=float)
    # Trailing mean EXCLUDING the current bar, so a single-week spike isn't
    # diluted by itself in the denominator.
    mean = weekly_volume.shift(1).rolling(n).mean()
    rvol = weekly_volume / mean.replace(0, np.nan)
    return rvol


def clip_rvol(rvol: pd.Series, lo: float = 0.3, hi: float = 4.0) -> pd.Series:
    """Clip RVOL to a stable display range; preserves NaNs."""
    return rvol.clip(lower=lo, upper=hi)
