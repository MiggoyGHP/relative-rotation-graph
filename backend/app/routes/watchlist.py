from __future__ import annotations

from fastapi import APIRouter, File, UploadFile

from app.services.tv_watchlist import parse_tv_watchlist

router = APIRouter()


@router.post("/api/watchlist/parse")
async def parse_watchlist(file: UploadFile = File(...)) -> dict:
    raw = await file.read()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")
    tickers, skipped = parse_tv_watchlist(text)
    return {"tickers": tickers, "skipped": skipped, "count": len(tickers)}
