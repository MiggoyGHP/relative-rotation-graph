from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import history, rrg, sectors, watchlist

app = FastAPI(title="RRG Backend", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sectors.router)
app.include_router(rrg.router)
app.include_router(watchlist.router)
app.include_router(history.router)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}
