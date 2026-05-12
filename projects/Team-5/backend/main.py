"""FastAPI app for ISTA/FISTA demos with SSE streaming.

Endpoints:
    GET /health                    -> {"status": "ok"}
    GET /presets/image             -> [{"name", "shape"}, ...]
    GET /presets/signal            -> [{"name", "length"}, ...]
    GET /preview/image/{name}      -> {"png_b64"}
    GET /preview/signal/{name}     -> {"data": [...]}
    GET /run/deblur/stream?...     -> SSE: init, iter*, done
    GET /run/denoise/stream?...    -> SSE: init, iter*, done

Run from project root:
    backend/.venv/Scripts/python -m uvicorn backend.main:app --reload --port 8000

Or, if launched directly:
    cd backend && .venv/Scripts/python -m uvicorn main:app --reload --port 8000

Frontend on http://localhost:3000 is allowed via CORS.
"""
from __future__ import annotations

import asyncio
import base64
import io
import json
import os
import sys
from typing import AsyncIterator, Literal

# Make sibling backend modules importable when launched from project root
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import numpy as np
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
from skimage import data
from skimage.transform import resize
from sse_starlette.sse import EventSourceResponse

from operators import make_blur_op, make_random_measurement_op
from deblur import ista_deblur_iter, fista_deblur_iter, naive_deblur
from denoise import ista_denoise_iter, fista_denoise_iter, naive_lasso
from metrics import psnr, ssim, snr, mse


app = FastAPI(title='ISTA/FISTA Demo')

app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost:3000', 'http://127.0.0.1:3000'],
    allow_methods=['*'],
    allow_headers=['*'],
)


# ----------------------------------------------------------------------
# Presets — loaded once at startup
# ----------------------------------------------------------------------

_IMAGE_PRESETS: dict[str, np.ndarray] = {}
_SIGNAL_PRESETS: dict[str, np.ndarray] = {}


def _load_image_presets() -> None:
    """Load skimage built-in images, normalized to [0,1] grayscale 256x256."""
    sources = [
        ('cameraman', data.camera),
        ('astronaut', lambda: data.astronaut().mean(axis=2)),
        ('coins',     data.coins),
        ('moon',      data.moon),
    ]
    for name, fn in sources:
        arr = np.asarray(fn(), dtype=np.float64)
        if arr.max() > 1.0:
            arr = arr / 255.0
        if arr.shape != (256, 256):
            arr = resize(arr, (256, 256), anti_aliasing=True)
        _IMAGE_PRESETS[name] = arr.astype(np.float64)


def _make_sparse(N: int, K: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    x = np.zeros(N, dtype=np.float64)
    idx = rng.choice(N, size=K, replace=False)
    x[idx] = rng.standard_normal(K) * 2.0
    return x


def _load_signal_presets() -> None:
    _SIGNAL_PRESETS['spikes_20']  = _make_sparse(1024, 20,  seed=0)
    _SIGNAL_PRESETS['spikes_40']  = _make_sparse(1024, 40,  seed=1)
    _SIGNAL_PRESETS['spikes_80']  = _make_sparse(1024, 80,  seed=2)


_load_image_presets()
_load_signal_presets()


# ----------------------------------------------------------------------
# Encoding helpers
# ----------------------------------------------------------------------

def _img_to_png_b64(arr: np.ndarray) -> str:
    """Encode a float [0,1] grayscale array as a base64 PNG string."""
    img = Image.fromarray(np.clip(arr * 255.0, 0, 255).astype(np.uint8))
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return base64.b64encode(buf.getvalue()).decode('ascii')


# ----------------------------------------------------------------------
# Discovery / preview routes
# ----------------------------------------------------------------------

@app.get('/health')
def health():
    return {'status': 'ok'}


@app.get('/presets/image')
def list_image_presets():
    return [{'name': k, 'shape': list(v.shape)} for k, v in _IMAGE_PRESETS.items()]


@app.get('/presets/signal')
def list_signal_presets():
    return [{'name': k, 'length': len(v)} for k, v in _SIGNAL_PRESETS.items()]


@app.get('/preview/image/{name}')
def preview_image(name: str):
    if name not in _IMAGE_PRESETS:
        raise HTTPException(404, f'Image preset {name!r} not found')
    return {'png_b64': _img_to_png_b64(_IMAGE_PRESETS[name])}


@app.get('/preview/signal/{name}')
def preview_signal(name: str):
    if name not in _SIGNAL_PRESETS:
        raise HTTPException(404, f'Signal preset {name!r} not found')
    return {'data': _SIGNAL_PRESETS[name].tolist()}


# ----------------------------------------------------------------------
# SSE streams
# ----------------------------------------------------------------------

_SSE_HEADERS = {
    'Cache-Control': 'no-cache, no-transform',
    'X-Accel-Buffering': 'no',
}


@app.get('/run/deblur/stream')
async def stream_deblur(
    name: str = Query(..., description='Preset image name'),
    algo: Literal['ista', 'fista'] = Query('fista'),
    lam: float = Query(0.003, ge=1e-6, le=1.0, description='Regularization strength'),
    sigma: float = Query(2.5, ge=0.5, le=5.0, description='Gaussian blur std-dev'),
    noise: float = Query(0.01, ge=0.0, le=0.2, description='Observation noise std'),
    max_iter: int = Query(200, ge=10, le=1000),
    snapshot_every: int = Query(5, ge=1, le=100, description='Push image snapshot every K iters'),
):
    if name not in _IMAGE_PRESETS:
        raise HTTPException(404, f'Preset {name!r} not found')

    x_true = _IMAGE_PRESETS[name]
    A, _ = make_blur_op(sigma)
    rng = np.random.default_rng(42)
    y = A(x_true) + noise * rng.standard_normal(x_true.shape)
    y = np.clip(y, 0.0, 1.0)
    psnr_in = psnr(x_true, y)

    # Naive direct-inverse baseline ("no optimizer"). Computed once per run
    # config; identical for ISTA and FISTA streams that share these params.
    x_naive = np.clip(naive_deblur(y, sigma), 0.0, 1.0)
    baseline_psnr = psnr(x_true, x_naive)
    baseline_ssim = ssim(x_true, x_naive)
    baseline_mse = mse(x_true, x_naive)

    iter_fn = ista_deblur_iter if algo == 'ista' else fista_deblur_iter

    async def event_gen() -> AsyncIterator[dict]:
        yield {
            'event': 'init',
            'data': json.dumps({
                'shape': list(x_true.shape),
                'x_true_png': _img_to_png_b64(x_true),
                'y_png':      _img_to_png_b64(y),
                'psnr_input': psnr_in,
                'baseline_png':  _img_to_png_b64(x_naive),
                'baseline_psnr': baseline_psnr,
                'baseline_ssim': baseline_ssim,
                'baseline_mse':  baseline_mse,
                'algo':       algo,
                'max_iter':   max_iter,
            }),
        }
        for info in iter_fn(y, x_true, sigma=sigma, lam=lam,
                            max_iter=max_iter, snapshot_every=snapshot_every):
            payload = {k: v for k, v in info.items() if k != 'x'}
            if info['x'] is not None:
                payload['x_png'] = _img_to_png_b64(info['x'])
            yield {'event': 'iter', 'data': json.dumps(payload)}
            await asyncio.sleep(0)
        yield {'event': 'done', 'data': '{}'}

    return EventSourceResponse(event_gen(), headers=_SSE_HEADERS)


@app.get('/run/denoise/stream')
async def stream_denoise(
    name: str = Query(..., description='Preset signal name'),
    algo: Literal['ista', 'fista'] = Query('fista'),
    lam: float = Query(0.05, ge=1e-6, le=1.0, description='ℓ1 regularization strength'),
    M: int = Query(400, ge=50, le=2000, description='Number of measurements'),
    noise: float = Query(0.01, ge=0.0, le=0.2),
    max_iter: int = Query(500, ge=10, le=2000),
    snapshot_every: int = Query(10, ge=1, le=200),
    seed: int = Query(1, ge=0, description='Sensing matrix seed'),
):
    if name not in _SIGNAL_PRESETS:
        raise HTTPException(404, f'Preset {name!r} not found')

    x_true = _SIGNAL_PRESETS[name]
    N = len(x_true)
    if M > N:
        raise HTTPException(400, f'M={M} must be <= N={N}')

    A_apply, A_adjoint, L, A_matrix = make_random_measurement_op(M, N, seed=seed)
    rng = np.random.default_rng(42 + seed)
    y_clean = A_apply(x_true)
    y = y_clean + noise * rng.standard_normal(M)

    # Naive least-squares baseline ("no optimizer"). Min-norm solution to
    # y = A x via Moore-Penrose pseudoinverse. Dense, not sparse.
    x_naive = naive_lasso(y, A_matrix)
    baseline_snr = snr(x_true, x_naive)
    baseline_mse = mse(x_true, x_naive)
    baseline_sparsity = float(np.mean(np.abs(x_naive) < 1e-6))

    iter_fn = ista_denoise_iter if algo == 'ista' else fista_denoise_iter

    async def event_gen() -> AsyncIterator[dict]:
        yield {
            'event': 'init',
            'data': json.dumps({
                'N': N, 'M': M,
                'x_true':   x_true.tolist(),
                'y':        y.tolist(),
                'L':        L,
                'baseline_x':        x_naive.tolist(),
                'baseline_snr':      baseline_snr,
                'baseline_mse':      baseline_mse,
                'baseline_sparsity': baseline_sparsity,
                'algo':     algo,
                'max_iter': max_iter,
            }),
        }
        for info in iter_fn(y, x_true, A_apply, A_adjoint, lam=lam, L=L,
                            max_iter=max_iter, snapshot_every=snapshot_every):
            payload = {k: v for k, v in info.items() if k != 'x'}
            if info['x'] is not None:
                payload['x'] = info['x'].tolist()
            yield {'event': 'iter', 'data': json.dumps(payload)}
            await asyncio.sleep(0)
        yield {'event': 'done', 'data': '{}'}

    return EventSourceResponse(event_gen(), headers=_SSE_HEADERS)
