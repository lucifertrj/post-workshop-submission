"""ISTA and FISTA for image deblurring with isotropic TV regularization.

Problem: y = A x_true + n, with A a Gaussian blur op (periodic BC) and n
Gaussian noise. We solve the composite minimization

    F(x) = (1/2)||A x - y||^2 + lambda * TV(x)

f(x) = (1/2)||A x - y||^2 has Lipschitz gradient ∇f = A^T (A x - y) with
constant L = ||A^T A||_2 (estimated via power iteration). Step size alpha = 1/L.

Both ISTA and FISTA are exposed as generators (per-iter info, for SSE) and
as eager run functions returning a `history` dict (for notebooks).

Also exposes `naive_deblur`: a non-iterative FFT-based inverse filter that
serves as the "no optimizer" baseline. Without regularization, noise at
frequencies where the blur kernel's transfer function is small gets
amplified — visible as ringing and high-frequency noise. PSNR is typically
*worse* than the blurry input. This is the textbook motivation for
regularized iterative methods.

Reference: Beck & Teboulle (2009), SIAM J. Imaging Sciences 2(1), 183-202.
"""
from __future__ import annotations

from typing import Callable, Iterator

import numpy as np
from scipy.ndimage import gaussian_filter

from prox import tv_prox
from operators import make_blur_op, estimate_lipschitz
from metrics import mse, psnr, ssim


def naive_deblur(y: np.ndarray, sigma: float) -> np.ndarray:
    """FFT-based inverse filter — the "no optimizer / no regularizer" baseline.

    Computes  x_hat = IDFT( DFT(y) / DFT(k) )  where k is the periodic-BC
    Gaussian kernel that defines the blur operator A. For a true noise-free
    observation y = A x*, this would recover x* exactly; for noisy y the
    division by small high-frequency values in DFT(k) amplifies noise.
    Numerically guarded by flooring |DFT(k)| at machine epsilon.
    """
    H, W = y.shape
    delta = np.zeros((H, W), dtype=np.float64)
    delta[0, 0] = 1.0
    kernel = gaussian_filter(delta, sigma=sigma, mode='wrap')
    K = np.fft.fft2(kernel)
    K_safe = np.where(np.abs(K) < 1e-12, 1e-12 + 0j, K)
    Y = np.fft.fft2(y)
    return np.real(np.fft.ifft2(Y / K_safe))


def isotropic_tv(x: np.ndarray) -> float:
    """Discrete isotropic TV used by Chambolle's algorithm (matches skimage)."""
    dx = np.diff(x, axis=1)[:-1, :]
    dy = np.diff(x, axis=0)[:, :-1]
    return float(np.sum(np.sqrt(dx * dx + dy * dy)))


def _info(k: int, x: np.ndarray, x_true: np.ndarray, A: Callable,
          y: np.ndarray, lam: float, snap_every: int, max_iter: int) -> dict:
    fidelity = 0.5 * float(np.sum((A(x) - y) ** 2))
    obj = fidelity + lam * isotropic_tv(x)
    x_clipped = np.clip(x, 0.0, 1.0)
    snap = x_clipped.copy() if (k % snap_every == 0 or k == max_iter - 1) else None
    return {
        'k': k,
        'obj': obj,
        'psnr': psnr(x_true, x_clipped),
        'ssim': ssim(x_true, x_clipped),
        'mse': mse(x_true, x_clipped),
        'x': snap,
    }


def ista_deblur_iter(y: np.ndarray, x_true: np.ndarray, *,
                     sigma: float, lam: float,
                     max_iter: int = 200, snapshot_every: int = 10) -> Iterator[dict]:
    """ISTA generator: yields per-iteration dict including obj, PSNR, SSIM, MSE."""
    A, At = make_blur_op(sigma)
    L = estimate_lipschitz(A, At, y.shape)
    alpha = 1.0 / L

    x = y.copy()
    for k in range(max_iter):
        grad = At(A(x) - y)
        x = tv_prox(x - alpha * grad, weight=alpha * lam)
        yield _info(k, x, x_true, A, y, lam, snapshot_every, max_iter)


def fista_deblur_iter(y: np.ndarray, x_true: np.ndarray, *,
                      sigma: float, lam: float,
                      max_iter: int = 200, snapshot_every: int = 10) -> Iterator[dict]:
    """FISTA generator with momentum sequence t_k (Beck-Teboulle 2009).

    Variables follow the paper: z is y_k (the momentum extrapolation point),
    distinct from the observation y.
    """
    A, At = make_blur_op(sigma)
    L = estimate_lipschitz(A, At, y.shape)
    alpha = 1.0 / L

    x = y.copy()
    z = x.copy()      # y_1 = x_0
    t = 1.0           # t_1
    for k in range(max_iter):
        grad = At(A(z) - y)
        x_new = tv_prox(z - alpha * grad, weight=alpha * lam)
        t_new = 0.5 * (1.0 + np.sqrt(1.0 + 4.0 * t * t))
        z = x_new + ((t - 1.0) / t_new) * (x_new - x)
        x, t = x_new, t_new
        yield _info(k, x, x_true, A, y, lam, snapshot_every, max_iter)


def _collect(it: Iterator[dict]) -> dict:
    h: dict = {'k': [], 'obj': [], 'psnr': [], 'ssim': [], 'mse': [], 'x_snapshots': []}
    for info in it:
        for key in ('k', 'obj', 'psnr', 'ssim', 'mse'):
            h[key].append(info[key])
        if info['x'] is not None:
            h['x_snapshots'].append(info['x'])
    return h


def ista_deblur(y: np.ndarray, x_true: np.ndarray, **kw) -> dict:
    return _collect(ista_deblur_iter(y, x_true, **kw))


def fista_deblur(y: np.ndarray, x_true: np.ndarray, **kw) -> dict:
    return _collect(fista_deblur_iter(y, x_true, **kw))
