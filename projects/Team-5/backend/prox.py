"""Proximal operators used by ISTA and FISTA.

For composite minimization F(x) = f(x) + g(x), each iteration applies
prox_{alpha*g} after the gradient step on f. We use two such prox operators:

    soft_threshold:  prox of g(x) = ||x||_1, used for sparse signal recovery
                     in a wavelet basis.
    tv_prox:         prox of g(x) = TV(x), used for image deblurring.
                     Wraps Chambolle's dual algorithm via skimage.

References:
    Parikh & Boyd (2014), "Proximal Algorithms".
    Chambolle (2004), "An algorithm for total variation minimization".
"""
from __future__ import annotations

import numpy as np
from skimage.restoration import denoise_tv_chambolle


def soft_threshold(x: np.ndarray, threshold: float) -> np.ndarray:
    """Element-wise soft thresholding: prox of g(x) = threshold * ||x||_1.

    S_t(x) = sign(x) * max(|x| - t, 0).
    """
    return np.sign(x) * np.maximum(np.abs(x) - threshold, 0.0)


def tv_prox(x: np.ndarray, weight: float, inner_iter: int = 50) -> np.ndarray:
    """Prox of g(x) = weight * TV(x) for a 2D grayscale image.

    `weight` here equals alpha * lambda from the outer ISTA/FISTA call site.
    Inner iteration count of 50 trades inner accuracy for outer-loop speed
    (default skimage uses 200, which is overkill when called once per outer step).
    """
    return denoise_tv_chambolle(x, weight=weight, max_num_iter=inner_iter)
