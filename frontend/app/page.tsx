"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { fetchSectors, IS_STATIC_MODE } from "@/lib/api";
import { useSessionStore } from "@/lib/sessionStore";
import WatchlistUploader from "@/components/WatchlistUploader";
import { SectorsResponse } from "@/lib/types";

export default function HomePage() {
  const router = useRouter();
  const createSession = useSessionStore((s) => s.createSession);
  const updateSession = useSessionStore((s) => s.updateSession);
  const setActive = useSessionStore((s) => s.setActive);
  const sessions = useSessionStore((s) => s.sessions);
  const [sectors, setSectors] = useState<SectorsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [wlTickers, setWlTickers] = useState<string[]>([]);
  const [wlBenchmark, setWlBenchmark] = useState("SPY");
  const [wlTitle, setWlTitle] = useState("Custom watchlist");

  // Hand-curated macro rotation watchlist (USOIL/XAUUSD normalized to USO/GLD,
  // SPY removed since it's the benchmark). Baked into the static snapshot.
  const MACRO_UNIVERSE = [
    "USO","EWY","XOP","XLE","SMH","COPX","URA","XLB","PBJ","GLD",
    "XLI","XBI","EEM","EWH","XLU","XME","XLRE","TAN","XLP","XLK",
    "XLC","XRT","VNM","KIE","XLV","XLF","UNG","KWEB","IBIT","ETHA",
  ];

  useEffect(() => {
    fetchSectors()
      .then(setSectors)
      .catch((e) => setError(String(e)));
  }, []);

  function launchSectors() {
    if (!sectors) return;
    const id = createSession({
      title: "Sectors vs SPY",
      universe: Object.keys(sectors.sectors),
      benchmark: sectors.benchmark,
      n: 14,
      tail: 8,
      startDate: "2016-01-01",
      currentDate: null,
    });
    router.push(`/session?id=${id}`);
  }

  function launchMacro() {
    const existing = sessions.find((s) => s.snapshotKey === "preset-macro");
    if (existing) {
      updateSession(existing.id, { universe: MACRO_UNIVERSE, benchmark: "SPY" });
      setActive(existing.id);
      router.push(`/session?id=${existing.id}`);
      return;
    }
    const id = createSession({
      title: "Macro rotation",
      universe: MACRO_UNIVERSE,
      benchmark: "SPY",
      n: 14,
      tail: 8,
      startDate: "2016-01-01",
      currentDate: null,
      snapshotKey: "preset-macro",
    });
    router.push(`/session?id=${id}`);
  }

  function launchWatchlist() {
    if (wlTickers.length === 0) return;
    const id = createSession({
      title: wlTitle || "Custom watchlist",
      universe: wlTickers,
      benchmark: wlBenchmark.toUpperCase().trim() || "SPY",
      n: 14,
      tail: 8,
      startDate: "2016-01-01",
      currentDate: null,
    });
    router.push(`/session?id=${id}`);
  }

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      <section className="bg-gray-900/60 border border-gray-800 rounded-lg p-6">
        <h2 className="text-lg font-semibold mb-2">Preset: SPDR Sectors vs SPY</h2>
        <p className="text-gray-400 text-sm mb-4">
          11 sector ETFs vs SPY, weekly, JdK normalized with n=14. Click any sector in the chart to
          drill into its top holdings.
        </p>
        <button
          onClick={launchSectors}
          disabled={!sectors}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 rounded text-white font-medium"
        >
          {sectors ? "Launch Sectors session" : "Loading sectors…"}
        </button>
        {error && <div className="mt-3 text-red-400 text-sm">{error}</div>}
      </section>

      <section className="bg-gray-900/60 border border-gray-800 rounded-lg p-6">
        <h2 className="text-lg font-semibold mb-2">Preset: Macro rotation watchlist vs SPY</h2>
        <p className="text-gray-400 text-sm mb-4">
          30 macro/thematic ETFs spanning energy (USO, XOP, XLE, XME, COPX, URA, UNG),
          metals (GLD), crypto (IBIT, ETHA), regions (EWY, EEM, EWH, VNM, KWEB),
          US sectors (XLK, XLF, XLV, XLI, …), and themes (SMH, XBI, TAN, KIE, PBJ, XRT) vs SPY.
        </p>
        <div className="bg-gray-950 border border-gray-800 rounded p-2 mb-4 text-gray-400 font-mono text-xs leading-relaxed">
          {MACRO_UNIVERSE.join(", ")}
        </div>
        <button
          onClick={launchMacro}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded text-white font-medium"
        >
          Launch Macro rotation session
        </button>
      </section>

      <section className="bg-gray-900/60 border border-gray-800 rounded-lg p-6 space-y-4">
        <h2 className="text-lg font-semibold">Custom watchlist</h2>
        {IS_STATIC_MODE ? (
          <div className="text-sm text-gray-400 bg-gray-950/50 border border-gray-800 rounded p-3">
            Watchlist upload is disabled in the static GitHub Pages build (no backend).
            Clone the repo and run <span className="font-mono text-gray-300">npm run dev</span> locally to use it.
          </div>
        ) : (
          <WatchlistUploader onParsed={setWlTickers} />
        )}

        {wlTickers.length > 0 && (
          <>
            <div className="text-sm">
              <div className="text-gray-400 mb-1">Parsed {wlTickers.length} tickers:</div>
              <div className="bg-gray-950 border border-gray-800 rounded p-2 max-h-28 overflow-y-auto text-gray-200 font-mono text-xs">
                {wlTickers.join(", ")}
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <label className="flex items-center gap-2 text-sm">
                <span className="text-gray-400">Benchmark</span>
                <input
                  value={wlBenchmark}
                  onChange={(e) => setWlBenchmark(e.target.value)}
                  className="bg-gray-900 border border-gray-700 px-2 py-1 rounded w-24 font-mono"
                />
              </label>
              <label className="flex items-center gap-2 text-sm flex-1 min-w-40">
                <span className="text-gray-400">Title</span>
                <input
                  value={wlTitle}
                  onChange={(e) => setWlTitle(e.target.value)}
                  className="bg-gray-900 border border-gray-700 px-2 py-1 rounded flex-1"
                />
              </label>
              <button
                onClick={launchWatchlist}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded text-white font-medium"
              >
                Launch session
              </button>
            </div>
          </>
        )}
      </section>
    </div>
  );
}
