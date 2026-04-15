import { RRGResponse, SectorsResponse } from "./types";

const LIVE_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";
const BASE_PATH = process.env.NEXT_PUBLIC_BASE_PATH ?? "";
const STATIC_MODE = process.env.NEXT_PUBLIC_STATIC_MODE === "1";

function snapshotUrl(name: string): string {
  return `${BASE_PATH}/snapshot/${name}.json`;
}

async function getLive<T>(path: string, params?: Record<string, string | number>): Promise<T> {
  const url = new URL(LIVE_BASE + path);
  if (params) {
    for (const [k, v] of Object.entries(params)) url.searchParams.set(k, String(v));
  }
  const res = await fetch(url.toString(), { cache: "no-store" });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`API ${path} ${res.status}: ${body}`);
  }
  return res.json();
}

async function getStatic<T>(name: string): Promise<T> {
  const res = await fetch(snapshotUrl(name), { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`snapshot ${name} ${res.status}`);
  }
  return res.json();
}

function snapshotKeyFor(universe: string[], benchmark: string): string {
  // Deterministic key: "sectors" for the sector preset, "drill-XLK" for a sector
  // drill-down, otherwise hash-free "wl-<sorted>" which we simply don't ship.
  const sortedUniverse = [...universe].sort().join(",");
  if (benchmark === "SPY" && sortedUniverse === ["XLK","XLC","XLY","XLP","XLE","XLF","XLV","XLI","XLB","XLRE","XLU"].sort().join(",")) {
    return "sectors";
  }
  // Sector drill-down: universe doesn't contain the benchmark and benchmark is a known sector ETF.
  const sectorEtfs = new Set(["XLK","XLC","XLE","XLF","XLI","XLV","XLU","XLP","XLY","XLRE","XLB"]);
  if (sectorEtfs.has(benchmark)) return `drill-${benchmark}`;
  return `wl-${benchmark}-${sortedUniverse}`;
}

export function fetchSectors(): Promise<SectorsResponse> {
  if (STATIC_MODE) return getStatic<SectorsResponse>("sectors_meta");
  return getLive<SectorsResponse>("/api/sectors");
}

export function fetchRRG(opts: {
  universe: string[];
  benchmark: string;
  n?: number;
  tail?: number;
  end?: string | null;
  start?: string;
}): Promise<RRGResponse> {
  if (STATIC_MODE) return getStatic<RRGResponse>(snapshotKeyFor(opts.universe, opts.benchmark));
  const params: Record<string, string | number> = {
    universe: opts.universe.join(","),
    benchmark: opts.benchmark,
    n: opts.n ?? 14,
    tail: opts.tail ?? 10,
    start: opts.start ?? "2016-01-01",
  };
  if (opts.end) params.end = opts.end;
  return getLive<RRGResponse>("/api/rrg", params);
}

export function fetchRRGRange(opts: {
  universe: string[];
  benchmark: string;
  n?: number;
  start?: string;
  end?: string | null;
}): Promise<RRGResponse> {
  if (STATIC_MODE) return getStatic<RRGResponse>(snapshotKeyFor(opts.universe, opts.benchmark));
  const params: Record<string, string | number> = {
    universe: opts.universe.join(","),
    benchmark: opts.benchmark,
    n: opts.n ?? 14,
    start: opts.start ?? "2016-01-01",
  };
  if (opts.end) params.end = opts.end;
  return getLive<RRGResponse>("/api/rrg/range", params);
}

export async function uploadWatchlist(file: File): Promise<{ tickers: string[]; skipped: string[]; count: number }> {
  if (STATIC_MODE) {
    throw new Error("Watchlist upload is disabled in the static build. Run the backend locally to enable it.");
  }
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(LIVE_BASE + "/api/watchlist/parse", { method: "POST", body: form });
  if (!res.ok) throw new Error(`watchlist parse failed: ${res.status}`);
  return res.json();
}

export const IS_STATIC_MODE = STATIC_MODE;
