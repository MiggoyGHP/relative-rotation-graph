"""Build static JSON snapshots for the Pages deploy.

Writes:
  frontend/public/snapshot/sectors_meta.json   (same shape as GET /api/sectors)
  frontend/public/snapshot/sectors.json        (Sectors-vs-SPY RRG range)
  frontend/public/snapshot/drill-<ETF>.json    (one per sector drill-down)

After running this, the Next.js build with STATIC_EXPORT=1 reads these files
instead of hitting the FastAPI backend.

    python -m scripts.snapshot
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.routes.rrg import _compute_series_for  # noqa: E402
from app.routes.sectors import SECTORS_PATH  # noqa: E402


OUT_DIR = Path(__file__).resolve().parents[2] / "frontend" / "public" / "snapshot"

# Keep in sync with frontend/app/page.tsx MACRO_UNIVERSE.
MACRO_PRESET = {
    "id": "preset-macro",
    "benchmark": "SPY",
    "universe": [
        "USO", "EWY", "XOP", "XLE", "SMH", "COPX", "URA", "XLB", "PBJ", "GLD",
        "XLI", "XBI", "EEM", "EWH", "XLU", "XME", "XLRE", "TAN", "XLP", "XLK",
        "XLC", "XRT", "VNM", "KIE", "XLV", "XLF", "UNG", "KWEB",
    ],
}


def write_json(name: str, payload: dict) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    target = OUT_DIR / f"{name}.json"
    target.write_text(json.dumps(payload, separators=(",", ":")))
    print(f"[snapshot] wrote {target.relative_to(OUT_DIR.parents[2])} ({target.stat().st_size:,} bytes)")


def main() -> None:
    cfg = json.loads(SECTORS_PATH.read_text())
    benchmark = cfg["benchmark"]
    sector_keys = list(cfg["sectors"].keys())

    # sectors_meta: the raw /api/sectors payload (lets the frontend read the
    # holdings map for drill-down labels).
    write_json("sectors_meta", cfg)

    # Sectors preset: full weekly range of 11 ETFs vs SPY.
    print(f"[snapshot] computing Sectors vs {benchmark}...")
    sectors_resp = _compute_series_for(
        tickers=sector_keys,
        benchmark=benchmark,
        n=14,
        start="2016-01-01",
        end=None,
        tail=None,
    )
    write_json("sectors", sectors_resp)

    # One drill-down snapshot per sector.
    for etf, info in cfg["sectors"].items():
        components = info["components"]
        print(f"[snapshot] computing {etf} Components vs {etf}...")
        try:
            resp = _compute_series_for(
                tickers=components,
                benchmark=etf,
                n=14,
                start="2016-01-01",
                end=None,
                tail=None,
            )
            write_json(f"drill-{etf}", resp)
        except Exception as e:
            print(f"[snapshot]   {etf} failed: {e}")

    # Macro rotation preset.
    print(f"[snapshot] computing {MACRO_PRESET['id']} ({len(MACRO_PRESET['universe'])} tickers vs {MACRO_PRESET['benchmark']})...")
    try:
        resp = _compute_series_for(
            tickers=MACRO_PRESET["universe"],
            benchmark=MACRO_PRESET["benchmark"],
            n=14,
            start="2016-01-01",
            end=None,
            tail=None,
        )
        write_json(MACRO_PRESET["id"], resp)
    except Exception as e:
        print(f"[snapshot]   {MACRO_PRESET['id']} failed: {e}")

    print("[snapshot] done")


if __name__ == "__main__":
    main()
