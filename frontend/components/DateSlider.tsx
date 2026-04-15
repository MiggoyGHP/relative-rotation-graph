"use client";
import { useEffect, useRef, useState } from "react";

interface Props {
  dates: string[];
  currentDate: string | null;
  onChange: (date: string) => void;
}

export default function DateSlider({ dates, currentDate, onChange }: Props) {
  const [playing, setPlaying] = useState(false);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  const currentIdx = currentDate ? Math.max(0, dates.indexOf(currentDate)) : dates.length - 1;

  useEffect(() => {
    if (!playing) {
      if (timer.current) clearInterval(timer.current);
      timer.current = null;
      return;
    }
    timer.current = setInterval(() => {
      const next = currentIdx + 1;
      if (next >= dates.length) {
        setPlaying(false);
        return;
      }
      onChange(dates[next]);
    }, 180);
    return () => {
      if (timer.current) clearInterval(timer.current);
    };
  }, [playing, currentIdx, dates, onChange]);

  if (dates.length === 0) return null;

  return (
    <div className="flex items-center gap-3 p-3 bg-gray-900/60 border border-gray-800 rounded-lg">
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
      >
        ⏮
      </button>
      <button
        onClick={() => {
          setPlaying(false);
          onChange(dates[dates.length - 1]);
        }}
        className="px-2 py-1 bg-gray-700 hover:bg-gray-600 rounded text-gray-100 text-xs"
      >
        ⏭
      </button>
      <input
        type="range"
        min={0}
        max={dates.length - 1}
        value={currentIdx}
        onChange={(e) => {
          setPlaying(false);
          onChange(dates[parseInt(e.target.value)]);
        }}
        className="flex-1 accent-blue-500"
      />
      <span className="w-24 text-right text-gray-300 text-sm tabular-nums">
        {dates[currentIdx]}
      </span>
    </div>
  );
}
