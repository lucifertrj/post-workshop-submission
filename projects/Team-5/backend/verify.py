"""End-to-end sanity check.

Runs ISTA and FISTA on:
    1. Cameraman image deblurring with TV regularization
       (canonical FISTA showcase from Beck-Teboulle 2009)
    2. Sparse signal recovery via LASSO from compressed Gaussian measurements
       (the canonical compressive-sensing benchmark for FISTA)

Prints metrics (PSNR, SSIM, SNR), iterations to reach successively tighter
fractions of the initial objective gap, and saves convergence + comparison
plots to _verify_outputs/.

This is the HARD GATE: if FISTA isn't visibly faster than ISTA on these plots,
something is wrong with the math and we don't move on to the FastAPI / frontend.

Run:
    backend/.venv/Scripts/python backend/verify.py
"""
from __future__ import annotations

import os
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from skimage import data
from skimage.transform import resize

# Make sibling modules importable regardless of where this is launched from
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from operators import make_blur_op, make_random_measurement_op  # noqa: E402
from deblur import ista_deblur, fista_deblur  # noqa: E402
from denoise import ista_denoise, fista_denoise  # noqa: E402
from metrics import psnr, snr  # noqa: E402


OUTDIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_verify_outputs')
os.makedirs(OUTDIR, exist_ok=True)


def iters_to_target(obj_history: list[float], target: float, fallback: int) -> int:
    """First k with obj <= target, or fallback if never reached."""
    for k, o in enumerate(obj_history):
        if o <= target:
            return k
    return fallback


def report_speedup(h_ista: dict, h_fista: dict, max_iter: int) -> None:
    """Print iters-to-target speedup at multiple precision levels.

    With easy problems (well-conditioned A, large lambda) both algos plateau
    fast and the speedup at loose tolerance is small. The asymptotic O(1/k^2)
    advantage of FISTA shows up at TIGHT tolerance — that's the headline.
    """
    obj_min = min(min(h_ista['obj']), min(h_fista['obj']))
    obj0 = h_ista['obj'][0]
    gap0 = obj0 - obj_min
    print('\nIters to reach gap-to-best-obj <= fraction of initial gap:')
    print(f'{"reduction":>12s}  {"ISTA":>6s}  {"FISTA":>6s}  {"speedup":>8s}')
    for frac in (0.1, 0.01, 0.001, 0.0001):
        target = obj_min + frac * gap0
        ki = iters_to_target(h_ista['obj'], target, max_iter)
        kf = iters_to_target(h_fista['obj'], target, max_iter)
        speedup = ki / max(kf, 1)
        tag = ' (capped)' if (ki >= max_iter or kf >= max_iter) else ''
        print(f'{(1-frac)*100:>10.2f}%  {ki:>6d}  {kf:>6d}  {speedup:>7.1f}x{tag}')


def deblur_demo(sigma_blur: float = 2.5, noise_std: float = 0.01,
                lam: float = 0.003, max_iter: int = 500) -> None:
    print('\n' + '=' * 60)
    print('DEMO 1: Image deblurring (Cameraman)')
    print('=' * 60)

    x_true = data.camera().astype(np.float64) / 255.0
    x_true = resize(x_true, (256, 256), anti_aliasing=True)

    A, _ = make_blur_op(sigma_blur)
    rng = np.random.default_rng(0)
    y = A(x_true) + noise_std * rng.standard_normal(x_true.shape)
    y = np.clip(y, 0.0, 1.0)

    print(f'Image: 256x256 grayscale, blur sigma={sigma_blur}, noise std={noise_std}')
    print(f'Lambda: {lam}, max_iter: {max_iter}')

    print('\nRunning ISTA...')
    h_ista = ista_deblur(y, x_true, sigma=sigma_blur, lam=lam,
                         max_iter=max_iter, snapshot_every=max_iter)
    print('Running FISTA...')
    h_fista = fista_deblur(y, x_true, sigma=sigma_blur, lam=lam,
                           max_iter=max_iter, snapshot_every=max_iter)

    psnr_in = psnr(x_true, np.clip(y, 0, 1))
    print(f'\nPSNR (blurry):  {psnr_in:6.2f} dB')
    print(f'PSNR (ISTA):    {h_ista["psnr"][-1]:6.2f} dB')
    print(f'PSNR (FISTA):   {h_fista["psnr"][-1]:6.2f} dB')

    report_speedup(h_ista, h_fista, max_iter)

    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    axes[0].semilogy(h_ista['obj'], label='ISTA', linewidth=2)
    axes[0].semilogy(h_fista['obj'], label='FISTA', linewidth=2)
    axes[0].set_xlabel('Iteration k'); axes[0].set_ylabel('F(x_k) [log]')
    axes[0].set_title(f'Objective (lambda={lam})')
    axes[0].legend(); axes[0].grid(alpha=0.3)
    axes[1].plot(h_ista['psnr'], label='ISTA', linewidth=2)
    axes[1].plot(h_fista['psnr'], label='FISTA', linewidth=2)
    axes[1].axhline(psnr_in, color='gray', linestyle=':', label=f'blurry input ({psnr_in:.2f} dB)')
    axes[1].set_xlabel('Iteration k'); axes[1].set_ylabel('PSNR (dB)')
    axes[1].set_title('Recovery quality')
    axes[1].legend(loc='lower right'); axes[1].grid(alpha=0.3)
    fig.suptitle('Image deblurring: ISTA vs FISTA')
    fig.tight_layout()
    fig.savefig(os.path.join(OUTDIR, 'deblur_convergence.png'), dpi=120)
    plt.close(fig)

    x_ista = h_ista['x_snapshots'][-1]
    x_fista = h_fista['x_snapshots'][-1]
    fig, axes = plt.subplots(1, 4, figsize=(14, 4))
    titles = [
        'Original',
        f'Blurry + noisy (PSNR {psnr_in:.1f} dB)',
        f'ISTA (PSNR {h_ista["psnr"][-1]:.1f} dB)',
        f'FISTA (PSNR {h_fista["psnr"][-1]:.1f} dB)',
    ]
    for ax, im, title in zip(axes, [x_true, y, x_ista, x_fista], titles):
        ax.imshow(im, cmap='gray', vmin=0, vmax=1)
        ax.set_title(title)
        ax.axis('off')
    fig.tight_layout()
    fig.savefig(os.path.join(OUTDIR, 'deblur_comparison.png'), dpi=120)
    plt.close(fig)

    print(f'\nSaved: {OUTDIR}/deblur_convergence.png')
    print(f'Saved: {OUTDIR}/deblur_comparison.png')


def make_sparse_signal(n: int = 1024, k: int = 20, seed: int = 0) -> np.ndarray:
    """K-sparse signal of length n: K random non-zero spikes, rest zero."""
    rng = np.random.default_rng(seed)
    x = np.zeros(n, dtype=np.float64)
    idx = rng.choice(n, size=k, replace=False)
    x[idx] = rng.standard_normal(k) * 2.0
    return x


def denoise_demo(N: int = 1024, M: int = 400, K: int = 20,
                 noise_std: float = 0.01, lam: float = 0.05,
                 max_iter: int = 500) -> None:
    print('\n' + '=' * 60)
    print('DEMO 2: Sparse signal recovery via LASSO (compressed sensing)')
    print('=' * 60)

    x_true = make_sparse_signal(N, K, seed=0)
    A_apply, A_adjoint, L, _A_matrix = make_random_measurement_op(M, N, seed=1)
    rng = np.random.default_rng(2)
    y_clean = A_apply(x_true)
    y = y_clean + noise_std * rng.standard_normal(M)

    print(f'Signal: N={N}, true sparsity K={K} ({100*K/N:.1f}% non-zero)')
    print(f'Sensing: M={M} measurements (compression M/N={M/N:.2f})')
    print(f'Noise std={noise_std}, Lambda={lam}, max_iter={max_iter}')
    print(f'Lipschitz L={L:.4f}, step alpha=1/L={1/L:.4f}')

    print('\nRunning ISTA...')
    h_ista = ista_denoise(y, x_true, A_apply, A_adjoint, lam=lam, L=L,
                          max_iter=max_iter, snapshot_every=max_iter)
    print('Running FISTA...')
    h_fista = fista_denoise(y, x_true, A_apply, A_adjoint, lam=lam, L=L,
                            max_iter=max_iter, snapshot_every=max_iter)

    print(f'\nSNR (recovered ISTA):  {h_ista["snr"][-1]:6.2f} dB')
    print(f'SNR (recovered FISTA): {h_fista["snr"][-1]:6.2f} dB')
    print(f'Sparsity (ISTA):  {100 * h_ista["sparsity"][-1]:5.1f}% coefs zero')
    print(f'Sparsity (FISTA): {100 * h_fista["sparsity"][-1]:5.1f}% coefs zero')
    print(f'Sparsity (truth): {100 * (1 - K/N):5.1f}% coefs zero')

    report_speedup(h_ista, h_fista, max_iter)

    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    axes[0].semilogy(h_ista['obj'], label='ISTA', linewidth=2)
    axes[0].semilogy(h_fista['obj'], label='FISTA', linewidth=2)
    axes[0].set_xlabel('Iteration k'); axes[0].set_ylabel('F(x_k) [log]')
    axes[0].set_title(f'Objective (lambda={lam})')
    axes[0].legend(); axes[0].grid(alpha=0.3)
    axes[1].plot(h_ista['snr'], label='ISTA', linewidth=2)
    axes[1].plot(h_fista['snr'], label='FISTA', linewidth=2)
    axes[1].set_xlabel('Iteration k'); axes[1].set_ylabel('SNR (dB)')
    axes[1].set_title('Recovery quality')
    axes[1].legend(loc='lower right'); axes[1].grid(alpha=0.3)
    fig.suptitle('Sparse recovery (LASSO): ISTA vs FISTA')
    fig.tight_layout()
    fig.savefig(os.path.join(OUTDIR, 'denoise_convergence.png'), dpi=120)
    plt.close(fig)

    x_ista = h_ista['x_snapshots'][-1]
    x_fista = h_fista['x_snapshots'][-1]
    fig, axes = plt.subplots(3, 1, figsize=(10, 8))
    nz = np.flatnonzero(x_true)
    axes[0].vlines(nz, 0, x_true[nz], colors='black', linewidth=1.5)
    axes[0].axhline(0, color='gray', linewidth=0.5)
    axes[0].set_title(f'True sparse signal (N={N}, K={K} non-zeros)')
    axes[0].set_xlim(0, N)
    axes[1].plot(y, color='gray', linewidth=0.6)
    axes[1].set_title(f'Compressed noisy measurements (M={M})')
    axes[1].set_xlim(0, M)
    axes[2].vlines(nz, 0, x_true[nz], colors='black', linewidth=1.5,
                   alpha=0.6, label='Original')
    axes[2].plot(x_ista, color='C0', linewidth=0.8, alpha=0.7,
                 label=f'ISTA (SNR {h_ista["snr"][-1]:.1f} dB)')
    axes[2].plot(x_fista, color='C1', linewidth=0.8, linestyle='--', alpha=0.7,
                 label=f'FISTA (SNR {h_fista["snr"][-1]:.1f} dB)')
    axes[2].axhline(0, color='gray', linewidth=0.5)
    axes[2].set_title('Recovered spikes')
    axes[2].set_xlim(0, N)
    axes[2].legend(loc='upper right')
    for a in axes:
        a.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(OUTDIR, 'denoise_comparison.png'), dpi=120)
    plt.close(fig)

    print(f'\nSaved: {OUTDIR}/denoise_convergence.png')
    print(f'Saved: {OUTDIR}/denoise_comparison.png')


if __name__ == '__main__':
    deblur_demo()
    denoise_demo()
    print('\n' + '=' * 60)
    print('VERIFICATION COMPLETE — check _verify_outputs/ for plots.')
    print('=' * 60)
