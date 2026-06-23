"""Golden reference model for the MTU systolic array.

Provides:
  * ``matmul_int``      -- bit-exact integer reference for Y = X @ W.
  * ``weight_load_seq`` -- the per-column weight feed order for the load shift chain.
  * ``skew_inputs`` / ``deskew_outputs`` -- diagonal staggering that mirrors the
    hardware dataflow so RTL results can be compared cycle-by-cycle.

The systolic array computes  Y[m][n] = sum_k X[m][k] * W[k][n]  with
  * X : (M x K) activations, fed one row per array-row (contraction index k),
  * W : (K x N) weights, one stationary weight per PE,
  * Y : (M x N) outputs, one accumulator per array-column.
"""

from __future__ import annotations

import numpy as np


def matmul_int(x: np.ndarray, w: np.ndarray) -> np.ndarray:
    """Integer reference matmul. Inputs are integer arrays; output is int64."""
    return x.astype(np.int64) @ w.astype(np.int64)


def weight_load_seq(w: np.ndarray) -> list[list[int]]:
    """Per-cycle weight feed for the load shift chain.

    Column ``n`` is fed W[K-1][n], W[K-2][n], ... , W[0][n] over K cycles so that
    after K shifts PE[k][n] holds W[k][n]. Returns a list of length K; element
    ``t`` is the row vector (length N) fed into the top of every column at cycle t.
    """
    k_dim = w.shape[0]
    return [[int(w[k_dim - 1 - t][n]) for n in range(w.shape[1])] for t in range(k_dim)]


def skew_inputs(x: np.ndarray, rows: int) -> list[list[int]]:
    """Diagonally skew activations for feeding the left edge.

    X[m][k] must enter row ``k`` at cycle ``m + k``. Returns a list of per-cycle
    frames; frame ``t`` is a length-``rows`` vector giving the activation fed to
    each array row at cycle ``t`` (0 where no data is scheduled).
    """
    m_dim, k_dim = x.shape
    assert k_dim == rows, f"X has K={k_dim} but array ROWS={rows}"
    n_cycles = m_dim + rows  # last input at cycle (M-1)+(K-1), +1 for exclusivity
    frames = [[0] * rows for _ in range(n_cycles)]
    for m in range(m_dim):
        for k in range(k_dim):
            frames[m + k][k] = int(x[m][k])
    return frames


def deskew_outputs(samples: list[list[int]], m_dim: int, rows: int, cols: int,
                   first_out_cycle: int) -> np.ndarray:
    """Recover Y from bottom-edge samples captured every cycle.

    Y[m][n] emerges at the bottom of column ``n`` at cycle
    ``first_out_cycle + m + n``. ``samples[t][n]`` is the value observed on
    column ``n`` at cycle ``t`` (indexing into the captured trace).
    """
    y = np.zeros((m_dim, cols), dtype=np.int64)
    for m in range(m_dim):
        for n in range(cols):
            t = first_out_cycle + m + n
            y[m][n] = samples[t][n]
    return y
