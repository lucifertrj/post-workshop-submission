"use client";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import {
  listImagePresets,
  previewImage,
  deblurStreamUrl,
} from "@/lib/api";
import { streamRun, type SSEHandle } from "@/lib/sse";
import type {
  Algo,
  DeblurInit,
  DeblurIter,
  ImagePresetInfo,
} from "@/lib/types";
import ParamSlider from "@/components/ParamSlider";
import AlgoToggle from "@/components/AlgoToggle";
import PresetPicker from "@/components/PresetPicker";
import ImageCanvas from "@/components/ImageCanvas";
import ConvergenceChart, { type ChartRun } from "@/components/ConvergenceChart";
import MetricsCard, { type RunSummary } from "@/components/MetricsCard";

type DeblurRun = {
  algo: Algo;
  history: DeblurIter[];
  latestImg: string | null;
  status: "streaming" | "done" | "error";
};

export default function DeblurPage() {
  const [presets, setPresets] = useState<ImagePresetInfo[]>([]);
  const [preset, setPreset] = useState("cameraman");
  const [algo, setAlgo] = useState<Algo>("fista");
  const [lam, setLam] = useState(0.003);
  const [sigma, setSigma] = useState(2.5);
  const [noise, setNoise] = useState(0.01);
  const [maxIter, setMaxIter] = useState(200);
  const [previewSrc, setPreviewSrc] = useState<string | null>(null);
  const [init, setInit] = useState<DeblurInit | null>(null);
  const [runs, setRuns] = useState<DeblurRun[]>([]);
  const [streaming, setStreaming] = useState(false);
  const handleRef = useRef<SSEHandle | null>(null);

  useEffect(() => {
    listImagePresets().then(setPresets).catch(console.error);
    return () => {
      handleRef.current?.close();
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    previewImage(preset)
      .then((src) => {
        if (!cancelled) setPreviewSrc(src);
      })
      .catch(console.error);
    return () => {
      cancelled = true;
    };
  }, [preset]);

  const updateLastRun = (fn: (r: DeblurRun) => DeblurRun) => {
    setRuns((rs) =>
      rs.map((r, i) => (i === rs.length - 1 ? fn(r) : r)),
    );
  };

  const handleRun = () => {
    if (streaming) return;
    const url = deblurStreamUrl({
      name: preset,
      algo,
      lam,
      sigma,
      noise,
      max_iter: maxIter,
      snapshot_every: 5,
    });
    setStreaming(true);
    setRuns((rs) => [
      ...rs,
      { algo, history: [], latestImg: null, status: "streaming" },
    ]);

    handleRef.current = streamRun<DeblurInit, DeblurIter>(url, {
      onInit: (data) => setInit(data),
      onIter: (data) =>
        updateLastRun((r) => ({
          ...r,
          history: [...r.history, data],
          latestImg: data.x_png
            ? `data:image/png;base64,${data.x_png}`
            : r.latestImg,
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
    updateLastRun((r) => (r.status === "streaming" ? { ...r, status: "done" } : r));
  };

  const handleClear = () => {
    handleStop();
    setRuns([]);
    setInit(null);
  };

  const lastRun = runs[runs.length - 1];
  const recoveredImg = lastRun?.latestImg ?? null;
  const recoveredAlgo = lastRun?.algo ?? null;
  const lastIter = lastRun?.history[lastRun.history.length - 1];

  const objRuns: ChartRun[] = runs.map((r) => ({
    algo: r.algo,
    history: r.history.map((h) => ({ k: h.k, value: h.obj })),
  }));
  const psnrRuns: ChartRun[] = runs.map((r) => ({
    algo: r.algo,
    history: r.history.map((h) => ({ k: h.k, value: h.psnr })),
  }));
  const ssimRuns: ChartRun[] = runs.map((r) => ({
    algo: r.algo,
    history: r.history.map((h) => ({ k: h.k, value: h.ssim })),
  }));

  const summaries: RunSummary[] = [];
  if (init) {
    summaries.push({
      algo: "naive",
      iters: 0,
      finalPsnr: init.baseline_psnr,
      finalSsim: init.baseline_ssim,
    });
  }
  for (const r of runs) {
    const last = r.history[r.history.length - 1];
    if (!last) continue;
    summaries.push({
      algo: r.algo,
      iters: r.history.length,
      finalObj: last.obj,
      finalPsnr: last.psnr,
      finalSsim: last.ssim,
    });
  }

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
          <Link href="/deblur" className="text-gold">
            deblur
          </Link>
          <Link href="/denoise" className="hover:text-gold transition-colors">
            recover
          </Link>
          <Link href="/race" className="hover:text-gold transition-colors">
            race
          </Link>
        </div>
      </nav>

      <div className="max-w-6xl mx-auto px-8 pb-32">
        <p className="font-mono text-xs uppercase tracking-[0.3em] text-muted mb-3">
          demo · 2D
        </p>
        <h1 className="text-4xl sm:text-5xl font-bold mb-4">
          Image Deblurring
        </h1>
        <p className="text-muted text-lg max-w-2xl mb-8 leading-relaxed">
          Recover a sharp image from a Gaussian-blurred, noisy observation
          using total-variation regularization. The composite objective is{" "}
          <span className="font-mono text-cream">
            ½‖A x − y‖² + λ TV(x)
          </span>
          , where A is the blur operator. The TV prox uses Chambolle's dual
          algorithm via skimage; the outer ISTA / FISTA loop is ours.
        </p>

        {/* Controls */}
        <section className="border border-line rounded-lg p-6 bg-deep/40 mb-8">
          <div className="grid sm:grid-cols-2 gap-6">
            <PresetPicker
              label="image"
              value={preset}
              onChange={setPreset}
              disabled={streaming}
              options={presets.map((p) => ({ value: p.name, label: p.name }))}
            />
            <AlgoToggle value={algo} onChange={setAlgo} disabled={streaming} />
            <ParamSlider
              label="λ (regularization)"
              value={lam}
              min={0.0001}
              max={0.05}
              step={0.0001}
              format={(v) => v.toFixed(4)}
              onChange={setLam}
              disabled={streaming}
            />
            <ParamSlider
              label="σ (blur stddev)"
              value={sigma}
              min={0.5}
              max={5.0}
              step={0.1}
              format={(v) => v.toFixed(1)}
              onChange={setSigma}
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
              min={50}
              max={500}
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

        {/* Image triptych */}
        <section className="grid sm:grid-cols-3 gap-4 mb-8">
          <ImageCanvas
            src={
              init?.x_true_png
                ? `data:image/png;base64,${init.x_true_png}`
                : previewSrc
            }
            title="original"
          />
          <ImageCanvas
            src={init?.y_png ? `data:image/png;base64,${init.y_png}` : null}
            title="blurry + noisy"
            caption={
              init ? `PSNR ${init.psnr_input.toFixed(2)} dB` : undefined
            }
          />
          <ImageCanvas
            src={recoveredImg}
            title={
              recoveredAlgo
                ? `recovered (${recoveredAlgo.toUpperCase()})`
                : "recovered"
            }
            caption={
              lastIter
                ? `iter ${lastIter.k + 1} · PSNR ${lastIter.psnr.toFixed(2)} dB`
                : undefined
            }
          />
        </section>

        {/* Convergence */}
        <section className="grid lg:grid-cols-3 gap-6 mb-8">
          <div className="border border-line rounded-lg p-5 bg-deep/40">
            <div className="font-mono text-xs uppercase tracking-wider text-muted mb-3">
              objective F(x_k) [log scale]
            </div>
            <ConvergenceChart runs={objRuns} yLabel="" yScale="log" />
          </div>
          <div className="border border-line rounded-lg p-5 bg-deep/40">
            <div className="font-mono text-xs uppercase tracking-wider text-muted mb-3">
              recovery quality (PSNR, dB)
            </div>
            <ConvergenceChart
              runs={psnrRuns}
              yLabel=""
              yScale="linear"
              referenceY={init?.baseline_psnr}
              referenceLabel="naive baseline"
            />
          </div>
          <div className="border border-line rounded-lg p-5 bg-deep/40">
            <div className="font-mono text-xs uppercase tracking-wider text-muted mb-3">
              structural similarity (SSIM)
            </div>
            <ConvergenceChart
              runs={ssimRuns}
              yLabel=""
              yScale="linear"
              yDomain={[0, 1]}
              referenceY={init?.baseline_ssim}
              referenceLabel="naive baseline"
            />
          </div>
        </section>

        {/* Metrics */}
        <section>
          <MetricsCard
            baselineLabel="blurry input"
            baselineValue={
              init ? `${init.psnr_input.toFixed(2)} dB` : "—"
            }
            baseline={init?.psnr_input}
            runs={summaries}
            metricLabel="final PSNR"
            formatMetric={(r) =>
              r.finalPsnr !== undefined ? `${r.finalPsnr.toFixed(2)} dB` : "—"
            }
          />
        </section>
      </div>
    </main>
  );
}
