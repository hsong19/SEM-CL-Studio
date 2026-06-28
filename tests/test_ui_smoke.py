from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pytest


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest

from semcl_studio.ui.main_window import MainWindow


def test_ui_loads_file_and_builds_stacked_point_spectra() -> None:
    examples = sorted((Path(__file__).resolve().parents[1] / "data").glob("*.h5"))
    if not examples:
        pytest.skip("No supplied HDF5 examples")
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    window.show()
    window.load_file(examples[0])
    dataset = window._active_dataset
    assert dataset is not None

    spectrum = window.spectrum_tab
    spectrum.add_point_button.setChecked(True)
    width_um, height_um = dataset.cl_extent_um
    spectrum._map_clicked(width_um * 0.35, height_um * 0.40)
    spectrum._map_clicked(width_um * 0.65, height_um * 0.60)
    spectrum.display_mode_combo.setCurrentText("Stack")
    app.processEvents()

    assert len(spectrum.points) == 2
    assert len(spectrum.axes.lines) == 2
    assert spectrum.axes.get_ylabel() == "Intensity + offset"
    assert spectrum.axes.lines[0].get_color() == spectrum.points[0].color

    # The selected point can be dragged from either registered image.
    x_um, y_um = dataset.cl_pixel_center_um(20, 25)
    spectrum.map_target.setPos(x_um, y_um)
    QTest.qWait(35)
    assert (spectrum.points[-1].x, spectrum.points[-1].y) == (20, 25)
    assert np.allclose(
        [spectrum.se_target.pos().x(), spectrum.se_target.pos().y()],
        [x_um, y_um],
    )

    spectrum.show_point_labels_check.setChecked(False)
    assert not spectrum._text_items[spectrum.se_panel]
    spectrum.plot_title_edit.setText("Custom title")
    assert spectrum.axes.get_title() == "Custom title"

    for tab, panels in (
        (window.mapping_tab, (window.mapping_tab.se_panel, window.mapping_tab.cl_panel)),
        (window.spectrum_tab, (window.spectrum_tab.se_panel, window.spectrum_tab.map_panel)),
    ):
        window.tabs.setCurrentWidget(tab)
        QTest.qWait(80)
        for panel in panels:
            rect = panel.image_rect
            x_range, y_range = panel.plot.getViewBox().viewRange()
            assert x_range[0] <= rect.left() <= rect.right() <= x_range[1]
            assert y_range[0] <= rect.top() <= rect.bottom() <= y_range[1]
    window.close()
