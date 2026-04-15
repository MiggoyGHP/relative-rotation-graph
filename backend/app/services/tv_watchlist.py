from __future__ import annotations


def parse_tv_watchlist(text: str) -> tuple[list[str], list[str]]:
    """Parse a TradingView watchlist export.

    Supports two shapes:
      1. Newline-separated: "NASDAQ:AAPL\\nNYSE:BA\\n###Section\\nMSFT"
      2. Comma-separated (flat list export): "NASDAQ:AAPL,NYSE:BA,###Section,MSFT"

    Returns (tickers, skipped) where tickers are de-duped symbols (no exchange
    prefix) in original order, and skipped contains entries we rejected.
    """
    if not text:
        return [], []

    # Normalize: split on either newlines OR commas.
    raw_tokens: list[str] = []
    for line in text.splitlines():
        if not line.strip():
            continue
        if "," in line and ":" in line and line.count(",") > line.count("\n"):
            raw_tokens.extend(p.strip() for p in line.split(","))
        else:
            raw_tokens.append(line.strip())

    tickers: list[str] = []
    skipped: list[str] = []
    seen: set[str] = set()

    for tok in raw_tokens:
        tok = tok.strip()
        if not tok:
            continue
        if tok.startswith("###") or tok.startswith("#"):
            continue  # section header
        sym = tok.split(":", 1)[1] if ":" in tok else tok
        sym = sym.strip().upper()
        # Strip trailing junk
        sym = sym.split()[0] if sym else sym
        if not sym or not sym.replace(".", "").replace("-", "").isalnum():
            skipped.append(tok)
            continue
        if sym in seen:
            continue
        seen.add(sym)
        tickers.append(sym)

    return tickers, skipped
