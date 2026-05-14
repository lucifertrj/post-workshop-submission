"use client";
import type { Algo } from "@/lib/types";

// "naive" is the non-iterative baseline (no-optimizer / no-prior reference).
// Iterative algos report a final objective value; naive doesn't, so finalObj
// is optional.
export type RunSummary = {
  algo: Algo | "naive";
  iters: number;             // 0 for naive
  finalObj?: number;
  finalPsnr?: number;
  finalSsim?: number;
  finalSnr?: number;
  finalSparsity?: number;
};

const ALGO_LABEL: Record<Algo | "naive", string> = {
  naive: "no-opt",
  ista: "ISTA",
  fista: "FISTA",
};

const ALGO_CLASS: Record<Algo | "naive", string> = {
  naive: "text-muted/80 italic",
  ista: "text-cream/80",
  fista: "text-gold",
};

export default function MetricsCard({
  baseline,
  baselineLabel,
  baselineValue,
  runs,
  metricLabel,
  formatMetric,
}: {
  baseline?: number;
  baselineLabel?: string;
  baselineValue?: string;
  runs: RunSummary[];
  metricLabel: string;
  formatMetric: (r: RunSummary) => string;
}) {
  return (
    <div className="border border-line rounded-lg p-5 bg-deep/40">
      <div className="font-mono text-xs uppercase tracking-wider text-muted mb-4">
        run summary
      </div>
      {baseline !== undefined && (
        <div className="flex items-baseline justify-between mb-3 pb-3 border-b border-line">
          <div className="text-sm text-muted">{baselineLabel ?? "input"}</div>
          <div className="font-mono text-sm tabular text-cream/80">
            {baselineValue}
          </div>
        </div>
      )}
      {runs.length === 0 ? (
        <div className="text-sm text-muted/70 italic">
          No runs yet — hit Run.
        </div>
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="text-muted font-mono text-xs uppercase tracking-wider">
              <th className="text-left pb-2 font-normal">algo</th>
              <th className="text-right pb-2 font-normal">iters</th>
              <th className="text-right pb-2 font-normal">final F(x)</th>
              <th className="text-right pb-2 font-normal">{metricLabel}</th>
            </tr>
          </thead>
          <tbody className="font-mono tabular">
            {runs.map((r, i) => (
              <tr key={i} className="border-t border-line/50">
                <td className={"py-2 " + ALGO_CLASS[r.algo]}>
                  {ALGO_LABEL[r.algo]}
                </td>
                <td className="py-2 text-right text-cream/80">
                  {r.algo === "naive" ? "—" : r.iters}
                </td>
                <td className="py-2 text-right text-cream/80">
                  {r.finalObj !== undefined ? r.finalObj.toExponential(3) : "—"}
                </td>
                <td className="py-2 text-right text-cream">
                  {formatMetric(r)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
