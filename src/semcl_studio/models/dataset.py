from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from scipy.ndimage import gaussian_filter, zoom
from scipy.signal import fftconvolve


@dataclass(slots=True)
class SemClMetadata:
    voltage_kv: float | None = None
    beam_current_pa: float | None = None
    pressure_mtorr: float | None = None
    magnification: float | None = None
    exposure_seconds: float | None = None
    dwell_seconds: float | None = None
    spectrometer: str | None = None
    extras: dict[str, str | float | int] = field(default_factory=dict)

    def primary_rows(self) -> list[tuple[str, str]]:
        return [
            ("Voltage", _format(self.voltage_kv, " kV")),
            ("Beam current", _format(self.beam_current_pa, " pA")),
            ("Magnification", _format(self.magnification, "×", thousands=True)),
            ("Exposure", _format(self.exposure_seconds, " s")),
        ]


@dataclass(slots=True)
class SemClDataset:
    source_path: Path
    survey_se: np.ndarray
    concurrent_se: np.ndarray
    cl_cube: np.ndarray
    wavelength_nm: np.ndarray
    survey_pixel_um: tuple[float, float]
    concurrent_pixel_um: tuple[float, float]
    cl_pixel_um: tuple[float, float]
    metadata: SemClMetadata
    survey_offset_um: tuple[float, float] = (0.0, 0.0)
    concurrent_offset_um: tuple[float, float] = (0.0, 0.0)
    cl_offset_um: tuple[float, float] = (0.0, 0.0)
    _survey_registration: tuple[int, int] | None = field(
        default=None, init=False, repr=False
    )
    _registered_survey: np.ndarray | None = field(
        default=None, init=False, repr=False
    )

    @property
    def display_name(self) -> str:
        return self.source_path.name

    @property
    def cl_shape(self) -> tuple[int, int, int]:
        return tuple(int(value) for value in self.cl_cube.shape)

    @property
    def cl_extent_um(self) -> tuple[float, float]:
        _, height, width = self.cl_cube.shape
        return width * self.cl_pixel_um[0], height * self.cl_pixel_um[1]

    @property
    def cl_bounds_um(self) -> tuple[float, float, float, float]:
        _, height, width = self.cl_cube.shape
        return _bounds(self.cl_offset_um, self.cl_pixel_um, (height, width))

    @property
    def concurrent_bounds_um(self) -> tuple[float, float, float, float]:
        return _bounds(self.concurrent_offset_um, self.concurrent_pixel_um, self.concurrent_se.shape)

    def se_image(
        self, source: str
    ) -> tuple[np.ndarray, tuple[float, float], tuple[float, float]]:
        if source.lower().startswith("survey"):
            return self.survey_se, self.survey_pixel_um, self.survey_offset_um
        return self.concurrent_se, self.concurrent_pixel_um, self.concurrent_offset_um

    def survey_crop_to_concurrent(
        self,
    ) -> tuple[np.ndarray, tuple[float, float], tuple[float, float]]:
        """Return Survey SE content-registered to the Concurrent/CL field of view.

        HDF5 offsets provide the initial search position, but the Survey and
        Concurrent acquisitions can drift by tens of Survey pixels.  A local
        normalized cross-correlation against the Concurrent SE image corrects
        that drift once per loaded dataset.
        """
        target_left, target_top, target_right, target_bottom = self.concurrent_bounds_um
        survey_left, survey_top, _, _ = _bounds(
            self.survey_offset_um, self.survey_pixel_um, self.survey_se.shape
        )
        px, py = self.survey_pixel_um
        height, width = self.survey_se.shape
        crop_width = max(1, int(round((target_right - target_left) / px)))
        crop_height = max(1, int(round((target_bottom - target_top) / py)))

        if self._survey_registration is None:
            expected_x = int(round((target_left - survey_left) / px))
            expected_y = int(round((target_top - survey_top) / py))
            self._survey_registration = _register_crop_origin(
                self.survey_se,
                self.concurrent_se,
                expected=(expected_x, expected_y),
                crop_shape=(crop_height, crop_width),
            )
        if self._registered_survey is None:
            self._registered_survey = _affine_registered_crop(
                self.survey_se,
                self.concurrent_se,
                origin=self._survey_registration,
                crop_shape=(crop_height, crop_width),
            )
        crop = self._registered_survey
        target_width = target_right - target_left
        target_height = target_bottom - target_top
        effective_pixel = (target_width / crop.shape[1], target_height / crop.shape[0])
        center = ((target_left + target_right) / 2.0, (target_top + target_bottom) / 2.0)
        return crop, effective_pixel, center

    def physical_to_cl_pixel(self, x_um: float, y_um: float) -> tuple[int, int] | None:
        left, top, right, bottom = self.cl_bounds_um
        if not (left <= x_um < right and top <= y_um < bottom):
            return None
        x = int((x_um - left) / self.cl_pixel_um[0])
        y = int((y_um - top) / self.cl_pixel_um[1])
        _, height, width = self.cl_cube.shape
        if 0 <= x < width and 0 <= y < height:
            return x, y
        return None

    def cl_pixel_center_um(self, x: int, y: int) -> tuple[float, float]:
        left, top, _, _ = self.cl_bounds_um
        return (
            left + (x + 0.5) * self.cl_pixel_um[0],
            top + (y + 0.5) * self.cl_pixel_um[1],
        )


def _bounds(
    center_um: tuple[float, float],
    pixel_um: tuple[float, float],
    shape: tuple[int, ...],
) -> tuple[float, float, float, float]:
    height, width = int(shape[-2]), int(shape[-1])
    half_width = width * pixel_um[0] / 2.0
    half_height = height * pixel_um[1] / 2.0
    return (
        center_um[0] - half_width,
        center_um[1] - half_height,
        center_um[0] + half_width,
        center_um[1] + half_height,
    )


def _register_crop_origin(
    survey: np.ndarray,
    concurrent: np.ndarray,
    *,
    expected: tuple[int, int],
    crop_shape: tuple[int, int],
) -> tuple[int, int]:
    """Find the Survey crop that best matches Concurrent SE content."""
    survey_data = np.asarray(survey, dtype=np.float32)
    crop_height, crop_width = crop_shape
    survey_height, survey_width = survey_data.shape
    if crop_height >= survey_height or crop_width >= survey_width:
        return 0, 0

    expected_x = int(np.clip(expected[0], 0, survey_width - crop_width))
    expected_y = int(np.clip(expected[1], 0, survey_height - crop_height))
    search_radius = min(220, max(48, int(min(crop_shape) * 0.32)))
    search_left = max(0, expected_x - search_radius)
    search_top = max(0, expected_y - search_radius)
    search_right = min(survey_width, expected_x + crop_width + search_radius)
    search_bottom = min(survey_height, expected_y + crop_height + search_radius)
    search = survey_data[search_top:search_bottom, search_left:search_right]

    target = zoom(
        np.asarray(concurrent, dtype=np.float32),
        (
            crop_height / concurrent.shape[0],
            crop_width / concurrent.shape[1],
        ),
        order=1,
        prefilter=False,
    )
    sigma = max(3.0, min(crop_shape) / 90.0)
    search_feature = search - gaussian_filter(search, sigma=sigma)
    target_feature = target - gaussian_filter(target, sigma=sigma)
    target_feature -= float(np.mean(target_feature))
    target_energy = float(np.sum(target_feature * target_feature))
    if target_energy <= 1e-12:
        return expected_x, expected_y

    numerator = fftconvolve(
        search_feature,
        target_feature[::-1, ::-1],
        mode="valid",
    )
    local_energy = fftconvolve(
        search_feature * search_feature,
        np.ones(target_feature.shape, dtype=np.float32),
        mode="valid",
    )
    denominator = np.sqrt(np.maximum(local_energy * target_energy, 1e-12))
    correlation = numerator / denominator
    if correlation.size == 0 or not np.any(np.isfinite(correlation)):
        return expected_x, expected_y
    match_y, match_x = np.unravel_index(
        int(np.nanargmax(correlation)), correlation.shape
    )
    return search_left + int(match_x), search_top + int(match_y)


def _affine_registered_crop(
    survey: np.ndarray,
    concurrent: np.ndarray,
    *,
    origin: tuple[int, int],
    crop_shape: tuple[int, int],
) -> np.ndarray:
    """Warp Survey SE into Concurrent coordinates using local tile matches."""
    from scipy.ndimage import map_coordinates

    survey_data = np.asarray(survey, dtype=np.float32)
    crop_height, crop_width = crop_shape
    target = zoom(
        np.asarray(concurrent, dtype=np.float32),
        (
            crop_height / concurrent.shape[0],
            crop_width / concurrent.shape[1],
        ),
        order=1,
        prefilter=False,
    )
    tile_size = max(72, min(140, min(crop_shape) // 4))
    search_radius = max(36, min(60, tile_size // 2))
    matches: list[tuple[tuple[float, float], tuple[float, float], float]] = []

    for fraction_y in (0.2, 0.5, 0.8):
        for fraction_x in (0.2, 0.5, 0.8):
            center_x = int(fraction_x * crop_width)
            center_y = int(fraction_y * crop_height)
            tile_x = max(0, min(crop_width - tile_size, center_x - tile_size // 2))
            tile_y = max(0, min(crop_height - tile_size, center_y - tile_size // 2))
            template = target[
                tile_y : tile_y + tile_size,
                tile_x : tile_x + tile_size,
            ]
            predicted_x = origin[0] + tile_x
            predicted_y = origin[1] + tile_y
            search_left = max(0, predicted_x - search_radius)
            search_top = max(0, predicted_y - search_radius)
            search_right = min(
                survey_data.shape[1], predicted_x + tile_size + search_radius
            )
            search_bottom = min(
                survey_data.shape[0], predicted_y + tile_size + search_radius
            )
            search = survey_data[
                search_top:search_bottom,
                search_left:search_right,
            ]
            if search.shape[0] < tile_size or search.shape[1] < tile_size:
                continue
            match_x, match_y, score = _local_ncc_match(search, template)
            matches.append(
                (
                    (tile_x + tile_size / 2.0, tile_y + tile_size / 2.0),
                    (
                        search_left + match_x + tile_size / 2.0,
                        search_top + match_y + tile_size / 2.0,
                    ),
                    score,
                )
            )

    matches.sort(key=lambda item: item[2], reverse=True)
    if len(matches) < 3:
        x0, y0 = origin
        return np.ascontiguousarray(
            survey_data[y0 : y0 + crop_height, x0 : x0 + crop_width]
        )
    score_floor = max(0.025, matches[min(5, len(matches) - 1)][2])
    selected = [item for item in matches if item[2] >= score_floor][:7]
    if len(selected) < 3:
        selected = matches[: min(5, len(matches))]

    target_points = np.asarray(
        [[item[0][0], item[0][1], 1.0] for item in selected],
        dtype=np.float64,
    )
    source_x = np.asarray([item[1][0] for item in selected], dtype=np.float64)
    source_y = np.asarray([item[1][1] for item in selected], dtype=np.float64)
    transform_x = np.linalg.lstsq(target_points, source_x, rcond=None)[0]
    transform_y = np.linalg.lstsq(target_points, source_y, rcond=None)[0]
    for _ in range(2):
        residual = np.hypot(
            target_points @ transform_x - source_x,
            target_points @ transform_y - source_y,
        )
        keep = residual <= max(8.0, float(np.median(residual)) * 2.5)
        if int(np.count_nonzero(keep)) < 3:
            break
        transform_x = np.linalg.lstsq(
            target_points[keep], source_x[keep], rcond=None
        )[0]
        transform_y = np.linalg.lstsq(
            target_points[keep], source_y[keep], rcond=None
        )[0]

    linear = np.asarray(
        [transform_x[:2], transform_y[:2]], dtype=np.float64
    )
    determinant = float(np.linalg.det(linear))
    if (
        not np.all(np.isfinite(linear))
        or not 0.72 <= determinant <= 1.35
        or float(np.max(np.abs(linear))) > 1.25
    ):
        transform_x = np.asarray([1.0, 0.0, float(origin[0])])
        transform_y = np.asarray([0.0, 1.0, float(origin[1])])

    output_y, output_x = np.indices(crop_shape, dtype=np.float32)
    source_grid_x = (
        transform_x[0] * output_x
        + transform_x[1] * output_y
        + transform_x[2]
    )
    source_grid_y = (
        transform_y[0] * output_x
        + transform_y[1] * output_y
        + transform_y[2]
    )
    return np.ascontiguousarray(
        map_coordinates(
            survey_data,
            (source_grid_y, source_grid_x),
            order=1,
            mode="nearest",
            prefilter=False,
        )
    )


def _local_ncc_match(
    search: np.ndarray, template: np.ndarray
) -> tuple[int, int, float]:
    sigma = max(2.0, min(template.shape) / 30.0)
    search_feature = search - gaussian_filter(search, sigma=sigma)
    template_feature = template - gaussian_filter(template, sigma=sigma)
    template_feature -= float(np.mean(template_feature))
    template_energy = float(np.sum(template_feature * template_feature))
    numerator = fftconvolve(
        search_feature,
        template_feature[::-1, ::-1],
        mode="valid",
    )
    local_energy = fftconvolve(
        search_feature * search_feature,
        np.ones(template_feature.shape, dtype=np.float32),
        mode="valid",
    )
    correlation = numerator / np.sqrt(
        np.maximum(local_energy * template_energy, 1e-12)
    )
    match_y, match_x = np.unravel_index(
        int(np.nanargmax(correlation)), correlation.shape
    )
    return int(match_x), int(match_y), float(correlation[match_y, match_x])


def _format(value: float | None, suffix: str, *, thousands: bool = False) -> str:
    if value is None or not np.isfinite(value):
        return "—"
    if thousands:
        return f"{value:,.0f}{suffix}"
    return f"{value:g}{suffix}"
