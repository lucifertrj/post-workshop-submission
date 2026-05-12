// Typed wrappers around the FastAPI backend. All endpoints are GET so the
// browser's EventSource works directly for SSE (no need for fetch+ReadableStream).

import type {
  ImagePresetInfo,
  SignalPresetInfo,
  DeblurRunParams,
  DenoiseRunParams,
} from './types';

export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? 'http://localhost:8000';

export async function listImagePresets(): Promise<ImagePresetInfo[]> {
  const r = await fetch(`${API_BASE}/presets/image`);
  if (!r.ok) throw new Error(`presets/image: ${r.status}`);
  return r.json();
}

export async function listSignalPresets(): Promise<SignalPresetInfo[]> {
  const r = await fetch(`${API_BASE}/presets/signal`);
  if (!r.ok) throw new Error(`presets/signal: ${r.status}`);
  return r.json();
}

export async function previewImage(name: string): Promise<string> {
  const r = await fetch(`${API_BASE}/preview/image/${name}`);
  if (!r.ok) throw new Error(`preview/image/${name}: ${r.status}`);
  const { png_b64 } = (await r.json()) as { png_b64: string };
  return `data:image/png;base64,${png_b64}`;
}

export async function previewSignal(name: string): Promise<number[]> {
  const r = await fetch(`${API_BASE}/preview/signal/${name}`);
  if (!r.ok) throw new Error(`preview/signal/${name}: ${r.status}`);
  const { data } = (await r.json()) as { data: number[] };
  return data;
}

export function deblurStreamUrl(p: DeblurRunParams): string {
  const q = new URLSearchParams({
    name: p.name,
    algo: p.algo,
    lam: String(p.lam),
    sigma: String(p.sigma),
    noise: String(p.noise),
    max_iter: String(p.max_iter),
    snapshot_every: String(p.snapshot_every),
  });
  return `${API_BASE}/run/deblur/stream?${q.toString()}`;
}

export function denoiseStreamUrl(p: DenoiseRunParams): string {
  const q = new URLSearchParams({
    name: p.name,
    algo: p.algo,
    lam: String(p.lam),
    M: String(p.M),
    noise: String(p.noise),
    max_iter: String(p.max_iter),
    snapshot_every: String(p.snapshot_every),
    seed: String(p.seed),
  });
  return `${API_BASE}/run/denoise/stream?${q.toString()}`;
}
