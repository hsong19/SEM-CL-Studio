from __future__ import annotations

from pathlib import Path
from typing import Any

import h5py
import numpy as np

from semcl_studio.io.filename_parser import parse_measurement_conditions
from semcl_studio.models.dataset import SemClDataset, SemClMetadata


class Hdf5ReadError(RuntimeError):
    pass


ImageAcquisition = tuple[
    np.ndarray,
    tuple[float, float],
    tuple[float, float],
    h5py.Group,
]
SpectrumAcquisition = tuple[
    np.ndarray,
    np.ndarray,
    tuple[float, float],
    tuple[float, float],
    h5py.Group,
]


def load_semcl_dataset(path: str | Path) -> SemClDataset:
    source_path = Path(path).expanduser().resolve()
    if not source_path.exists():
        raise Hdf5ReadError(f"File does not exist: {source_path}")

    survey: ImageAcquisition | None = None
    concurrent: ImageAcquisition | None = None
    spectrum: SpectrumAcquisition | None = None

    try:
        with h5py.File(source_path, "r") as handle:
            acquisitions = [
                handle[key] for key in sorted(handle.keys()) if key.startswith("Acquisition")
            ]
            for acquisition in acquisitions:
                if "ImageData/Image" not in acquisition:
                    continue
                title = _read_text(acquisition.get("PhysicalData/Title")).lower()
                image_dataset = acquisition["ImageData/Image"]
                shape = image_dataset.shape
                if "spectrum" in title or (len(shape) >= 3 and shape[0] > 1):
                    cube = _read_cube(image_dataset)
                    wavelengths = _read_wavelength_nm(acquisition, cube.shape[0])
                    spectrum = (
                        cube,
                        wavelengths,
                        _pixel_size_um(acquisition),
                        _offset_um(acquisition),
                        acquisition,
                    )
                elif "survey" in title:
                    survey = (
                        _read_image(image_dataset),
                        _pixel_size_um(acquisition),
                        _offset_um(acquisition),
                        acquisition,
                    )
                elif "concurrent" in title:
                    concurrent = (
                        _read_image(image_dataset),
                        _pixel_size_um(acquisition),
                        _offset_um(acquisition),
                        acquisition,
                    )

            if survey is None or concurrent is None or spectrum is None:
                survey, concurrent, spectrum = _fallback_acquisitions(
                    acquisitions, survey, concurrent, spectrum
                )

            if survey is None:
                raise Hdf5ReadError("Survey SE image was not found")
            if concurrent is None:
                raise Hdf5ReadError("Concurrent SE image was not found")
            if spectrum is None:
                raise Hdf5ReadError("CL spectrum cube was not found")

            cube, wavelengths, cl_pixel, cl_offset, spectrum_acquisition = spectrum
            if cube.shape[0] != wavelengths.size:
                raise Hdf5ReadError(
                    f"Spectrum axis mismatch: cube={cube.shape[0]}, wavelength={wavelengths.size}"
                )

            metadata = _read_metadata(source_path, concurrent[3], spectrum_acquisition)
            return SemClDataset(
                source_path=source_path,
                survey_se=survey[0],
                concurrent_se=concurrent[0],
                cl_cube=cube,
                wavelength_nm=wavelengths,
                survey_pixel_um=survey[1],
                concurrent_pixel_um=concurrent[1],
                cl_pixel_um=cl_pixel,
                metadata=metadata,
                survey_offset_um=survey[2],
                concurrent_offset_um=concurrent[2],
                cl_offset_um=cl_offset,
            )
    except OSError as exc:
        raise Hdf5ReadError(f"Could not open HDF5 file: {exc}") from exc


def _fallback_acquisitions(acquisitions, survey, concurrent, spectrum):
    images: list[ImageAcquisition] = []
    for acquisition in acquisitions:
        if "ImageData/Image" not in acquisition:
            continue
        dataset = acquisition["ImageData/Image"]
        if dataset.shape and dataset.shape[0] > 1:
            if spectrum is None:
                cube = _read_cube(dataset)
                spectrum = (
                    cube,
                    _read_wavelength_nm(acquisition, cube.shape[0]),
                    _pixel_size_um(acquisition),
                    _offset_um(acquisition),
                    acquisition,
                )
        else:
            images.append(
                (
                    _read_image(dataset),
                    _pixel_size_um(acquisition),
                    _offset_um(acquisition),
                    acquisition,
                )
            )
    if survey is None and images:
        survey = images[0]
    if concurrent is None and len(images) > 1:
        concurrent = images[1]
    return survey, concurrent, spectrum


def _read_image(dataset: h5py.Dataset) -> np.ndarray:
    image = np.asarray(dataset[()])
    image = np.squeeze(image)
    if image.ndim != 2:
        raise Hdf5ReadError(f"Expected a 2D SE image after squeeze, got {image.shape}")
    return np.ascontiguousarray(image)


def _read_cube(dataset: h5py.Dataset) -> np.ndarray:
    data = np.asarray(dataset[()])
    if data.ndim == 5:
        data = data[:, 0, 0, :, :]
    else:
        data = np.squeeze(data)
    if data.ndim != 3:
        raise Hdf5ReadError(f"Expected a wavelength/y/x cube, got {data.shape}")
    return np.ascontiguousarray(data)


def _read_wavelength_nm(acquisition: h5py.Group, channel_count: int) -> np.ndarray:
    path = "ImageData/DimensionScaleC"
    if path not in acquisition:
        raise Hdf5ReadError("Spectrum wavelength dimension is missing")
    values = np.asarray(acquisition[path][()], dtype=np.float64).reshape(-1)
    if values.size != channel_count:
        raise Hdf5ReadError("Wavelength dimension length does not match the spectrum cube")
    finite = values[np.isfinite(values)]
    if finite.size and float(np.nanmax(np.abs(finite))) < 1e-3:
        values = values * 1e9
    return values


def _pixel_size_um(acquisition: h5py.Group) -> tuple[float, float]:
    x = _read_number(acquisition.get("ImageData/DimensionScaleX"))
    y = _read_number(acquisition.get("ImageData/DimensionScaleY"))
    x_um = float(x * 1e6) if x is not None else 1.0
    y_um = float(y * 1e6) if y is not None else 1.0
    return x_um, y_um


def _offset_um(acquisition: h5py.Group) -> tuple[float, float]:
    x = _read_number(acquisition.get("ImageData/XOffset"))
    y = _read_number(acquisition.get("ImageData/YOffset"))
    return (
        float(x * 1e6) if x is not None else 0.0,
        float(y * 1e6) if y is not None else 0.0,
    )


def _read_metadata(
    source_path: Path, concurrent: h5py.Group, spectrum: h5py.Group
) -> SemClMetadata:
    parsed = parse_measurement_conditions(source_path)
    concurrent_physical = concurrent.get("PhysicalData")
    spectrum_physical = spectrum.get("PhysicalData")
    magnification = (
        _read_number(concurrent_physical.get("Magnification"))
        if concurrent_physical
        else None
    )
    dwell = (
        _read_number(concurrent_physical.get("IntegrationTime"))
        if concurrent_physical
        else None
    )
    exposure = (
        _read_number(spectrum_physical.get("IntegrationTime"))
        if spectrum_physical
        else None
    )
    spectrometer = (
        _read_text(spectrum_physical.get("HardwareName"))
        if spectrum_physical
        else ""
    )
    return SemClMetadata(
        voltage_kv=parsed["voltage_kv"],
        beam_current_pa=parsed["beam_current_pa"],
        pressure_mtorr=parsed["pressure_mtorr"],
        magnification=magnification,
        exposure_seconds=exposure,
        dwell_seconds=dwell,
        spectrometer=spectrometer or None,
    )


def _read_text(dataset: h5py.Dataset | None) -> str:
    if dataset is None:
        return ""
    value: Any = dataset[()]
    if isinstance(value, np.ndarray):
        if value.size == 0:
            return ""
        value = value.reshape(-1)[0]
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _read_number(dataset: h5py.Dataset | None) -> float | None:
    if dataset is None:
        return None
    try:
        value = np.asarray(dataset[()], dtype=np.float64).reshape(-1)
    except (TypeError, ValueError):
        return None
    if value.size == 0 or not np.isfinite(value[0]):
        return None
    return float(value[0])
