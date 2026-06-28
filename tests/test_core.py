from pathlib import Path

import numpy as np

from semcl_studio.analysis.mapping import compute_cl_map, mean_spectrum
from semcl_studio.analysis.spectrum import extract_point_spectrum
from semcl_studio.io.filename_parser import parse_measurement_conditions


def test_filename_conditions() -> None:
    result = parse_measurement_conditions("NMA_200mmol_5kV57pA220mTorr_1.h5")
    assert result == {"voltage_kv": 5.0, "beam_current_pa": 57.0, "pressure_mtorr": 220.0}


def test_mapping_and_point_spectrum() -> None:
    cube = np.arange(4 * 3 * 2, dtype=np.uint16).reshape(4, 3, 2)
    wavelengths = np.array([500.0, 510.0, 520.0, 530.0])
    assert np.allclose(mean_spectrum(cube), cube.mean(axis=(1, 2)))
    assert np.array_equal(compute_cl_map(cube, wavelengths, mode="point", point_nm=519.0), cube[2])
    assert np.array_equal(
        compute_cl_map(cube, wavelengths, mode="band", start_nm=505.0, end_nm=525.0),
        cube[1:3].sum(axis=0),
    )
    assert np.allclose(extract_point_spectrum(cube, 0, 1, size=1), cube[:, 1, 0])

