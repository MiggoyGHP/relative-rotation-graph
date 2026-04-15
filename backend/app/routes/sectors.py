from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter

router = APIRouter()

SECTORS_PATH = Path(__file__).resolve().parents[1] / "config" / "sectors.json"


@router.get("/api/sectors")
def get_sectors() -> dict:
    with SECTORS_PATH.open() as f:
        return json.load(f)
