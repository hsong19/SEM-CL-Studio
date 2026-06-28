from __future__ import annotations

import numpy as np


def mean_spectrum(cube: np.ndarray) -> np.ndarray:
    if cube.ndim != 3:
        raise ValueError("CL cube must have wavelength/y/x dimensions")
    return np.asarray(cube, dtype=np.float64).mean(axis=(1, 2))


def compute_cl_map(
    cube: np.ndarray,
    wavelength_nm: np.ndarray,
    *,
    mode: str = "total",
    point_nm: float | None = None,
    start_nm: float | None = None,
    end_nm: float | None = None,
    reduction: str = "sum",
) -> np.ndarray:
    if cube.ndim != 3:
        raise ValueError("CL cube must have wavelength/y/x dimensions")
    wavelengths = np.asarray(wavelength_nm, dtype=float)
    if wavelengths.ndim != 1 or wavelengths.size != cube.shape[0]:
        raise ValueError("Wavelength axis does not match the cube")

    normalized_mode = mode.lower().strip()
    if normalized_mode == "total":
        return np.asarray(cube, dtype=np.float32).sum(axis=0, dtype=np.float32)
    if normalized_mode == "point":
        if point_nm is None:
            raise ValueError("point_nm is required for point mapping")
        index = int(np.nanargmin(np.abs(wavelengths - point_nm)))
        return np.asarray(cube[index], dtype=np.float32)
    if normalized_mode != "band":
        raise ValueError(f"Unknown mapping mode: {mode}")

    if start_nm is None or end_nm is None:
        raise ValueError("start_nm and end_nm are required for band mapping")
    low, high = sorted((float(start_nm), float(end_nm)))
    indices = np.flatnonzero((wavelengths >= low) & (wavelengths <= high))
    if indices.size == 0:
        center = (low + high) / 2.0
        indices = np.array([int(np.nanargmin(np.abs(wavelengths - center)))])
    band = np.asarray(cube[indices], dtype=np.float32)
    if reduction == "mean":
        return band.mean(axis=0, dtype=np.float32)
    if reduction == "max":
        return band.max(axis=0)
    return band.sum(axis=0, dtype=np.float32)


def percentile_levels(data: np.ndarray, low: float = 1.0, high: float = 99.0) -> tuple[float, float]:
    finite = np.asarray(data)[np.isfinite(data)]
    if finite.size == 0:
        return 0.0, 1.0
    lo, hi = np.percentile(finite, [low, high])
    if hi <= lo:
        hi = lo + 1.0
    return float(lo), float(hi)

