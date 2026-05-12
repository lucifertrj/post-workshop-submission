"""ISTA and FISTA for the LASSO problem (sparse recovery from compressed
measurements).

Problem: y = A x_true + n, with x_true sparse (most coefficients zero) and A
a non-orthogonal sensing operator (e.g., random Gaussian). We solve

    F(x) = (1/2)||A x - y||^2 + lambda * ||x||_1

with f(x) = (1/2)||A x - y||^2 (gradient ∇f = A^T (A x - y), Lipschitz
constant L = ||A^T A||_2) and g(x) = lambda * ||x||_1 (prox = soft thresh).

Note: pure denoising (A = I) or wavelet ℓ1 with an orthogonal basis has a
closed-form one-step solution by soft thresholding — there is no iteration
story. The non-orthogonal A here is what makes ISTA vs FISTA non-trivial,
and is the canonical FISTA showcase from Beck & Teboulle (2009).

References:
    Daubechies-Defrise-De Mol (2004); Beck & Teboulle (2009).
    Tibshirani (1996), "Regression Shrinkage and Selection via the Lasso".
"""
from __future__ import annotations

from typing import Callable, Iterator

import numpy as np

from prox import soft_threshold
from operators import estimate_lipschitz
from metrics import mse, snr


def naive_lasso(y: np.ndarray, A_matrix: np.ndarray) -> np.ndarray:
    """Min-norm least-squares solution — the "no optimizer / no prior" baseline.

    For the underdetermined system y = A x with A of shape (M, N), M < N,
    there are infinitely many exact solutions; `np.linalg.lstsq` returns
    the minimum L2-norm one (Moore-Penrose pseudoinverse). This solution
    is DENSE — energy spread across all coordinates — so it does not
    recover the K-sparse truth. Demonstrates why the ℓ1 prior is essential.
    """
    x_naive, *_ = np.linalg.lstsq(A_matrix, y, rcond=None)
    return x_naive


def _info(k: int, x: np.ndarray, x_true: np.ndarray, A_apply: Callable,
          y: np.ndarray, lam: float, snap_every: int, max_iter: int) -> dict:
    fidelity = 0.5 * float(np.sum((A_apply(x) - y) ** 2))
    obj = fidelity + lam * float(np.sum(np.abs(x)))
    sparsity = float(np.mean(x == 0))
    snap = x.copy() if (k % snap_every == 0 or k == max_iter - 1) else None
    return {
        'k': k,
        'obj': obj,
        'snr': snr(x_true, x),
        'mse': mse(x_true, x),
        'sparsity': sparsity,
        'x': snap,
    }


def ista_denoise_iter(y: np.ndarray, x_true: np.ndarray,
                      A_apply: Callable, A_adjoint: Callable, *,
                      lam: float, L: float | None = None,
                      max_iter: int = 500, snapshot_every: int = 20) -> Iterator[dict]:
    """ISTA generator for LASSO. Cold-start from x = 0 (avoids fixed-point traps)."""
    if L is None:
        L = estimate_lipschitz(A_apply, A_adjoint, x_true.shape)
    alpha = 1.0 / L

    x = np.zeros_like(x_true, dtype=np.float64)
    for k in range(max_iter):
        grad = A_adjoint(A_apply(x) - y)
        x = soft_threshold(x - alpha * grad, alpha * lam)
        yield _info(k, x, x_true, A_apply, y, lam, snapshot_every, max_iter)


def fista_denoise_iter(y: np.ndarray, x_true: np.ndarray,
                       A_apply: Callable, A_adjoint: Callable, *,
                       lam: float, L: float | None = None,
                       max_iter: int = 500, snapshot_every: int = 20) -> Iterator[dict]:
    """FISTA generator for LASSO with momentum sequence t_k (Beck-Teboulle)."""
    if L is None:
        L = estimate_lipschitz(A_apply, A_adjoint, x_true.shape)
    alpha = 1.0 / L

    x = np.zeros_like(x_true, dtype=np.float64)
    z = x.copy()
    t = 1.0
    for k in range(max_iter):
        grad = A_adjoint(A_apply(z) - y)
        x_new = soft_threshold(z - alpha * grad, alpha * lam)
        t_new = 0.5 * (1.0 + np.sqrt(1.0 + 4.0 * t * t))
        z = x_new + ((t - 1.0) / t_new) * (x_new - x)
        x, t = x_new, t_new
        yield _info(k, x, x_true, A_apply, y, lam, snapshot_every, max_iter)


def _collect(it: Iterator[dict]) -> dict:
    h: dict = {'k': [], 'obj': [], 'snr': [], 'mse': [], 'sparsity': [], 'x_snapshots': []}
    for info in it:
        for key in ('k', 'obj', 'snr', 'mse', 'sparsity'):
            h[key].append(info[key])
        if info['x'] is not None:
            h['x_snapshots'].append(info['x'])
    return h


def ista_denoise(*args, **kw) -> dict:
    return _collect(ista_denoise_iter(*args, **kw))


def fista_denoise(*args, **kw) -> dict:
    return _collect(fista_denoise_iter(*args, **kw))
