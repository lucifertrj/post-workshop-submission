"""Forward operators (blur, wavelet) and Lipschitz constant estimation.

For ISTA/FISTA on f(x) = (1/2)||Ax - y||^2, we need:
    A (apply), A^T (adjoint), and L = ||A^T A||_2 (Lipschitz of grad f).

Image deblurring uses a Gaussian blur with periodic boundary conditions, so
A is its own adjoint and L is found by power iteration.

Signal denoising uses an orthogonal wavelet transform (periodization mode),
so the synthesis op W^T satisfies ||W^T||_2 = 1 and L = 1 directly.
"""
from __future__ import annotations

from typing import Callable

import numpy as np
import pywt
from scipy.ndimage import gaussian_filter


# --------------------------------------------------------------- 2D blur op

def make_blur_op(sigma: float) -> tuple[Callable, Callable]:
    """Return (apply, adjoint) for periodic-BC Gaussian blur of a 2D array.

    The Gaussian kernel is symmetric, and `mode='wrap'` gives circular
    convolution, so the adjoint operator equals the apply operator.
    """
    def apply(x: np.ndarray) -> np.ndarray:
        return gaussian_filter(x, sigma=sigma, mode='wrap').astype(np.float64)

    return apply, apply


# --------------------------------------------------------- 1D wavelet ops

def make_wavelet_ops(
    signal_length: int,
    wavelet: str = 'db4',
    level: int | None = None,
) -> tuple[Callable, Callable, int]:
    """Return (analysis, synthesis, coef_size) for the 1D DWT.

    `analysis(x) -> c`: forward wavelet transform W, returns flat coef array.
    `synthesis(c) -> x`: inverse transform W^T, returns time-domain signal.

    Uses 'periodization' boundary handling so the transform is orthogonal:
    W^T = W^{-1} and ||W||_2 = ||W^T||_2 = 1, giving L = 1 in the outer loop.
    """
    if level is None:
        level = pywt.dwt_max_level(signal_length, wavelet)

    dummy = np.zeros(signal_length)
    coeffs0 = pywt.wavedec(dummy, wavelet, level=level, mode='periodization')
    flat0, slices = pywt.coeffs_to_array(coeffs0)
    coef_size = int(flat0.size)

    def analysis(x: np.ndarray) -> np.ndarray:
        cs = pywt.wavedec(x, wavelet, level=level, mode='periodization')
        flat, _ = pywt.coeffs_to_array(cs)
        return flat

    def synthesis(c: np.ndarray) -> np.ndarray:
        cs = pywt.array_to_coeffs(c, slices, output_format='wavedec')
        return pywt.waverec(cs, wavelet, mode='periodization')[:signal_length]

    return analysis, synthesis, coef_size


# ----------------------------------------- Random sensing op (LASSO / CS)

def make_random_measurement_op(
    M: int, N: int, seed: int = 0,
) -> tuple[Callable, Callable, float, np.ndarray]:
    """Random Gaussian sensing matrix A of shape (M, N).

    Returns (apply, adjoint, L, A_matrix) where L = ||A^T A||_2 = sigma_max(A)^2.
    The dense matrix is also returned so callers can compute non-iterative
    baselines (e.g., the lstsq pseudoinverse "no optimizer" reference).
    Columns are scaled by 1/sqrt(M) so each column has unit norm in
    expectation — the standard compressive-sensing normalization.

    Used for the LASSO demo:  minimize  (1/2)||A x - y||^2 + lambda * ||x||_1.
    """
    rng = np.random.default_rng(seed)
    A = rng.standard_normal((M, N)) / np.sqrt(M)

    def apply(x: np.ndarray) -> np.ndarray:
        return A @ x

    def adjoint(z: np.ndarray) -> np.ndarray:
        return A.T @ z

    sigma_max = float(np.linalg.norm(A, ord=2))
    return apply, adjoint, sigma_max ** 2, A


# ------------------------------------------------------ Lipschitz estimator

def estimate_lipschitz(
    apply: Callable,
    adjoint: Callable,
    shape: tuple,
    n_iter: int = 30,
    seed: int = 0,
    rel_tol: float = 1e-6,
) -> float:
    """Power iteration on A^T A to estimate L = sigma_max(A)^2.

    For ISTA/FISTA on f(x) = (1/2)||Ax - y||^2, ∇f = A^T(Ax - y) is L-Lipschitz
    with L = ||A^T A||_2 = sigma_max(A)^2.
    """
    rng = np.random.default_rng(seed)
    x = rng.standard_normal(shape)
    x /= np.linalg.norm(x)
    L_prev = 0.0
    for _ in range(n_iter):
        y = adjoint(apply(x))
        L = float(np.linalg.norm(y))
        if L < 1e-12:
            return 0.0
        if abs(L - L_prev) / max(L, 1e-12) < rel_tol:
            return L
        x = y / L
        L_prev = L
    return L
