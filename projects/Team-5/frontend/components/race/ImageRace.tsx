"use client";
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
import PresetPicker from "@/components/PresetPicker";
import ImageCanvas from "@/components/ImageCanvas";
import ConvergenceChart, {
  type ChartRun,
} from "@/components/ConvergenceChart";
import MetricsCard, { type RunSummary } from "@/components/MetricsCard";

type DeblurRun = {
  runId: string;
  algo: Algo;
  history: DeblurIter[];
  latestImg: string | null;
  status: "streaming" | "done" | "error";
};

export default function ImageRace() {
  const [presets, setPresets] = useState<ImagePresetInfo[]>([]);
  const [preset, setPreset] = useState("cameraman");
  const [lam, setLam] = useState(0.003);
  const [sigma, setSigma] = useState(2.5);
  const [noise, setNoise] = useState(0.01);
  const [maxIter, setMaxIter] = useState(200);
  const [previewSrc, setPreviewSrc] = useState<string | null>(null);
  const [init, setInit] = useState<DeblurInit | null>(null);
  const [runs, setRuns] = useState<DeblurRun[]>([]);
  const [activeStreams, setActiveStreams] = useState(0);
  const handlesRef = useRef<SSEHandle[]>([]);

  useEffect(() => {
    listImagePresets().then(setPresets).catch(console.error);
    return () => {
      handlesRef.current.forEach((h) => h.close());
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

  const updateRun = (runId: string, fn: (r: DeblurRun) => DeblurRun) => {
    setRuns((rs) => rs.map((r) => (r.runId === runId ? fn(r) : r)));
  };

  const racing = activeStreams > 0;

  const handleRunRace = () => {
    if (racing) return;
    // Reset previous race so the comparison view stays focused
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
        latestImg: null,
        status: "streaming",
      },
      {
        runId: fistaRunId,
        algo: "fista",
        history: [],
        latestImg: null,
        status: "streaming",
      },
    ]);
    setActiveStreams(2);

    const handlers = (runId: string) => ({
      onInit: (data: DeblurInit) => setInit(data),
      onIter: (data: DeblurIter) =>
        updateRun(runId, (r) => ({
          ...r,
          history: [...r.history, data],
          latestImg: data.x_png
            ? `data:image/png;base64,${data.x_png}`
            : r.latestImg,
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
      sigma,
      noise,
      max_iter: maxIter,
      snapshot_every: 5,
    } as const;

    handlesRef.current = [
      streamRun<DeblurInit, DeblurIter>(
        deblurStreamUrl({ ...common, algo: "ista" }),
        handlers(istaRunId),
      ),
      streamRun<DeblurInit, DeblurIter>(
        deblurStreamUrl({ ...common, algo: "fista" }),
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
  const istaLast = istaRun?.history[istaRun.history.length - 1];
  const fistaLast = fistaRun?.history[fistaRun.history.length - 1];

  const objRuns: ChartRun[] = runs.map((r) => ({
    algo: r.algo,
    history: r.history.map((h) => ({ k: h.k, value: h.obj })),
  }));
  const psnrRuns: ChartRun[] = runs.map((r) => ({
    algo: r.algo,
    history: r.history.map((h) => ({ k: h.k, value: h.psnr })),
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
    <div>
      <p className="text-muted text-base max-w-3xl mb-8 leading-relaxed">
        Three solvers, one inverse problem. The{" "}
        <span className="text-cream">naive FFT inverse filter</span> divides{" "}
        <span className="font-mono">DFT(y) / DFT(k)</span> with no
        regularization — high-frequency noise gets amplified into ringing.{" "}
        <span className="text-cream">ISTA</span> and{" "}
        <span className="text-gold">FISTA</span> both minimize{" "}
        <span className="font-mono">½‖A x − y‖² + λ TV(x)</span> via
        proximal-gradient steps; FISTA's momentum gets there in roughly{" "}
        <span className="text-gold">3-4×</span> fewer iterations.
      </p>

      <section className="border border-line rounded-lg p-6 bg-deep/40 mb-8">
        <div className="grid sm:grid-cols-2 gap-6">
          <PresetPicker
            label="image"
            value={preset}
            onChange={setPreset}
            disabled={racing}
            options={presets.map((p) => ({ value: p.name, label: p.name }))}
          />
          <div />
          <ParamSlider
            label="λ (regularization)"
            value={lam}
            min={0.0001}
            max={0.05}
            step={0.0001}
            format={(v) => v.toFixed(4)}
            onChange={setLam}
            disabled={racing}
          />
          <ParamSlider
            label="σ (blur stddev)"
            value={sigma}
            min={0.5}
            max={5.0}
            step={0.1}
            format={(v) => v.toFixed(1)}
            onChange={setSigma}
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
            min={50}
            max={500}
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

      {/* 5-panel image strip: original | blurry | naive | ISTA | FISTA */}
      <section className="grid sm:grid-cols-2 lg:grid-cols-5 gap-4 mb-8">
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
          src={
            init?.baseline_png
              ? `data:image/png;base64,${init.baseline_png}`
              : null
          }
          title="naive (no-opt)"
          caption={
            init
              ? `PSNR ${init.baseline_psnr.toFixed(2)} dB`
              : undefined
          }
        />
        <ImageCanvas
          src={istaRun?.latestImg ?? null}
          title="ISTA recovered"
          caption={
            istaLast
              ? `iter ${istaLast.k + 1} · ${istaLast.psnr.toFixed(2)} dB`
              : undefined
          }
        />
        <ImageCanvas
          src={fistaRun?.latestImg ?? null}
          title="FISTA recovered"
          caption={
            fistaLast
              ? `iter ${fistaLast.k + 1} · ${fistaLast.psnr.toFixed(2)} dB`
              : undefined
          }
        />
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
            recovery quality (PSNR, dB)
          </div>
          <ConvergenceChart
            runs={psnrRuns}
            yLabel=""
            yScale="linear"
            referenceY={init?.baseline_psnr}
            referenceLabel={
              init
                ? `no-opt: ${init.baseline_psnr.toFixed(1)} dB`
                : undefined
            }
          />
        </div>
      </section>

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
            r.finalPsnr !== undefined
              ? `${r.finalPsnr.toFixed(2)} dB`
              : "—"
          }
        />
      </section>
    </div>
  );
}
