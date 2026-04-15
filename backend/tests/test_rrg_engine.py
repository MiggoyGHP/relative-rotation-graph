from __future__ import annotations

import numpy as np
import pandas as pd

from app.services.rrg_engine import (
    classify_quadrant,
    compute_rrg_series,
    jdk_rs_momentum,
    jdk_rs_ratio,
    rs_line,
)
from app.services.volume import clip_rvol, weekly_rvol


def _mk_series(values, start="2016-01-08", freq="W-FRI"):
    idx = pd.date_range(start=start, periods=len(values), freq=freq)
    return pd.Series(values, index=idx, dtype=float)


def test_rs_line_identity():
    s = _mk_series(np.linspace(100, 200, 100))
    rs = rs_line(s, s)
    # Identity: ticker/benchmark = 1.0 everywhere.
    assert np.allclose(rs.values, 1.0)


def test_identical_series_yield_neutral_ratio():
    s = _mk_series(np.linspace(100, 200, 100))
    rrg = compute_rrg_series(s, s, n=14)
    # RS is constant → std=0 → NaN; dropna gives empty frame or all NaN.
    # Downstream API drops NaN points, which is the intended behavior.
    assert rrg["rs_ratio"].dropna().empty or np.allclose(
        rrg["rs_ratio"].dropna(), 100, atol=0.01
    )


def test_constant_outperformer_ratio_trends_above_100():
    n = 60
    bench = _mk_series(np.linspace(100, 110, n))                   # slow climb
    tkr = _mk_series(np.linspace(100, 100 * 1.5, n))               # fast climb
    rrg = compute_rrg_series(tkr, bench, n=14)
    later = rrg["rs_ratio"].dropna().iloc[-10:]
    assert (later > 100).mean() >= 0.7, f"expected mostly >100, got {later.tolist()}"


def test_classify_quadrant():
    assert classify_quadrant(101, 101) == "Leading"
    assert classify_quadrant(101, 99) == "Weakening"
    assert classify_quadrant(99, 99) == "Lagging"
    assert classify_quadrant(99, 101) == "Improving"
    assert classify_quadrant(float("nan"), 101) == "Unknown"


def test_rvol_basic():
    # 20 weeks of flat vol then one spike. Trailing mean excludes current bar,
    # so rvol[-1] = 2.5M / 1.0M = 2.5 exactly.
    v = _mk_series([1_000_000] * 20 + [2_500_000])
    rvol = weekly_rvol(v, n=20)
    assert np.isclose(rvol.iloc[-1], 2.5, atol=0.001)
    # First 20 bars are NaN (need 20 prior bars before the window fills).
    assert rvol.iloc[:20].isna().all()


def test_rvol_clip():
    s = _mk_series([0.1, 0.5, 1.0, 2.0, 10.0])
    clipped = clip_rvol(s, 0.3, 4.0)
    assert clipped.iloc[0] == 0.3
    assert clipped.iloc[-1] == 4.0
    assert clipped.iloc[2] == 1.0
