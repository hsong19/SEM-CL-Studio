from pathlib import Path

import pytest

from semcl_studio.io.hdf5_reader import load_semcl_dataset


def test_reads_supplied_hdf5_example() -> None:
    examples = sorted((Path(__file__).resolve().parents[1] / "data").glob("*.h5"))
    if not examples:
        pytest.skip("No supplied HDF5 examples")
    dataset = load_semcl_dataset(examples[0])
    assert dataset.survey_se.ndim == 2
    assert dataset.concurrent_se.ndim == 2
    assert dataset.cl_cube.ndim == 3
    assert dataset.cl_cube.shape[0] == dataset.wavelength_nm.size
    assert dataset.metadata.voltage_kv == 5.0
