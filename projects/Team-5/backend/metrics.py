"""Quality metrics for image and signal recovery.

PSNR and SSIM use skimage's reference implementations. SNR is defined for 1D
signals as 10 log10(||x||^2 / ||x - x_est||^2).
"""
from __future__ import annotations

import numpy as np
from skimage.metrics import peak_signal_noise_ratio, structural_similarity


def mse(x: np.ndarray, y: np.ndarray) -> float:
    return float(np.mean((x - y) ** 2))


def psnr(x_true: np.ndarray, x_est: np.ndarray, data_range: float = 1.0) -> float:
    """Peak signal-to-noise ratio in dB. `data_range` is the dynamic range (1.0 for [0,1])."""
    return float(peak_signal_noise_ratio(x_true, x_est, data_range=data_range))


def ssim(x_true: np.ndarray, x_est: np.ndarray, data_range: float = 1.0) -> float:
    """Structural similarity index (skimage)."""
    return float(structural_similarity(x_true, x_est, data_range=data_range))


def snr(x_true: np.ndarray, x_est: np.ndarray) -> float:
    """Signal-to-noise ratio in dB: 10 log10(||x||^2 / ||x - x_est||^2)."""
    sig_power = float(np.sum(x_true ** 2))
    err_power = float(np.sum((x_true - x_est) ** 2))
    if err_power == 0.0:
        return float('inf')
    return 10.0 * float(np.log10(sig_power / err_power))
