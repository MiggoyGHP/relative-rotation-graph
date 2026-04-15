"use client";

interface Props {
  tail: number;
  onTailChange: (n: number) => void;
  n: number;
  onNChange: (n: number) => void;
  showRvolWidth: boolean;
  onRvolToggle: (v: boolean) => void;
  showFundamentalColor: boolean;
  onFundamentalToggle: (v: boolean) => void;
  showLabels: boolean;
  onLabelsToggle: (v: boolean) => void;
}

export default function TailControls({
  tail,
  onTailChange,
  n,
  onNChange,
  showRvolWidth,
  onRvolToggle,
  showFundamentalColor,
  onFundamentalToggle,
  showLabels,
  onLabelsToggle,
}: Props) {
  return (
    <div className="flex flex-wrap items-center gap-6 p-4 bg-gray-900/60 rounded-lg border border-gray-800 text-sm">
      <label className="flex items-center gap-2">
        <span className="text-gray-400">Tail</span>
        <input
          type="range"
          min={1}
          max={20}
          value={tail}
          onChange={(e) => onTailChange(parseInt(e.target.value))}
          className="w-28 accent-blue-500"
        />
        <span className="w-8 text-right text-gray-200 tabular-nums">{tail}</span>
      </label>

      <label className="flex items-center gap-2">
        <span className="text-gray-400">n (lookback)</span>
        <input
          type="range"
          min={4}
          max={26}
          value={n}
          onChange={(e) => onNChange(parseInt(e.target.value))}
          className="w-24 accent-blue-500"
        />
        <span className="w-8 text-right text-gray-200 tabular-nums">{n}</span>
      </label>

      <label className="flex items-center gap-2 cursor-pointer">
        <input
          type="checkbox"
          checked={showRvolWidth}
          onChange={(e) => onRvolToggle(e.target.checked)}
          className="accent-blue-500 h-4 w-4"
        />
        <span className="text-gray-200">RVOL width</span>
      </label>

      <label className="flex items-center gap-2 cursor-pointer">
        <input
          type="checkbox"
          checked={showFundamentalColor}
          onChange={(e) => onFundamentalToggle(e.target.checked)}
          className="accent-blue-500 h-4 w-4"
        />
        <span className="text-gray-200">Fundamental color</span>
      </label>

      <label className="flex items-center gap-2 cursor-pointer">
        <input
          type="checkbox"
          checked={showLabels}
          onChange={(e) => onLabelsToggle(e.target.checked)}
          className="accent-blue-500 h-4 w-4"
        />
        <span className="text-gray-200">Labels</span>
      </label>
    </div>
  );
}
