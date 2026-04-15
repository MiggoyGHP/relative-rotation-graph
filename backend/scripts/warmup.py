"""Prime the SQLite cache with weekly OHLC + fundamentals for the default universe.

Run once after install; re-run weekly to refresh.

    python -m scripts.warmup
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.cache import get_weekly_batch  # noqa: E402
from app.services.fundamentals import get_fundamentals, is_etf  # noqa: E402


def main() -> None:
    sectors_path = Path(__file__).resolve().parents[1] / "app" / "config" / "sectors.json"
    cfg = json.loads(sectors_path.read_text())

    tickers: list[str] = [cfg["benchmark"]]
    tickers.extend(cfg["sectors"].keys())
    for s in cfg["sectors"].values():
        tickers.extend(s["components"])

    # De-dupe preserving order
    seen: set[str] = set()
    unique = []
    for t in tickers:
        if t not in seen:
            seen.add(t)
            unique.append(t)

    print(f"[warmup] fetching weekly bars for {len(unique)} tickers...")
    data = get_weekly_batch(unique, start="2016-01-01", refresh=True)
    print(f"[warmup] cached weekly bars for {len(data)}/{len(unique)} tickers")

    stocks = [t for t in unique if not is_etf(t)]
    print(f"[warmup] fetching fundamentals for {len(stocks)} stocks...")
    ok = 0
    for t in stocks:
        try:
            df = get_fundamentals(t, refresh=True)
            if df is not None and not df.empty:
                ok += 1
        except Exception as e:
            print(f"[warmup]   {t}: {e}")
    print(f"[warmup] cached fundamentals for {ok}/{len(stocks)} stocks")
    print("[warmup] done")


if __name__ == "__main__":
    main()
