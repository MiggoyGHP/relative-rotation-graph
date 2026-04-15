"use client";
import dynamic from "next/dynamic";
import { useMemo } from "react";
import { interpolateRdYlGn } from "d3-scale-chromatic";
import { RRGSeries } from "@/lib/types";

// Plotly is client-only.
const Plot = dynamic(() => import("react-plotly.js"), { ssr: false });

interface Props {
  series: RRGSeries[];
  benchmark: string;
  showRvolWidth: boolean;
  showFundamentalColor: boolean;
  showLabels: boolean;
  onTickerClick?: (ticker: string) => void;
  height?: number;
}

const NEUTRAL = "#6b7280";
const CATEGORICAL = [
  "#2563eb", "#dc2626", "#16a34a", "#ea580c", "#9333ea",
  "#0891b2", "#db2777", "#65a30d", "#7c3aed", "#f59e0b",
  "#0d9488",
];

function mapRange(v: number | null | undefined, inLo: number, inHi: number, outLo: number, outHi: number): number {
  if (v == null || !Number.isFinite(v)) return (outLo + outHi) / 2;
  const clamped = Math.max(inLo, Math.min(inHi, v));
  return outLo + ((clamped - inLo) / (inHi - inLo)) * (outHi - outLo);
}

function colorFor(fund: number | null | undefined): string {
  if (fund == null || !Number.isFinite(fund)) return NEUTRAL;
  const t = (fund + 100) / 200; // -100..100 → 0..1
  return interpolateRdYlGn(Math.max(0, Math.min(1, t)));
}

export default function RRGChart({
  series,
  benchmark,
  showRvolWidth,
  showFundamentalColor,
  showLabels,
  onTickerClick,
  height = 680,
}: Props) {
  const { traces, range } = useMemo(() => {
    const traces: any[] = [];

    let minX = 100, maxX = 100, minY = 100, maxY = 100;

    series.forEach((s, sIdx) => {
      const pts = s.points.filter((p) => p.rs_ratio != null && p.rs_momentum != null);
      if (pts.length === 0) return;

      const tickerColor = CATEGORICAL[sIdx % CATEGORICAL.length];

      // Per-segment tail traces — one short line per consecutive pair.
      for (let i = 1; i < pts.length; i++) {
        const a = pts[i - 1];
        const b = pts[i];
        const rvolMid = ((a.rvol ?? 1) + (b.rvol ?? 1)) / 2;
        const width = showRvolWidth ? mapRange(rvolMid, 0.5, 3.0, 1.5, 9) : 2;
        const opacity = showRvolWidth ? mapRange(rvolMid, 0.5, 3.0, 0.35, 1) : 0.85;
        const color = showFundamentalColor ? colorFor(b.fund_score) : tickerColor;

        traces.push({
          x: [a.rs_ratio, b.rs_ratio],
          y: [a.rs_momentum, b.rs_momentum],
          type: "scatter",
          mode: "lines",
          line: { width, color },
          opacity,
          hoverinfo: "skip",
          showlegend: false,
          legendgroup: s.ticker,
        });

        minX = Math.min(minX, a.rs_ratio!, b.rs_ratio!);
        maxX = Math.max(maxX, a.rs_ratio!, b.rs_ratio!);
        minY = Math.min(minY, a.rs_momentum!, b.rs_momentum!);
        maxY = Math.max(maxY, a.rs_momentum!, b.rs_momentum!);
      }

      // Head marker — labeled, legend-visible entry.
      const head = pts[pts.length - 1];
      const headFundColor = showFundamentalColor ? colorFor(head.fund_score) : tickerColor;
      const headSize = showRvolWidth ? mapRange(head.rvol, 0.5, 3.0, 11, 22) : 14;

      traces.push({
        x: [head.rs_ratio],
        y: [head.rs_momentum],
        type: "scatter",
        mode: showLabels ? "markers+text" : "markers",
        marker: {
          size: headSize,
          color: headFundColor,
          line: { color: "#111827", width: 1.5 },
        },
        text: showLabels ? [s.ticker] : undefined,
        textposition: "top center",
        textfont: { color: "#f3f4f6", size: 12, family: "Inter, sans-serif" },
        name: s.ticker,
        legendgroup: s.ticker,
        showlegend: true,
        customdata: [[s.ticker, head.quadrant, head.date, head.rvol, head.fund_score]],
        hovertemplate:
          "<b>%{customdata[0]}</b><br>" +
          "RS-Ratio: %{x:.2f}<br>" +
          "RS-Mom: %{y:.2f}<br>" +
          "Quadrant: %{customdata[1]}<br>" +
          "Date: %{customdata[2]}<br>" +
          "RVOL: %{customdata[3]}<br>" +
          "Fund score: %{customdata[4]}<extra></extra>",
      });
    });

    // Symmetric square padded by 1.5 around 100 based on data extent.
    const pad = Math.max(1.5, Math.max(maxX - 100, 100 - minX, maxY - 100, 100 - minY) + 0.5);
    const range = {
      x: [100 - pad, 100 + pad] as [number, number],
      y: [100 - pad, 100 + pad] as [number, number],
    };

    return { traces, range };
  }, [series, showRvolWidth, showFundamentalColor, showLabels]);

  const shapes = useMemo(
    () => [
      { type: "line", x0: 100, x1: 100, y0: range.y[0], y1: range.y[1], line: { color: "#4b5563", width: 1, dash: "dot" } },
      { type: "line", x0: range.x[0], x1: range.x[1], y0: 100, y1: 100, line: { color: "#4b5563", width: 1, dash: "dot" } },
      // Quadrant background tints
      { type: "rect", xref: "x", yref: "y", x0: 100, y0: 100, x1: range.x[1], y1: range.y[1], fillcolor: "rgba(22,163,74,0.08)", line: { width: 0 }, layer: "below" },
      { type: "rect", xref: "x", yref: "y", x0: 100, y0: range.y[0], x1: range.x[1], y1: 100, fillcolor: "rgba(234,179,8,0.08)", line: { width: 0 }, layer: "below" },
      { type: "rect", xref: "x", yref: "y", x0: range.x[0], y0: range.y[0], x1: 100, y1: 100, fillcolor: "rgba(220,38,38,0.08)", line: { width: 0 }, layer: "below" },
      { type: "rect", xref: "x", yref: "y", x0: range.x[0], y0: 100, x1: 100, y1: range.y[1], fillcolor: "rgba(37,99,235,0.08)", line: { width: 0 }, layer: "below" },
    ],
    [range]
  );

  const annotations = useMemo(
    () => [
      { x: range.x[1] - 0.2, y: range.y[1] - 0.2, xref: "x", yref: "y", text: "Leading", showarrow: false, font: { color: "#16a34a", size: 14 }, xanchor: "right", yanchor: "top" },
      { x: range.x[1] - 0.2, y: range.y[0] + 0.2, xref: "x", yref: "y", text: "Weakening", showarrow: false, font: { color: "#ca8a04", size: 14 }, xanchor: "right", yanchor: "bottom" },
      { x: range.x[0] + 0.2, y: range.y[0] + 0.2, xref: "x", yref: "y", text: "Lagging", showarrow: false, font: { color: "#dc2626", size: 14 }, xanchor: "left", yanchor: "bottom" },
      { x: range.x[0] + 0.2, y: range.y[1] - 0.2, xref: "x", yref: "y", text: "Improving", showarrow: false, font: { color: "#2563eb", size: 14 }, xanchor: "left", yanchor: "top" },
    ],
    [range]
  );

  return (
    <Plot
      data={traces}
      layout={{
        autosize: true,
        height,
        margin: { l: 60, r: 20, t: 40, b: 50 },
        paper_bgcolor: "#0b1220",
        plot_bgcolor: "#0b1220",
        font: { color: "#e5e7eb", family: "Inter, sans-serif" },
        title: { text: `RRG vs ${benchmark}`, font: { color: "#f3f4f6", size: 16 } },
        xaxis: {
          title: { text: "JdK RS-Ratio" },
          range: range.x,
          gridcolor: "#1f2937",
          zerolinecolor: "#374151",
        },
        yaxis: {
          title: { text: "JdK RS-Momentum" },
          range: range.y,
          gridcolor: "#1f2937",
          zerolinecolor: "#374151",
        },
        shapes: shapes as any,
        annotations: annotations as any,
        legend: { bgcolor: "rgba(17,24,39,0.6)", bordercolor: "#374151", borderwidth: 1 },
        hovermode: "closest",
      }}
      config={{ displayModeBar: true, displaylogo: false, responsive: true }}
      style={{ width: "100%" }}
      onClick={(e: any) => {
        if (!onTickerClick) return;
        const pt = e.points?.[0];
        const t = pt?.customdata?.[0];
        if (typeof t === "string") onTickerClick(t);
      }}
    />
  );
}
