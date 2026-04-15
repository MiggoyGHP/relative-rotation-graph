"use client";
import { useState } from "react";
import { uploadWatchlist } from "@/lib/api";

interface Props {
  onParsed: (tickers: string[]) => void;
}

export default function WatchlistUploader({ onParsed }: Props) {
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleFile(file: File) {
    setError(null);
    setStatus("Parsing…");
    try {
      const res = await uploadWatchlist(file);
      setStatus(`Parsed ${res.count} tickers${res.skipped.length ? ` (skipped ${res.skipped.length})` : ""}`);
      onParsed(res.tickers);
    } catch (e) {
      setError(String(e));
      setStatus(null);
    }
  }

  return (
    <div className="p-6 border-2 border-dashed border-gray-700 rounded-lg bg-gray-900/40">
      <label className="cursor-pointer block text-center">
        <input
          type="file"
          accept=".txt,.csv"
          className="hidden"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) handleFile(f);
          }}
        />
        <span className="text-gray-200 font-medium">Click or drop a TradingView export</span>
        <div className="text-xs text-gray-500 mt-1">.txt or .csv — one symbol per line, or comma-separated</div>
      </label>
      {status && <div className="mt-3 text-sm text-green-400">{status}</div>}
      {error && <div className="mt-3 text-sm text-red-400">{error}</div>}
    </div>
  );
}
