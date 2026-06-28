from __future__ import annotations

import numpy as np
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QPushButton,
    QScrollArea,
    QSlider,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from semcl_studio.analysis.mapping import compute_cl_map, mean_spectrum
from semcl_studio.models.dataset import SemClDataset
from semcl_studio.ui.widgets.image_panel import ImagePanel
from semcl_studio.ui.widgets.scale_bar_controls import ScaleBarControls
from semcl_studio.ui.widgets.wavelength_selector import WavelengthSelector


class MappingTab(QWidget):
    status_message = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.dataset: SemClDataset | None = None
        self._map_initialized = False
        self._survey_view: tuple[
            np.ndarray, tuple[float, float], tuple[float, float]
        ] | None = None

        self.se_panel = ImagePanel("SURVEY SE · CL FIELD OF VIEW", show_colorbar=False)
        self.cl_panel = ImagePanel("CL MAPPING", show_colorbar=True)
        self.cl_panel.link_view(self.se_panel)
        image_splitter = QSplitter(Qt.Orientation.Vertical)
        image_splitter.addWidget(self.se_panel)
        image_splitter.addWidget(self.cl_panel)
        image_splitter.setSizes([450, 450])
        image_splitter.setStretchFactor(0, 1)
        image_splitter.setStretchFactor(1, 1)

        self.colormap_combo = QComboBox()
        self.colormap_combo.addItems(
            ["viridis", "plasma", "inferno", "magma", "cividis", "turbo", "gray"]
        )
        self.overlay_check = QCheckBox("Show Survey SE overlay")
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.setValue(35)
        self.auto_contrast_button = QPushButton("Auto map contrast")
        self.export_data_button = QPushButton("Export map CSV")
        self.scale_controls = ScaleBarControls("Scale bars · both images")

        controls = QFrame()
        controls.setObjectName("InspectorPanel")
        controls_layout = QVBoxLayout(controls)
        controls_layout.setContentsMargins(14, 14, 14, 14)

        display_group = QGroupBox("Display")
        display_form = QFormLayout(display_group)
        display_form.addRow("Colormap", self.colormap_combo)
        display_form.addRow(self.auto_contrast_button)
        display_form.addRow(self.export_data_button)
        display_form.addRow(self.overlay_check)
        display_form.addRow("Overlay opacity", self.opacity_slider)
        controls_layout.addWidget(display_group)
        controls_layout.addWidget(self.scale_controls)
        controls_layout.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(controls)
        scroll.setMinimumWidth(270)

        self.selector = WavelengthSelector()
        self.selector.setMinimumHeight(270)
        right_splitter = QSplitter(Qt.Orientation.Vertical)
        right_splitter.addWidget(scroll)
        right_splitter.addWidget(self.selector)
        right_splitter.setSizes([500, 380])

        outer = QSplitter(Qt.Orientation.Horizontal)
        outer.addWidget(image_splitter)
        outer.addWidget(right_splitter)
        outer.setSizes([1020, 360])
        outer.setStretchFactor(0, 1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(outer)

        self._update_timer = QTimer(self)
        self._update_timer.setSingleShot(True)
        self._update_timer.setInterval(16)
        self._update_timer.timeout.connect(self._update_map)

        self.selector.selection_changed.connect(self._schedule_update)
        self.colormap_combo.currentTextChanged.connect(self._schedule_update)
        self.overlay_check.toggled.connect(self._update_overlay)
        self.opacity_slider.valueChanged.connect(self._update_overlay)
        self.auto_contrast_button.clicked.connect(self.cl_panel.auto_levels)
        self.export_data_button.clicked.connect(self._export_map_data)
        self.scale_controls.changed.connect(self._apply_scale_bars)
        self.se_panel.hovered.connect(self._sync_crosshair)
        self.cl_panel.hovered.connect(self._sync_crosshair)
        self.se_panel.hover_left.connect(self._hide_crosshair)
        self.cl_panel.hover_left.connect(self._hide_crosshair)
        self.cl_panel.cursor_changed.connect(
            lambda x, y, value: self.status_message.emit(
                f"CL map  x={x:.3f} µm  y={y:.3f} µm  intensity={value:.3g}"
            )
        )

    def set_dataset(self, dataset: SemClDataset) -> None:
        self.dataset = dataset
        self._map_initialized = False
        self._survey_view = dataset.survey_crop_to_concurrent()
        survey, pixel, center = self._survey_view
        self.se_panel.set_image(
            survey, pixel, center_um=center, colormap="gray"
        )
        self.selector.set_spectrum(
            dataset.wavelength_nm, mean_spectrum(dataset.cl_cube)
        )
        self._apply_scale_bars()
        self._update_map()

    def current_map(self) -> np.ndarray | None:
        if self.dataset is None:
            return None
        selection = self.selector.selection()
        return compute_cl_map(
            self.dataset.cl_cube,
            self.dataset.wavelength_nm,
            mode=str(selection["mode"]),
            point_nm=float(selection["point_nm"]),
            start_nm=float(selection["start_nm"]),
            end_nm=float(selection["end_nm"]),
            reduction=str(selection["reduction"]),
        )

    def _update_map(self) -> None:
        data = self.current_map()
        if data is None or self.dataset is None:
            return
        self.cl_panel.set_image(
            data,
            self.dataset.cl_pixel_um,
            center_um=self.dataset.cl_offset_um,
            colormap=self.colormap_combo.currentText(),
            fit=not self._map_initialized,
        )
        self._map_initialized = True
        self._update_overlay()
        self._apply_scale_bars()

    def _schedule_update(self, *_args) -> None:
        # Throttle to display cadence instead of restarting the timer on every
        # drag event.  Fast line/region movement therefore keeps updating.
        if not self._update_timer.isActive():
            self._update_timer.start()

    def _sync_crosshair(self, x_um: float, y_um: float) -> None:
        self.se_panel.set_crosshair(x_um, y_um)
        self.cl_panel.set_crosshair(x_um, y_um)

    def _hide_crosshair(self) -> None:
        self.se_panel.set_crosshair()
        self.cl_panel.set_crosshair()

    def _update_overlay(self, *_args) -> None:
        if (
            self.dataset is None
            or self._survey_view is None
            or not self.overlay_check.isChecked()
        ):
            self.cl_panel.set_overlay(None)
            return
        image, pixel, center = self._survey_view
        self.cl_panel.set_overlay(
            image,
            pixel,
            center_um=center,
            opacity=self.opacity_slider.value() / 100.0,
        )

    def _apply_scale_bars(self) -> None:
        self.scale_controls.apply(self.se_panel)
        self.scale_controls.apply(self.cl_panel)

    def _export_map_data(self) -> None:
        data = self.current_map()
        if data is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export CL map data", "cl-map.csv", "CSV (*.csv)"
        )
        if path:
            np.savetxt(path, data, delimiter=",")
            self.status_message.emit(f"Exported CL map data: {path}")
