from __future__ import annotations

import numpy as np


def extract_point_spectrum(cube: np.ndarray, x: int, y: int, size: int = 1) -> np.ndarray:
    if cube.ndim != 3:
        raise ValueError("CL cube must have wavelength/y/x dimensions")
    _, height, width = cube.shape
    x = min(max(int(x), 0), width - 1)
    y = min(max(int(y), 0), height - 1)
    size = max(1, int(size))
    if size % 2 == 0:
        size += 1
    radius = size // 2
    x0, x1 = max(0, x - radius), min(width, x + radius + 1)
    y0, y1 = max(0, y - radius), min(height, y + radius + 1)
    return np.asarray(cube[:, y0:y1, x0:x1], dtype=np.float64).mean(axis=(1, 2))

