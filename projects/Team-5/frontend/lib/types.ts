// Shared types between the FastAPI backend and the Next.js client.
// Mirror exactly what backend/main.py emits over SSE.

export type Algo = 'ista' | 'fista';

export type ImagePresetInfo = { name: string; shape: [number, number] };
export type SignalPresetInfo = { name: string; length: number };

// ---------- Deblur SSE events ----------

export type DeblurInit = {
  shape: [number, number];
  x_true_png: string;     // base64 PNG
  y_png: string;          // base64 PNG (blurry observation)
  psnr_input: number;
  // "No optimizer" baseline — naive FFT inverse filter, no regularization.
  baseline_png: string;
  baseline_psnr: number;
  baseline_ssim: number;
  baseline_mse: number;
  algo: Algo;
  max_iter: number;
};

export type DeblurIter = {
  k: number;
  obj: number;
  psnr: number;
  ssim: number;
  mse: number;
  x_png?: string;         // present every snapshot_every iterations
};

// ---------- Denoise (LASSO) SSE events ----------

export type DenoiseInit = {
  N: number;
  M: number;
  x_true: number[];       // length N
  y: number[];            // length M
  L: number;
  // "No optimizer" baseline — Moore-Penrose pseudoinverse, no ℓ1 prior.
  baseline_x: number[];
  baseline_snr: number;
  baseline_mse: number;
  baseline_sparsity: number;
  algo: Algo;
  max_iter: number;
};

export type DenoiseIter = {
  k: number;
  obj: number;
  snr: number;
  mse: number;
  sparsity: number;       // fraction of coefficients that are zero (0..1)
  x?: number[];           // present every snapshot_every iterations
};

// ---------- Run-config types (frontend -> backend query strings) ----------

export type DeblurRunParams = {
  name: string;
  algo: Algo;
  lam: number;
  sigma: number;
  noise: number;
  max_iter: number;
  snapshot_every: number;
};

export type DenoiseRunParams = {
  name: string;
  algo: Algo;
  lam: number;
  M: number;
  noise: number;
  max_iter: number;
  snapshot_every: number;
  seed: number;
};
