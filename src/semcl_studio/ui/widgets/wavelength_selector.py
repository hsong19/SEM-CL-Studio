from __future__ import annotations

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import QSignalBlocker, Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)


class WavelengthSelector(QFrame):
    selection_changed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ImageCard")
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(
            ["Total intensity", "Single wavelength", "Wavelength band"]
        )
        self.point_spin = _wavelength_spin()
        self.start_spin = _wavelength_spin()
        self.end_spin = _wavelength_spin()
        self.reduction_combo = QComboBox()
        self.reduction_combo.addItems(["Sum", "Mean", "Maximum"])

        controls = QHBoxLayout()
        controls.setContentsMargins(0, 0, 0, 0)
        mode_form = QFormLayout()
        mode_form.setContentsMargins(0, 0, 0, 0)
        mode_form.addRow("Map", self.mode_combo)
        point_form = QFormLayout()
        point_form.setContentsMargins(0, 0, 0, 0)
        point_form.addRow("Wavelength", self.point_spin)
        band_form = QFormLayout()
        band_form.setContentsMargins(0, 0, 0, 0)
        band_form.addRow("Start", self.start_spin)
        band_form.addRow("End", self.end_spin)
        band_form.addRow("Method", self.reduction_combo)
        controls.addLayout(mode_form)
        controls.addSpacing(8)
        controls.addLayout(point_form)
        controls.addSpacing(8)
        controls.addLayout(band_form)
        controls.addStretch(1)

        self.plot = pg.PlotWidget()
        self.plot.setBackground("w")
        self.plot.setLabel("bottom", "Wavelength", units="nm")
        self.plot.setLabel("left", "Mean intensity")
        self.plot.showGrid(x=True, y=True, alpha=0.2)
        self.point_line = pg.InfiniteLine(
            angle=90, movable=True, pen=pg.mkPen("#0066cc", width=2)
        )
        self.band_region = pg.LinearRegionItem(
            values=(700.0, 800.0),
            brush=pg.mkBrush(0, 102, 204, 45),
            pen=pg.mkPen("#0066cc", width=1.5),
            movable=True,
        )
        self.plot.addItem(self.band_region)
        self.plot.addItem(self.point_line)

        title = QLabel("AVERAGE SPECTRUM · drag the line or window")
        title.setObjectName("SectionTitle")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)
        layout.addWidget(title)
        layout.addLayout(controls)
        layout.addWidget(self.plot, 1)

        self.mode_combo.currentTextChanged.connect(self._mode_changed)
        self.point_spin.valueChanged.connect(self._point_spin_changed)
        self.start_spin.valueChanged.connect(self._band_spin_changed)
        self.end_spin.valueChanged.connect(self._band_spin_changed)
        self.reduction_combo.currentTextChanged.connect(self._emit_changed)
        self.point_line.sigPositionChanged.connect(self._point_line_changed)
        self.band_region.sigRegionChanged.connect(self._band_region_changed)
        self.plot.scene().sigMouseClicked.connect(self._plot_clicked)
        self._mode_changed()

    def set_spectrum(self, wavelength_nm: np.ndarray, intensity: np.ndarray) -> None:
        wavelength = np.asarray(wavelength_nm, dtype=float)
        values = np.asarray(intensity, dtype=float)
        self.plot.clear()
        self.plot.plot(wavelength, values, pen=pg.mkPen("#0066cc", width=1.5))
        self.plot.addItem(self.band_region)
        self.plot.addItem(self.point_line)

        low, high = float(np.nanmin(wavelength)), float(np.nanmax(wavelength))
        peak = float(wavelength[int(np.nanargmax(values))])
        span = high - low
        default_start = max(low, peak - span * 0.05)
        default_end = min(high, peak + span * 0.05)
        for spin in (self.point_spin, self.start_spin, self.end_spin):
            with QSignalBlocker(spin):
                spin.setRange(low, high)
        with QSignalBlocker(self.point_spin):
            self.point_spin.setValue(peak)
        with QSignalBlocker(self.start_spin):
            self.start_spin.setValue(default_start)
        with QSignalBlocker(self.end_spin):
            self.end_spin.setValue(default_end)
        self.point_line.setBounds((low, high))
        self.band_region.setBounds((low, high))
        self.point_line.setValue(peak)
        self.band_region.setRegion((default_start, default_end))
        self.plot.autoRange()
        self._mode_changed()

    def mode(self) -> str:
        text = self.mode_combo.currentText()
        if text == "Single wavelength":
            return "point"
        if text == "Wavelength band":
            return "band"
        return "total"

    def selection(self) -> dict[str, float | str]:
        return {
            "mode": self.mode(),
            "point_nm": self.point_spin.value(),
            "start_nm": min(self.start_spin.value(), self.end_spin.value()),
            "end_nm": max(self.start_spin.value(), self.end_spin.value()),
            "reduction": {
                "Sum": "sum",
                "Mean": "mean",
                "Maximum": "max",
            }[self.reduction_combo.currentText()],
        }

    def _mode_changed(self, *_args) -> None:
        point = self.mode() == "point"
        band = self.mode() == "band"
        self.point_spin.setVisible(point)
        self.point_line.setVisible(point)
        self.start_spin.setVisible(band)
        self.end_spin.setVisible(band)
        self.reduction_combo.setVisible(band)
        self.band_region.setVisible(band)
        self._emit_changed()

    def _point_spin_changed(self, value: float) -> None:
        with QSignalBlocker(self.point_line):
            self.point_line.setValue(value)
        self._emit_changed()

    def _band_spin_changed(self, *_args) -> None:
        with QSignalBlocker(self.band_region):
            self.band_region.setRegion(
                (self.start_spin.value(), self.end_spin.value())
            )
        self._emit_changed()

    def _point_line_changed(self) -> None:
        with QSignalBlocker(self.point_spin):
            self.point_spin.setValue(float(self.point_line.value()))
        self._emit_changed()

    def _band_region_changed(self) -> None:
        start, end = self.band_region.getRegion()
        with QSignalBlocker(self.start_spin):
            self.start_spin.setValue(float(start))
        with QSignalBlocker(self.end_spin):
            self.end_spin.setValue(float(end))
        self._emit_changed()

    def _plot_clicked(self, event) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return
        if not self.plot.plotItem.sceneBoundingRect().contains(event.scenePos()):
            return
        point = self.plot.plotItem.vb.mapSceneToView(event.scenePos())
        value = float(point.x())
        if self.mode() == "point":
            self.point_spin.setValue(value)
        elif self.mode() == "band":
            start, end = self.band_region.getRegion()
            half_width = max((end - start) / 2.0, 0.5)
            self.band_region.setRegion((value - half_width, value + half_width))

    def _emit_changed(self, *_args) -> None:
        self.selection_changed.emit()


def _wavelength_spin() -> QDoubleSpinBox:
    spin = QDoubleSpinBox()
    spin.setDecimals(3)
    spin.setSingleStep(0.5)
    spin.setSuffix(" nm")
    return spin
