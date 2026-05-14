"use client";
import { useEffect, useRef, useState } from "react";
import {
  listSignalPresets,
  previewSignal,
  denoiseStreamUrl,
} from "@/lib/api";
import { streamRun, type SSEHandle } from "@/lib/sse";
import type {
  Algo,
  DenoiseInit,
  DenoiseIter,
  SignalPresetInfo,
} from "@/lib/types";
import ParamSlider from "@/components/ParamSlider";
import PresetPicker from "@/components/PresetPicker";
import SignalChart from "@/components/SignalChart";
import ConvergenceChart, {
  type ChartRun,
} from "@/components/ConvergenceChart";
import MetricsCard, { type RunSummary } from "@/components/MetricsCard";

type DenoiseRun = {
  runId: string;
  algo: Algo;
  history: DenoiseIter[];
  latestX: number[] | null;
  status: "streaming" | "done" | "error";
};

export default function SignalRace() {
  const [presets, setPresets] = useState<SignalPresetInfo[]>([]);
  const [preset, setPreset] = useState("spikes_20");
  const [lam, setLam] = useState(0.05);
  const [M, setM] = useState(400);
  const [noise, setNoise] = useState(0.01);
  const [maxIter, setMaxIter] = useState(500);
  const [seed, setSeed] = useState(1);
  const [previewSig, setPreviewSig] = useState<number[] | null>(null);
  const [init, setInit] = useState<DenoiseInit | null>(null);
  const [runs, setRuns] = useState<DenoiseRun[]>([]);
  const [activeStreams, setActiveStreams] = useState(0);
  const handlesRef = useRef<SSEHandle[]>([]);

  useEffect(() => {
    listSignalPresets().then(setPresets).catch(console.error);
    return () => {
      handlesRef.current.forEach((h) => h.close());
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    previewSignal(preset)
      .then((s) => {
        if (!cancelled) setPreviewSig(s);
      })
      .catch(console.error);
    return () => {
      cancelled = true;
    };
  }, [preset]);

  const updateRun = (runId: string, fn: (r: DenoiseRun) => DenoiseRun) => {
    setRuns((rs) => rs.map((r) => (r.runId === runId ? fn(r) : r)));
  };

  const racing = activeStreams > 0;

  const handleRunRace = () => {
    if (racing) return;
    handlesRef.current.forEach((h) => h.close());
    handlesRef.current = [];
    setInit(null);

    const istaRunId = crypto.randomUUID();
    const fistaRunId = crypto.randomUUID();
    setRuns([
      {
        runId: istaRunId,
        algo: "ista",
        history: [],
        latestX: null,
        status: "streaming",
      },
      {
        runId: fistaRunId,
        algo: "fista",
        history: [],
        latestX: null,
        status: "streaming",
      },
    ]);
    setActiveStreams(2);

    const handlers = (runId: string) => ({
      onInit: (data: DenoiseInit) => setInit(data),
      onIter: (data: DenoiseIter) =>
        updateRun(runId, (r) => ({
          ...r,
          history: [...r.history, data],
          latestX: data.x ?? r.latestX,
        })),
      onDone: () => {
        updateRun(runId, (r) => ({ ...r, status: "done" }));
        setActiveStreams((c) => c - 1);
      },
      onError: () => {
        updateRun(runId, (r) => ({ ...r, status: "error" }));
        setActiveStreams((c) => c - 1);
      },
    });

    const common = {
      name: preset,
      lam,
      M,
      noise,
      max_iter: maxIter,
      snapshot_every: 10,
      seed,
    } as const;

    handlesRef.current = [
      streamRun<DenoiseInit, DenoiseIter>(
        denoiseStreamUrl({ ...common, algo: "ista" }),
        handlers(istaRunId),
      ),
      streamRun<DenoiseInit, DenoiseIter>(
        denoiseStreamUrl({ ...common, algo: "fista" }),
        handlers(fistaRunId),
      ),
    ];
  };

  const handleStop = () => {
    handlesRef.current.forEach((h) => h.close());
    handlesRef.current = [];
    setActiveStreams(0);
    setRuns((rs) =>
      rs.map((r) =>
        r.status === "streaming" ? { ...r, status: "done" } : r,
      ),
    );
  };

  const handleClear = () => {
    handleStop();
    setRuns([]);
    setInit(null);
  };

  const istaRun = runs.find((r) => r.algo === "ista");
  const fistaRun = runs.find((r) => r.algo === "fista");
  const lastIterAny =
    fistaRun?.history[fistaRun.history.length - 1] ??
    istaRun?.history[istaRun.history.length - 1];

  const objRuns: ChartRun[] = runs.map((r) => ({
    algo: r.algo,
    history: r.history.map((h) => ({ k: h.k, value: h.obj })),
  }));
  const snrRuns: ChartRun[] = runs.map((r) => ({
    algo: r.algo,
    history: r.history.map((h) => ({ k: h.k, value: h.snr })),
  }));

  const summaries: RunSummary[] = [];
  if (init) {
    summaries.push({
      algo: "naive",
      iters: 0,
      finalSnr: init.baseline_snr,
      finalSparsity: init.baseline_sparsity,
    });
  }
  for (const r of runs) {
    const last = r.history[r.history.length - 1];
    if (!last) continue;
    summaries.push({
      algo: r.algo,
      iters: r.history.length,
      finalObj: last.obj,
      finalSnr: last.snr,
      finalSparsity: last.sparsity,
    });
  }

  const truthSignal = init?.x_true ?? previewSig;

  return (
    <div>
      <p className="text-muted text-base max-w-3xl mb-8 leading-relaxed">
        Three solvers, one underdetermined inverse problem. The{" "}
        <span className="text-cream">naive least-squares pseudoinverse</span>{" "}
        gives a min-L2-norm solution — dense, not sparse.{" "}
        <span className="text-cream">ISTA</span> and{" "}
        <span className="text-gold">FISTA</span> both minimize{" "}
        <span className="font-mono">½‖A x − y‖² + λ‖x‖₁</span> via soft
        thresholding; FISTA's momentum gets there roughly{" "}
        <span className="text-gold">3-4×</span> faster.
      </p>

      <section className="border border-line rounded-lg p-6 bg-deep/40 mb-8">
        <div className="grid sm:grid-cols-2 gap-6">
          <PresetPicker
            label="signal"
            value={preset}
            onChange={setPreset}
            disabled={racing}
            options={presets.map((p) => ({
              value: p.name,
              label: `${p.name} (N=${p.length})`,
            }))}
          />
          <div />
          <ParamSlider
            label="λ (sparsity prior)"
            value={lam}
            min={0.001}
            max={0.5}
            step={0.001}
            format={(v) => v.toFixed(3)}
            onChange={setLam}
            disabled={racing}
          />
          <ParamSlider
            label="M (measurements)"
            value={M}
            min={50}
            max={1024}
            step={25}
            format={(v) => v.toString()}
            onChange={setM}
            disabled={racing}
          />
          <ParamSlider
            label="noise stddev"
            value={noise}
            min={0}
            max={0.1}
            step={0.005}
            format={(v) => v.toFixed(3)}
            onChange={setNoise}
            disabled={racing}
          />
          <ParamSlider
            label="max iterations"
            value={maxIter}
            min={100}
            max={1000}
            step={50}
            format={(v) => v.toString()}
            onChange={setMaxIter}
            disabled={racing}
          />
        </div>
        <div className="flex flex-wrap gap-3 mt-6">
          <button
            type="button"
            onClick={handleRunRace}
            disabled={racing}
            className="px-6 py-2 rounded-full bg-gold text-deep font-medium hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {racing
              ? `Racing (${activeStreams} stream${activeStreams === 1 ? "" : "s"})…`
              : "Run Race"}
          </button>
          {racing && (
            <button
              type="button"
              onClick={handleStop}
              className="px-6 py-2 rounded-full border border-line text-cream hover:border-cream/40 transition-colors"
            >
              Stop
            </button>
          )}
          <button
            type="button"
            onClick={handleClear}
            disabled={racing}
            className="px-6 py-2 rounded-full border border-line text-muted hover:text-cream hover:border-cream/40 transition-colors disabled:opacity-50"
          >
            Clear
          </button>
        </div>
      </section>

      {/* Three stacked signal panels: truth, measurements, recovered overlay */}
      <section className="space-y-4 mb-8">
        <div className="border border-line rounded-lg p-5 bg-deep/40">
          <div className="font-mono text-xs uppercase tracking-wider text-muted mb-3">
            true sparse signal (length {truthSignal?.length ?? "—"})
          </div>
          <SignalChart
            series={
              truthSignal
                ? [{ name: "truth", values: truthSignal, color: "#f4ebe1" }]
                : []
            }
            height={140}
          />
        </div>
        <div className="border border-line rounded-lg p-5 bg-deep/40">
          <div className="font-mono text-xs uppercase tracking-wider text-muted mb-3">
            compressed noisy measurements y (M = {init?.M ?? "—"})
          </div>
          <SignalChart
            series={
              init
                ? [
                    {
                      name: "y",
                      values: init.y,
                      color: "#a89580",
                      alpha: 0.85,
                    },
                  ]
                : []
            }
            height={140}
            showZeroLine
          />
        </div>
        <div className="border border-line rounded-lg p-5 bg-deep/40">
          <div className="font-mono text-xs uppercase tracking-wider text-muted mb-3">
            recovered signals
            {lastIterAny
              ? ` · iter ${lastIterAny.k + 1}`
              : ""}
          </div>
          <SignalChart
            series={[
              ...(truthSignal
                ? [
                    {
                      name: "truth",
                      values: truthSignal,
                      color: "#f4ebe1",
                      alpha: 0.5,
                    },
                  ]
                : []),
              ...(init?.baseline_x
                ? [
                    {
                      name: "naive",
                      values: init.baseline_x,
                      color: "#a89580",
                      alpha: 0.55,
                      dashed: true,
                    },
                  ]
                : []),
              ...(istaRun?.latestX
                ? [
                    {
                      name: "ista",
                      values: istaRun.latestX,
                      color: "#5b9bd5",
                      alpha: 0.95,
                    },
                  ]
                : []),
              ...(fistaRun?.latestX
                ? [
                    {
                      name: "fista",
                      values: fistaRun.latestX,
                      color: "#e0a93f",
                      alpha: 0.95,
                      dashed: true,
                    },
                  ]
                : []),
            ]}
            height={200}
          />
        </div>
      </section>

      <section className="grid lg:grid-cols-2 gap-6 mb-8">
        <div className="border border-line rounded-lg p-5 bg-deep/40">
          <div className="font-mono text-xs uppercase tracking-wider text-muted mb-3">
            objective F(x_k) [log scale]
          </div>
          <ConvergenceChart runs={objRuns} yLabel="" yScale="log" />
        </div>
        <div className="border border-line rounded-lg p-5 bg-deep/40">
          <div className="font-mono text-xs uppercase tracking-wider text-muted mb-3">
            recovery quality (SNR, dB)
          </div>
          <ConvergenceChart
            runs={snrRuns}
            yLabel=""
            yScale="linear"
            referenceY={init?.baseline_snr}
            referenceLabel={
              init
                ? `no-opt: ${init.baseline_snr.toFixed(1)} dB`
                : undefined
            }
          />
        </div>
      </section>

      <section>
        <MetricsCard
          baselineLabel="problem"
          baselineValue={
            init
              ? `N=${init.N}, M=${init.M}, L=${init.L.toFixed(3)}`
              : "—"
          }
          runs={summaries}
          metricLabel="final SNR"
          formatMetric={(r) =>
            r.finalSnr !== undefined
              ? `${r.finalSnr.toFixed(2)} dB`
              : "—"
          }
        />
      </section>
    </div>
  );
}
