"use client";
import Link from "next/link";
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
import AlgoToggle from "@/components/AlgoToggle";
import PresetPicker from "@/components/PresetPicker";
import SignalChart from "@/components/SignalChart";
import ConvergenceChart, { type ChartRun } from "@/components/ConvergenceChart";
import MetricsCard, { type RunSummary } from "@/components/MetricsCard";

type DenoiseRun = {
  algo: Algo;
  history: DenoiseIter[];
  latestX: number[] | null;
  status: "streaming" | "done" | "error";
};

export default function DenoisePage() {
  const [presets, setPresets] = useState<SignalPresetInfo[]>([]);
  const [preset, setPreset] = useState("spikes_20");
  const [algo, setAlgo] = useState<Algo>("fista");
  const [lam, setLam] = useState(0.05);
  const [M, setM] = useState(400);
  const [noise, setNoise] = useState(0.01);
  const [maxIter, setMaxIter] = useState(500);
  const [seed, setSeed] = useState(1);
  const [previewSig, setPreviewSig] = useState<number[] | null>(null);
  const [init, setInit] = useState<DenoiseInit | null>(null);
  const [runs, setRuns] = useState<DenoiseRun[]>([]);
  const [streaming, setStreaming] = useState(false);
  const handleRef = useRef<SSEHandle | null>(null);

  useEffect(() => {
    listSignalPresets().then(setPresets).catch(console.error);
    return () => {
      handleRef.current?.close();
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

  const updateLastRun = (fn: (r: DenoiseRun) => DenoiseRun) => {
    setRuns((rs) =>
      rs.map((r, i) => (i === rs.length - 1 ? fn(r) : r)),
    );
  };

  const handleRun = () => {
    if (streaming) return;
    const url = denoiseStreamUrl({
      name: preset,
      algo,
      lam,
      M,
      noise,
      max_iter: maxIter,
      snapshot_every: 10,
      seed,
    });
    setStreaming(true);
    setRuns((rs) => [
      ...rs,
      { algo, history: [], latestX: null, status: "streaming" },
    ]);

    handleRef.current = streamRun<DenoiseInit, DenoiseIter>(url, {
      onInit: (data) => setInit(data),
      onIter: (data) =>
        updateLastRun((r) => ({
          ...r,
          history: [...r.history, data],
          latestX: data.x ?? r.latestX,
        })),
      onDone: () => {
        updateLastRun((r) => ({ ...r, status: "done" }));
        setStreaming(false);
        handleRef.current = null;
      },
      onError: () => {
        updateLastRun((r) => ({ ...r, status: "error" }));
        setStreaming(false);
        handleRef.current = null;
      },
    });
  };

  const handleStop = () => {
    handleRef.current?.close();
    handleRef.current = null;
    setStreaming(false);
    updateLastRun((r) =>
      r.status === "streaming" ? { ...r, status: "done" } : r,
    );
  };

  const handleClear = () => {
    handleStop();
    setRuns([]);
    setInit(null);
  };

  const lastRun = runs[runs.length - 1];
  const lastIter = lastRun?.history[lastRun.history.length - 1];

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

  // Signal display: show truth (from init or preview) + latest recovery
  const truthSignal = init?.x_true ?? previewSig;
  const recoverySignal = lastRun?.latestX ?? null;

  return (
    <main>
      <nav className="flex items-center justify-between px-8 py-6 text-sm font-mono">
        <Link
          href="/"
          className="text-cream tracking-tight hover:text-gold transition-colors"
        >
          ← proximal methods
        </Link>
        <div className="flex gap-6 text-muted">
          <Link href="/deblur" className="hover:text-gold transition-colors">
            deblur
          </Link>
          <Link href="/denoise" className="text-gold">
            recover
          </Link>
          <Link href="/race" className="hover:text-gold transition-colors">
            race
          </Link>
        </div>
      </nav>

      <div className="max-w-6xl mx-auto px-8 pb-32">
        <p className="font-mono text-xs uppercase tracking-[0.3em] text-muted mb-3">
          demo · 1D
        </p>
        <h1 className="text-4xl sm:text-5xl font-bold mb-4">
          Sparse Recovery (LASSO)
        </h1>
        <p className="text-muted text-lg max-w-2xl mb-8 leading-relaxed">
          Recover a sparse signal from compressed Gaussian measurements{" "}
          <span className="font-mono text-cream">y = A x + n</span>, where A is
          M×N with M&lt;N. The composite objective is{" "}
          <span className="font-mono text-cream">
            ½‖A x − y‖² + λ‖x‖₁
          </span>
          , with prox = soft thresholding. Soft thresholding from scratch; A
          is dense Gaussian.
        </p>

        {/* Controls */}
        <section className="border border-line rounded-lg p-6 bg-deep/40 mb-8">
          <div className="grid sm:grid-cols-2 gap-6">
            <PresetPicker
              label="signal"
              value={preset}
              onChange={setPreset}
              disabled={streaming}
              options={presets.map((p) => ({
                value: p.name,
                label: `${p.name} (N=${p.length})`,
              }))}
            />
            <AlgoToggle value={algo} onChange={setAlgo} disabled={streaming} />
            <ParamSlider
              label="λ (sparsity prior)"
              value={lam}
              min={0.001}
              max={0.5}
              step={0.001}
              format={(v) => v.toFixed(3)}
              onChange={setLam}
              disabled={streaming}
            />
            <ParamSlider
              label="M (measurements)"
              value={M}
              min={50}
              max={1024}
              step={25}
              format={(v) => v.toString()}
              onChange={setM}
              disabled={streaming}
            />
            <ParamSlider
              label="noise stddev"
              value={noise}
              min={0}
              max={0.1}
              step={0.005}
              format={(v) => v.toFixed(3)}
              onChange={setNoise}
              disabled={streaming}
            />
            <ParamSlider
              label="max iterations"
              value={maxIter}
              min={100}
              max={1000}
              step={50}
              format={(v) => v.toString()}
              onChange={setMaxIter}
              disabled={streaming}
            />
          </div>
          <div className="flex flex-wrap gap-3 mt-6">
            <button
              type="button"
              onClick={handleRun}
              disabled={streaming}
              className="px-6 py-2 rounded-full bg-gold text-deep font-medium hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {streaming
                ? `Running ${algo.toUpperCase()}…`
                : `Run ${algo.toUpperCase()}`}
            </button>
            {streaming && (
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
              disabled={streaming}
              className="px-6 py-2 rounded-full border border-line text-muted hover:text-cream hover:border-cream/40 transition-colors disabled:opacity-50"
            >
              Clear runs
            </button>
          </div>
        </section>

        {/* Signal panels */}
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
                  ? [{ name: "y", values: init.y, color: "#a89580", alpha: 0.85 }]
                  : []
              }
              height={140}
              showZeroLine
            />
          </div>
          <div className="border border-line rounded-lg p-5 bg-deep/40">
            <div className="font-mono text-xs uppercase tracking-wider text-muted mb-3">
              recovered signal{" "}
              {lastIter
                ? `· iter ${lastIter.k + 1} · SNR ${lastIter.snr.toFixed(2)} dB · sparsity ${(lastIter.sparsity * 100).toFixed(1)}%`
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
                ...(recoverySignal
                  ? [
                      {
                        name: "recovered",
                        values: recoverySignal,
                        color:
                          lastRun?.algo === "fista" ? "#e0a93f" : "#5b9bd5",
                        dashed: true,
                      },
                    ]
                  : []),
              ]}
              height={180}
            />
          </div>
        </section>

        {/* Convergence */}
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
            <ConvergenceChart runs={snrRuns} yLabel="" yScale="linear" />
          </div>
        </section>

        {/* Metrics */}
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
              r.finalSnr !== undefined ? `${r.finalSnr.toFixed(2)} dB` : "—"
            }
          />
        </section>
      </div>
    </main>
  );
}
