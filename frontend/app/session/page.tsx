"use client";
import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { fetchRRGRange, fetchSectors } from "@/lib/api";
import { useSessionStore } from "@/lib/sessionStore";
import { RRGResponse, RRGSeries, SectorsResponse } from "@/lib/types";
import RRGChart from "@/components/RRGChart";
import TailControls from "@/components/TailControls";
import DateSlider from "@/components/DateSlider";

// Query-string routing (/session?id=X) is unreliable in static export +
// trailingSlash builds — GitHub Pages drops the query on some navigations.
// The store already tracks activeId, so use that as the session pointer.
export default function SessionPage() {
  const router = useRouter();

  const id = useSessionStore((s) => s.activeId) ?? "";
  const session = useSessionStore((s) => s.sessions.find((x) => x.id === id));
  const updateSession = useSessionStore((s) => s.updateSession);
  const createSession = useSessionStore((s) => s.createSession);

  // Guard against showing "Session not found" before Zustand rehydrates
  // localStorage on the client.
  const [hydrated, setHydrated] = useState(false);
  useEffect(() => setHydrated(true), []);

  const [data, setData] = useState<RRGResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sectors, setSectors] = useState<SectorsResponse | null>(null);

  const [showRvolWidth, setShowRvolWidth] = useState(true);
  const [showFundamentalColor, setShowFundamentalColor] = useState(true);
  const [showLabels, setShowLabels] = useState(true);

  useEffect(() => {
    fetchSectors().then(setSectors).catch(() => {});
  }, []);

  useEffect(() => {
    if (!session) return;
    setLoading(true);
    setError(null);
    fetchRRGRange({
      universe: session.universe,
      benchmark: session.benchmark,
      n: session.n,
      start: session.startDate,
      snapshotKey: session.snapshotKey,
    })
      .then((resp) => {
        setData(resp);
        setLoading(false);
      })
      .catch((e) => {
        setError(String(e));
        setLoading(false);
      });
  }, [session?.universe.join(","), session?.benchmark, session?.n, session?.startDate]);

  const allDates = useMemo(() => {
    if (!data) return [] as string[];
    const set = new Set<string>();
    data.series.forEach((s) => s.points.forEach((p) => set.add(p.date)));
    return Array.from(set).sort();
  }, [data]);

  const currentDate = session?.currentDate ?? (allDates.length ? allDates[allDates.length - 1] : null);

  const visibleSeries: RRGSeries[] = useMemo(() => {
    if (!data || !session || !currentDate) return [];
    const endIdx = allDates.indexOf(currentDate);
    if (endIdx < 0) return [];
    const startIdx = Math.max(0, endIdx - session.tail + 1);
    const window = new Set(allDates.slice(startIdx, endIdx + 1));
    return data.series.map((s) => ({
      ...s,
      points: s.points.filter((p) => window.has(p.date)),
    }));
  }, [data, session?.tail, currentDate, allDates]);

  function handleDrillDown(ticker: string) {
    if (!sectors) return;
    const sec = sectors.sectors[ticker];
    if (!sec) return;
    createSession({
      title: `${ticker} Components`,
      universe: sec.components,
      benchmark: ticker,
      n: session?.n ?? 14,
      tail: session?.tail ?? 8,
      startDate: session?.startDate ?? "2016-01-01",
      currentDate: null,
    });
    router.push(`/session`);
  }

  if (!hydrated) {
    return <div className="max-w-4xl mx-auto text-center text-gray-400 py-20">Loading session…</div>;
  }

  if (!session) {
    return (
      <div className="max-w-4xl mx-auto text-center text-gray-400 py-20">
        Session not found. <a href="./" className="text-blue-400 underline">Go home</a>.
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto space-y-4">
      <div className="flex items-baseline justify-between">
        <div>
          <h2 className="text-xl font-semibold">{session.title}</h2>
          <div className="text-sm text-gray-400">
            {session.universe.length} tickers vs <span className="font-mono text-gray-200">{session.benchmark}</span>
            {" · weekly · n="}{session.n}
          </div>
        </div>
        {loading && <div className="text-sm text-blue-400">loading weekly bars…</div>}
      </div>

      {error && (
        <div className="p-4 bg-red-900/30 border border-red-800 rounded text-red-300 text-sm">{error}</div>
      )}

      <TailControls
        tail={session.tail}
        onTailChange={(v) => updateSession(session.id, { tail: v })}
        n={session.n}
        onNChange={(v) => updateSession(session.id, { n: v })}
        showRvolWidth={showRvolWidth}
        onRvolToggle={setShowRvolWidth}
        showFundamentalColor={showFundamentalColor}
        onFundamentalToggle={setShowFundamentalColor}
        showLabels={showLabels}
        onLabelsToggle={setShowLabels}
      />

      {data && visibleSeries.length > 0 && (
        <RRGChart
          series={visibleSeries}
          benchmark={session.benchmark}
          showRvolWidth={showRvolWidth}
          showFundamentalColor={showFundamentalColor}
          showLabels={showLabels}
          onTickerClick={handleDrillDown}
        />
      )}

      {allDates.length > 0 && (
        <DateSlider
          dates={allDates}
          currentDate={currentDate}
          onChange={(d) => updateSession(session.id, { currentDate: d })}
        />
      )}

      <div className="flex items-center gap-4 text-xs text-gray-500">
        <span>Click a ticker to drill down (sectors only)</span>
        <span>·</span>
        <span>Tail width = RVOL · Color = EPS+Rev acceleration (Red→Green) · Gray = ETF or missing</span>
      </div>
    </div>
  );
}
