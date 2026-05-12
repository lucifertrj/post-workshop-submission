"use client";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ResponsiveContainer,
  ReferenceLine,
  Label,
} from "recharts";
import type { Algo } from "@/lib/types";

export type ChartRun = {
  algo: Algo;
  history: { k: number; value: number }[];
};

type Props = {
  runs: ChartRun[];
  yLabel: string;
  yScale?: "log" | "linear";
  yDomain?: [number | "auto", number | "auto"];
  height?: number;
  // Optional horizontal reference line, used to show the non-iterative
  // "no-optimizer" baseline value (e.g., naive-inverse PSNR).
  referenceY?: number;
  referenceLabel?: string;
};

const COLORS: Record<Algo, [string, string]> = {
  // [first run, second run] of each algo — supports up to 2 runs per algo
  ista:  ["#5b9bd5", "#3878b8"],
  fista: ["#e0a93f", "#c08020"],
};

export default function ConvergenceChart({
  runs,
  yLabel,
  yScale = "log",
  yDomain,
  height = 260,
  referenceY,
  referenceLabel,
}: Props) {
  // Color each run by algo, distinguishing repeats
  const seenByAlgo: Record<Algo, number> = { ista: 0, fista: 0 };
  return (
    <div className="w-full">
      <ResponsiveContainer width="100%" height={height}>
        <LineChart margin={{ top: 8, right: 16, left: 4, bottom: 4 }}>
          <CartesianGrid stroke="rgba(244,235,225,0.07)" />
          <XAxis
            dataKey="k"
            type="number"
            tick={{ fill: "rgba(244,235,225,0.7)", fontSize: 11 }}
            stroke="rgba(244,235,225,0.2)"
            label={{
              value: "iteration k",
              position: "insideBottom",
              offset: -2,
              fill: "rgba(244,235,225,0.5)",
              fontSize: 11,
            }}
          />
          <YAxis
            scale={yScale}
            domain={yDomain ?? ["auto", "auto"]}
            tick={{ fill: "rgba(244,235,225,0.7)", fontSize: 11 }}
            stroke="rgba(244,235,225,0.2)"
            label={{
              value: yLabel,
              angle: -90,
              position: "insideLeft",
              fill: "rgba(244,235,225,0.5)",
              fontSize: 11,
            }}
            allowDataOverflow={false}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: "rgba(10,16,20,0.92)",
              border: "1px solid rgba(244,235,225,0.15)",
              borderRadius: "6px",
              fontSize: "12px",
              color: "rgba(244,235,225,0.9)",
            }}
            labelStyle={{ color: "rgba(244,235,225,0.6)" }}
            formatter={(v: number) =>
              Math.abs(v) < 1e-3 || Math.abs(v) >= 1e4
                ? v.toExponential(3)
                : v.toFixed(3)
            }
          />
          {referenceY !== undefined && Number.isFinite(referenceY) && (
            <ReferenceLine
              y={referenceY}
              stroke="rgba(173,152,134,0.7)"
              strokeDasharray="4 4"
              ifOverflow="extendDomain"
              label={(props: { viewBox?: { x: number; y: number; width: number; height: number } }) => {
                const vb = props.viewBox;
                if (!vb) return null;
                // Always render 10px above the reference line, right-aligned.
                // Clamped so it never exits the top margin (min y = 18).
                const textY = Math.max(vb.y - 10, 18);
                const textX = vb.x + vb.width - 6;
                return (
                  <text
                    x={textX}
                    y={textY}
                    textAnchor="end"
                    fill="rgba(173,152,134,0.9)"
                    fontSize={10}
                    fontFamily="'JetBrains Mono', monospace"
                    letterSpacing="0.04em"
                  >
                    {referenceLabel ?? "no-opt baseline"}
                  </text>
                );
              }}
            />
          )}
          {runs.map((run, i) => {
            const idx = seenByAlgo[run.algo]++;
            const color =
              COLORS[run.algo][Math.min(idx, COLORS[run.algo].length - 1)];
            return (
              <Line
                key={i}
                data={run.history}
                dataKey="value"
                name={`${run.algo.toUpperCase()}${idx > 0 ? ` (${idx + 1})` : ""}`}
                stroke={color}
                strokeWidth={2}
                dot={false}
                isAnimationActive={false}
              />
            );
          })}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
