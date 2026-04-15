"use client";
import { useEffect, useRef, useState } from "react";

interface Props {
  dates: string[];
  currentDate: string | null;
  onChange: (date: string) => void;
}

// Base interval between frames at 1× speed (ms/bar). Chosen so a 500-week
// replay takes ~5 minutes at 1× and is comfortably readable.
const BASE_INTERVAL_MS = 600;

const SPEEDS: { label: string; value: number }[] = [
  { label: "0.25×", value: 0.25 },
  { label: "0.5×", value: 0.5 },
  { label: "1×", value: 1 },
  { label: "2×", value: 2 },
  { label: "4×", value: 4 },
  { label: "8×", value: 8 },
];

export default function DateSlider({ dates, currentDate, onChange }: Props) {
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);
  // Refs avoid re-creating the interval on every tick (which would add React
  // render latency per frame and make speed ~3x slower than configured).
  const idxRef = useRef(0);
  const onChangeRef = useRef(onChange);
  const datesRef = useRef(dates);

  const currentIdx = currentDate ? Math.max(0, dates.indexOf(currentDate)) : dates.length - 1;

  // Keep refs fresh without invalidating the playback effect.
  useEffect(() => { idxRef.current = currentIdx; }, [currentIdx]);
  useEffect(() => { onChangeRef.current = onChange; }, [onChange]);
  useEffect(() => { datesRef.current = dates; }, [dates]);

  useEffect(() => {
    if (!playing) {
      if (timer.current) clearInterval(timer.current);
      timer.current = null;
      return;
    }
    const intervalMs = Math.max(30, BASE_INTERVAL_MS / speed);
    timer.current = setInterval(() => {
      const next = idxRef.current + 1;
      const d = datesRef.current;
      if (next >= d.length) {
        setPlaying(false);
        return;
      }
      idxRef.current = next;
      onChangeRef.current(d[next]);
    }, intervalMs);
    return () => {
      if (timer.current) clearInterval(timer.current);
    };
  }, [playing, speed]);

  if (dates.length === 0) return null;

  return (
    <div className="flex flex-wrap items-center gap-3 p-3 bg-gray-900/60 border border-gray-800 rounded-lg">
      <button
        onClick={() => setPlaying((p) => !p)}
        className="px-3 py-1 bg-blue-600 hover:bg-blue-500 rounded text-white text-sm font-medium"
      >
        {playing ? "Pause" : "Play"}
      </button>
      <button
        onClick={() => {
          setPlaying(false);
          onChange(dates[0]);
        }}
        className="px-2 py-1 bg-gray-700 hover:bg-gray-600 rounded text-gray-100 text-xs"
        aria-label="Jump to start"
        title="Jump to start"
      >
        ⏮
      </button>
      <button
        onClick={() => {
          setPlaying(false);
          onChange(dates[dates.length - 1]);
        }}
        className="px-2 py-1 bg-gray-700 hover:bg-gray-600 rounded text-gray-100 text-xs"
        aria-label="Jump to end"
        title="Jump to end"
      >
        ⏭
      </button>

      <div className="flex items-center gap-1" role="group" aria-label="Playback speed">
        {SPEEDS.map((s) => (
          <button
            key={s.value}
            onClick={() => setSpeed(s.value)}
            className={`px-2 py-1 text-xs rounded tabular-nums ${
              speed === s.value
                ? "bg-blue-600 text-white"
                : "bg-gray-800 text-gray-300 hover:bg-gray-700"
            }`}
          >
            {s.label}
          </button>
        ))}
      </div>

      <input
        type="range"
        min={0}
        max={dates.length - 1}
        value={currentIdx}
        onChange={(e) => {
          setPlaying(false);
          onChange(dates[parseInt(e.target.value)]);
        }}
        className="flex-1 min-w-40 accent-blue-500"
      />
      <span className="w-24 text-right text-gray-300 text-sm tabular-nums">
        {dates[currentIdx]}
      </span>
    </div>
  );
}
