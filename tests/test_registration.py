from pathlib import Path

import numpy as np
import pytest
from scipy.ndimage import gaussian_filter, zoom

from semcl_studio.io.hdf5_reader import load_semcl_dataset


def _example_dataset():
    examples = sorted((Path(__file__).resolve().parents[1] / "data").glob("*.h5"))
    if not examples:
        pytest.skip("No supplied HDF5 examples")
    return load_semcl_dataset(examples[0])


def test_survey_crop_matches_concurrent_field_of_view() -> None:
    dataset = _example_dataset()
    image, pixel_um, center_um = dataset.survey_crop_to_concurrent()
    left, top, right, bottom = dataset.concurrent_bounds_um

    assert np.allclose(
        center_um,
        ((left + right) / 2.0, (top + bottom) / 2.0),
    )
    assert np.allclose(
        (image.shape[1] * pixel_um[0], image.shape[0] * pixel_um[1]),
        (right - left, bottom - top),
    )
    assert np.allclose(dataset.cl_bounds_um, dataset.concurrent_bounds_um)
    assert dataset._survey_registration is not None

    concurrent = zoom(
        np.asarray(dataset.concurrent_se, dtype=np.float32),
        (
            image.shape[0] / dataset.concurrent_se.shape[0],
            image.shape[1] / dataset.concurrent_se.shape[1],
        ),
        order=1,
    )
    survey_feature = image - gaussian_filter(image, 6.0)
    concurrent_feature = concurrent - gaussian_filter(concurrent, 6.0)
    correlation = np.corrcoef(
        survey_feature.ravel(), concurrent_feature.ravel()
    )[0, 1]
    assert correlation > 0.4


def test_cl_physical_coordinate_round_trip() -> None:
    dataset = _example_dataset()
    _, height, width = dataset.cl_shape
    x, y = width // 3, height // 2
    physical = dataset.cl_pixel_center_um(x, y)
    assert dataset.physical_to_cl_pixel(*physical) == (x, y)
