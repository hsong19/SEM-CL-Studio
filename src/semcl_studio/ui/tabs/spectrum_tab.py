from __future__ import annotations

import csv
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

import numpy as np
import pyqtgraph as pg
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
from matplotlib.ticker import AutoLocator, MultipleLocator
from PySide6.QtCore import QSignalBlocker, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QIcon, QImage, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from semcl_studio.analysis.mapping import compute_cl_map, mean_spectrum
from semcl_studio.analysis.spectrum import extract_point_spectrum
from semcl_studio.models.dataset import SemClDataset
from semcl_studio.ui.widgets.image_panel import ImagePanel
from semcl_studio.ui.widgets.scale_bar_controls import ScaleBarControls
from semcl_studio.ui.widgets.wavelength_selector import WavelengthSelector


POINT_COLORS = [
    "#ff5a4f",
    "#10a7e8",
    "#f59e0b",
    "#7c5cff",
    "#00a878",
    "#d946ef",
    "#8b5e3c",
    "#4b5563",
]


@dataclass(slots=True)
class SpectrumPoint:
    point_id: int
    name: str
    x: int
    y: int
    color: str
    sample_size: int = 1
    visible: bool = True


class SpectrumTab(QWidget):
    status_message = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.dataset: SemClDataset | None = None
        self._points_by_file: dict[str, list[SpectrumPoint]] = {}
        self._selected_by_file: dict[str, int | None] = {}
        self._text_items: dict[ImagePanel, list[pg.TextItem]] = {}
        self._line_to_point: dict[object, int] = {}
        self._map_initialized = False
        self._target_syncing = False

        self.se_panel = ImagePanel(
            "SURVEY SE · CLICK TO SELECT", show_colorbar=False
        )
        self.map_panel = ImagePanel(
            "CL MAPPING · CLICK TO SELECT", show_colorbar=True
        )
        self.map_panel.link_view(self.se_panel)
        self.selector = WavelengthSelector()
        self.selector.setMinimumHeight(260)

        self.se_scatter = pg.ScatterPlotItem(pxMode=True, hoverable=True)
        self.map_scatter = pg.ScatterPlotItem(pxMode=True, hoverable=True)
        for panel, scatter in (
            (self.se_panel, self.se_scatter),
            (self.map_panel, self.map_scatter),
        ):
            scatter.setZValue(20)
            panel.plot.addItem(scatter)
            self._text_items[panel] = []

        self.se_target = pg.TargetItem(
            size=13,
            symbol="o",
            pen=pg.mkPen("#ffffff", width=2),
            brush=pg.mkBrush("#ff5a4f"),
            hoverPen=pg.mkPen("#ffcc00", width=3),
            movable=True,
        )
        self.map_target = pg.TargetItem(
            size=13,
            symbol="o",
            pen=pg.mkPen("#ffffff", width=2),
            brush=pg.mkBrush("#ff5a4f"),
            hoverPen=pg.mkPen("#ffcc00", width=3),
            movable=True,
        )
        for panel, target in (
            (self.se_panel, self.se_target),
            (self.map_panel, self.map_target),
        ):
            target.setZValue(30)
            target.hide()
            panel.plot.addItem(target)

        image_splitter = QSplitter(Qt.Orientation.Vertical)
        image_splitter.addWidget(self.se_panel)
        image_splitter.addWidget(self.map_panel)
        image_splitter.setSizes([450, 450])
        image_splitter.setStretchFactor(0, 1)
        image_splitter.setStretchFactor(1, 1)

        self.figure = Figure(figsize=(7.2, 5.4), dpi=100, facecolor="white")
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.axes = self.figure.subplots()
        self.toolbar = NavigationToolbar2QT(self.canvas, self)
        self.copy_figure_button = QPushButton("Copy")
        self.copy_data_button = QPushButton("Copy Data")
        self.export_data_button = QPushButton("Export CSV")
        self.export_figure_button = QPushButton("Export")

        plot_header = QHBoxLayout()
        plot_header.setContentsMargins(0, 0, 0, 0)
        plot_header.addWidget(self.toolbar)
        plot_header.addStretch(1)
        plot_header.addWidget(self.copy_figure_button)
        plot_header.addWidget(self.copy_data_button)
        plot_header.addWidget(self.export_data_button)
        plot_header.addWidget(self.export_figure_button)

        plot_frame = QFrame()
        plot_layout = QVBoxLayout(plot_frame)
        plot_layout.setContentsMargins(10, 10, 10, 10)
        spectrum_title = QLabel("POINT SPECTRA")
        spectrum_title.setObjectName("SectionTitle")
        plot_layout.addWidget(spectrum_title)
        plot_layout.addLayout(plot_header)
        plot_layout.addWidget(self.canvas, 1)

        inspector = self._build_inspector()
        inspector_scroll = QScrollArea()
        inspector_scroll.setWidgetResizable(True)
        inspector_scroll.setWidget(inspector)
        inspector_scroll.setMinimumWidth(280)

        right_splitter = QSplitter(Qt.Orientation.Vertical)
        right_splitter.addWidget(inspector_scroll)
        right_splitter.addWidget(self.selector)
        right_splitter.setSizes([590, 310])
        right_splitter.setMinimumWidth(390)
        right_splitter.setMaximumWidth(500)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(image_splitter)
        splitter.addWidget(plot_frame)
        splitter.addWidget(right_splitter)
        splitter.setSizes([460, 640, 420])
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(splitter)

        self._map_timer = QTimer(self)
        self._map_timer.setSingleShot(True)
        self._map_timer.setInterval(16)
        self._map_timer.timeout.connect(self._update_map)
        self._point_move_timer = QTimer(self)
        self._point_move_timer.setSingleShot(True)
        self._point_move_timer.setInterval(24)
        self._point_move_timer.timeout.connect(self._finish_point_move)

        self.se_panel.clicked.connect(self._image_clicked)
        self.map_panel.clicked.connect(self._image_clicked)
        self.se_panel.cursor_changed.connect(
            lambda x, y, value: self.status_message.emit(
                f"Spectrum SE  x={x:.3f} µm  y={y:.3f} µm  intensity={value:.3g}"
            )
        )
        self.map_panel.cursor_changed.connect(
            lambda x, y, value: self.status_message.emit(
                f"Spectrum map  x={x:.3f} µm  y={y:.3f} µm  intensity={value:.3g}"
            )
        )
        self.se_scatter.sigClicked.connect(self._scatter_clicked)
        self.map_scatter.sigClicked.connect(self._scatter_clicked)
        self.se_target.sigPositionChanged.connect(
            lambda *_: self._target_moved(self.se_target)
        )
        self.map_target.sigPositionChanged.connect(
            lambda *_: self._target_moved(self.map_target)
        )
        self.se_target.sigPositionChangeFinished.connect(
            self._finish_point_move
        )
        self.map_target.sigPositionChangeFinished.connect(
            self._finish_point_move
        )
        self.se_panel.hovered.connect(self._sync_crosshair)
        self.map_panel.hovered.connect(self._sync_crosshair)
        self.se_panel.hover_left.connect(self._hide_crosshair)
        self.map_panel.hover_left.connect(self._hide_crosshair)
        self.point_list.currentItemChanged.connect(self._point_selection_changed)
        self.add_point_button.toggled.connect(self._add_point_toggled)
        self.color_button.clicked.connect(self._change_point_color)
        self.rename_button.clicked.connect(self._rename_point)
        self.delete_button.clicked.connect(self._delete_point)
        self.sample_size_combo.currentTextChanged.connect(
            self._sample_size_changed
        )
        self.selector.selection_changed.connect(self._schedule_map_update)
        self.map_colormap_combo.currentTextChanged.connect(
            self._schedule_map_update
        )
        self.scale_controls.changed.connect(self._apply_scale_bars)
        self.display_mode_combo.currentTextChanged.connect(self._update_plot)
        self.auto_offset_check.toggled.connect(self._stack_controls_changed)
        self.offset_spin.valueChanged.connect(self._update_plot)
        self.baseline_zero_check.toggled.connect(self._update_plot)
        self.separator_check.toggled.connect(self._update_plot)
        self.show_legend_check.toggled.connect(self._update_plot)
        self.grid_check.toggled.connect(self._update_plot)
        self.line_width_spin.valueChanged.connect(self._update_plot)
        self.show_point_labels_check.toggled.connect(self._update_markers)
        self.auto_x_check.toggled.connect(self._axis_controls_changed)
        self.auto_y_check.toggled.connect(self._axis_controls_changed)
        for widget in (
            self.x_min_spin,
            self.x_max_spin,
            self.y_min_spin,
            self.y_max_spin,
            self.x_tick_spin,
            self.y_tick_spin,
            self.font_size_spin,
        ):
            widget.valueChanged.connect(self._update_plot)
        for edit in (self.plot_title_edit, self.x_label_edit, self.y_label_edit):
            edit.textChanged.connect(self._update_plot)
        self.copy_figure_button.clicked.connect(self.copy_figure)
        self.copy_data_button.clicked.connect(self.copy_data)
        self.export_data_button.clicked.connect(self.choose_export_data)
        self.export_figure_button.clicked.connect(self.export_figure)
        self.canvas.mpl_connect("pick_event", self._line_picked)
        self._stack_controls_changed()
        self._axis_controls_changed()
        self._update_plot()

    @property
    def points(self) -> list[SpectrumPoint]:
        if self.dataset is None:
            return []
        return self._points_by_file.setdefault(str(self.dataset.source_path), [])

    @property
    def selected_id(self) -> int | None:
        if self.dataset is None:
            return None
        return self._selected_by_file.get(str(self.dataset.source_path))

    @selected_id.setter
    def selected_id(self, value: int | None) -> None:
        if self.dataset is not None:
            self._selected_by_file[str(self.dataset.source_path)] = value

    def set_dataset(self, dataset: SemClDataset) -> None:
        self.dataset = dataset
        self._map_initialized = False
        self._points_by_file.setdefault(str(dataset.source_path), [])
        self._selected_by_file.setdefault(str(dataset.source_path), None)

        survey, pixel, center = dataset.survey_crop_to_concurrent()
        self.se_panel.set_image(
            survey, pixel, center_um=center, colormap="gray"
        )
        self.selector.set_spectrum(
            dataset.wavelength_nm, mean_spectrum(dataset.cl_cube)
        )
        with QSignalBlocker(self.x_min_spin):
            self.x_min_spin.setValue(float(np.nanmin(dataset.wavelength_nm)))
        with QSignalBlocker(self.x_max_spin):
            self.x_max_spin.setValue(float(np.nanmax(dataset.wavelength_nm)))
        self._update_map()
        self._apply_scale_bars()
        self._refresh_point_list()
        self._update_markers()
        self._update_plot()

    def _build_inspector(self) -> QFrame:
        inspector = QFrame()
        inspector.setObjectName("InspectorPanel")
        layout = QVBoxLayout(inspector)
        layout.setContentsMargins(14, 14, 14, 14)
        title = QLabel("INSPECTOR")
        title.setObjectName("SectionTitle")
        layout.addWidget(title)

        map_display_group = QGroupBox("Map display")
        map_display_form = QFormLayout(map_display_group)
        self.map_colormap_combo = QComboBox()
        self.map_colormap_combo.addItems(
            ["viridis", "plasma", "inferno", "magma", "cividis", "turbo", "gray"]
        )
        map_display_form.addRow("Colormap", self.map_colormap_combo)

        point_group = QGroupBox("Points / Traces")
        point_layout = QVBoxLayout(point_group)
        self.add_point_button = QPushButton("Click image to add")
        self.add_point_button.setCheckable(True)
        self.add_point_button.setChecked(True)
        self.point_list = QListWidget()
        self.point_list.setMinimumHeight(130)
        point_actions = QHBoxLayout()
        self.color_button = QPushButton("Color")
        self.rename_button = QPushButton("Rename")
        self.delete_button = QPushButton("Delete")
        point_actions.addWidget(self.color_button)
        point_actions.addWidget(self.rename_button)
        point_actions.addWidget(self.delete_button)
        self.sample_size_combo = QComboBox()
        self.sample_size_combo.addItems(["1 × 1", "3 × 3", "5 × 5"])
        self.show_point_labels_check = QCheckBox("Show point names on images")
        self.show_point_labels_check.setChecked(True)
        point_layout.addWidget(self.add_point_button)
        point_layout.addWidget(self.point_list)
        point_layout.addLayout(point_actions)
        sample_form = QFormLayout()
        sample_form.addRow("Sampling", self.sample_size_combo)
        point_layout.addLayout(sample_form)
        point_layout.addWidget(self.show_point_labels_check)

        stack_group = QGroupBox("Overlay / Stack")
        stack_form = QFormLayout(stack_group)
        self.display_mode_combo = QComboBox()
        self.display_mode_combo.addItems(["Overlay", "Stack"])
        self.auto_offset_check = QCheckBox("Auto offset")
        self.auto_offset_check.setChecked(True)
        self.offset_spin = QDoubleSpinBox()
        self.offset_spin.setRange(0.0, 1e12)
        self.offset_spin.setDecimals(2)
        self.offset_spin.setValue(1000.0)
        self.baseline_zero_check = QCheckBox("Align baseline to zero")
        self.separator_check = QCheckBox("Show separators")
        stack_form.addRow("Mode", self.display_mode_combo)
        stack_form.addRow(self.auto_offset_check)
        stack_form.addRow("Offset", self.offset_spin)
        stack_form.addRow(self.baseline_zero_check)
        stack_form.addRow(self.separator_check)

        style_group = QGroupBox("Figure style")
        style_form = QFormLayout(style_group)
        self.line_width_spin = QDoubleSpinBox()
        self.line_width_spin.setRange(0.5, 6.0)
        self.line_width_spin.setValue(1.8)
        self.show_legend_check = QCheckBox("Show legend")
        self.show_legend_check.setChecked(True)
        self.grid_check = QCheckBox("Show grid")
        self.grid_check.setChecked(True)
        style_form.addRow("Line width", self.line_width_spin)
        style_form.addRow(self.show_legend_check)
        style_form.addRow(self.grid_check)

        axes_group = QGroupBox("Axes / labels")
        axes_form = QFormLayout(axes_group)
        self.plot_title_edit = QLineEdit()
        self.plot_title_edit.setPlaceholderText("Optional title")
        self.x_label_edit = QLineEdit("Wavelength (nm)")
        self.y_label_edit = QLineEdit("Intensity")
        self.auto_x_check = QCheckBox("Auto X range")
        self.auto_x_check.setChecked(True)
        self.auto_y_check = QCheckBox("Auto Y range")
        self.auto_y_check.setChecked(True)
        self.x_min_spin = _axis_spin()
        self.x_max_spin = _axis_spin()
        self.y_min_spin = _axis_spin()
        self.y_max_spin = _axis_spin()
        self.x_tick_spin = _tick_spin()
        self.y_tick_spin = _tick_spin()
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(6, 30)
        self.font_size_spin.setValue(10)
        self.font_size_spin.setSuffix(" pt")
        axes_form.addRow("Title", self.plot_title_edit)
        axes_form.addRow("X label", self.x_label_edit)
        axes_form.addRow("Y label", self.y_label_edit)
        axes_form.addRow(self.auto_x_check)
        axes_form.addRow("X minimum", self.x_min_spin)
        axes_form.addRow("X maximum", self.x_max_spin)
        axes_form.addRow("X major tick", self.x_tick_spin)
        axes_form.addRow(self.auto_y_check)
        axes_form.addRow("Y minimum", self.y_min_spin)
        axes_form.addRow("Y maximum", self.y_max_spin)
        axes_form.addRow("Y major tick", self.y_tick_spin)
        axes_form.addRow("Font size", self.font_size_spin)

        self.scale_controls = ScaleBarControls("Scale bars · both images")
        layout.addWidget(map_display_group)
        layout.addWidget(point_group)
        layout.addWidget(stack_group)
        layout.addWidget(style_group)
        layout.addWidget(axes_group)
        layout.addWidget(self.scale_controls)
        layout.addStretch(1)
        return inspector

    def _current_map(self) -> np.ndarray | None:
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
        data = self._current_map()
        if data is None or self.dataset is None:
            return
        self.map_panel.set_image(
            data,
            self.dataset.cl_pixel_um,
            center_um=self.dataset.cl_offset_um,
            colormap=self.map_colormap_combo.currentText(),
            fit=not self._map_initialized,
        )
        self._map_initialized = True
        self._apply_scale_bars()
        self._update_markers()

    def _schedule_map_update(self, *_args) -> None:
        if not self._map_timer.isActive():
            self._map_timer.start()

    def _sync_crosshair(self, x_um: float, y_um: float) -> None:
        self.se_panel.set_crosshair(x_um, y_um)
        self.map_panel.set_crosshair(x_um, y_um)

    def _hide_crosshair(self) -> None:
        self.se_panel.set_crosshair()
        self.map_panel.set_crosshair()

    def _image_clicked(self, x_um: float, y_um: float) -> None:
        if self.dataset is None:
            return
        pixel = self.dataset.physical_to_cl_pixel(x_um, y_um)
        if pixel is None:
            return
        x, y = pixel
        nearest = self._nearest_point(x, y)
        if nearest is not None:
            self._select_point(nearest.point_id)
            return
        if not self.add_point_button.isChecked():
            return
        next_id = max((point.point_id for point in self.points), default=0) + 1
        point = SpectrumPoint(
            point_id=next_id,
            name=f"P{next_id}",
            x=x,
            y=y,
            color=POINT_COLORS[(next_id - 1) % len(POINT_COLORS)],
            sample_size=_sample_size(self.sample_size_combo.currentText()),
        )
        self.points.append(point)
        self.selected_id = point.point_id
        self._refresh_point_list()
        self._update_markers()
        self._update_plot()

    def _map_clicked(self, x_um: float, y_um: float) -> None:
        """Compatibility entry point using CL-local physical coordinates."""
        if self.dataset is None:
            return
        left, top, _, _ = self.dataset.cl_bounds_um
        self._image_clicked(left + x_um, top + y_um)

    def _nearest_point(self, x: int, y: int) -> SpectrumPoint | None:
        for point in self.points:
            if abs(point.x - x) <= 1 and abs(point.y - y) <= 1:
                return point
        return None

    def _scatter_clicked(self, _scatter, spots, _event) -> None:
        if spots:
            self._select_point(int(spots[0].data()))

    def _select_point(self, point_id: int | None) -> None:
        self.selected_id = point_id
        with QSignalBlocker(self.point_list):
            for index in range(self.point_list.count()):
                item = self.point_list.item(index)
                if item.data(Qt.ItemDataRole.UserRole) == point_id:
                    self.point_list.setCurrentItem(item)
                    break
        point = self._selected_point()
        if point is not None:
            with QSignalBlocker(self.sample_size_combo):
                self.sample_size_combo.setCurrentText(
                    f"{point.sample_size} × {point.sample_size}"
                )
        self._update_markers()
        self._update_plot()

    def _refresh_point_list(self) -> None:
        with QSignalBlocker(self.point_list):
            self.point_list.clear()
            for point in self.points:
                item = QListWidgetItem(
                    f"{point.name}   ({point.x}, {point.y})"
                )
                item.setData(Qt.ItemDataRole.UserRole, point.point_id)
                item.setIcon(_color_icon(point.color))
                self.point_list.addItem(item)
                if point.point_id == self.selected_id:
                    self.point_list.setCurrentItem(item)
        enabled = bool(self.points)
        self.color_button.setEnabled(enabled)
        self.rename_button.setEnabled(enabled)
        self.delete_button.setEnabled(enabled)

    def _update_markers(self) -> None:
        if self.dataset is None:
            self.se_scatter.setData([])
            self.map_scatter.setData([])
            return

        spots: list[dict] = []
        positions: list[tuple[SpectrumPoint, float, float]] = []
        for point in self.points:
            x_um, y_um = self.dataset.cl_pixel_center_um(point.x, point.y)
            selected = point.point_id == self.selected_id
            spots.append(
                {
                    "pos": (x_um, y_um),
                    "data": point.point_id,
                    "symbol": "o",
                    "size": 12 if selected else 9,
                    "brush": pg.mkBrush(point.color),
                    "pen": pg.mkPen(
                        "#ffffff" if selected else "#1d1d1f",
                        width=2 if selected else 1,
                    ),
                }
            )
            positions.append((point, x_um, y_um))

        self.se_scatter.setData(spots)
        self.map_scatter.setData(spots)
        for panel in (self.se_panel, self.map_panel):
            for item in self._text_items[panel]:
                panel.plot.removeItem(item)
            self._text_items[panel].clear()
            if self.show_point_labels_check.isChecked():
                for point, x_um, y_um in positions:
                    label = pg.TextItem(
                        point.name,
                        color=point.color,
                        anchor=(0.0, 1.0),
                    )
                    label.setPos(x_um, y_um)
                    label.setZValue(21)
                    panel.plot.addItem(label)
                    self._text_items[panel].append(label)

        selected = self._selected_point()
        self._target_syncing = True
        try:
            if selected is None:
                self.se_target.hide()
                self.map_target.hide()
            else:
                x_um, y_um = self.dataset.cl_pixel_center_um(
                    selected.x, selected.y
                )
                for target in (self.se_target, self.map_target):
                    target.setPen(pg.mkPen("#ffffff", width=2))
                    target.setBrush(pg.mkBrush(selected.color))
                    target.setPos(x_um, y_um)
                    target.show()
        finally:
            self._target_syncing = False

    def _target_moved(self, target: pg.TargetItem) -> None:
        if self._target_syncing or self.dataset is None:
            return
        point = self._selected_point()
        if point is None:
            return
        position = target.pos()
        pixel = self.dataset.physical_to_cl_pixel(
            float(position.x()), float(position.y())
        )
        if pixel is None:
            self._update_markers()
            return
        point.x, point.y = pixel
        self._update_markers()
        if not self._point_move_timer.isActive():
            self._point_move_timer.start()

    def _finish_point_move(self, *_args) -> None:
        self._point_move_timer.stop()
        self._refresh_point_list()
        self._update_plot()

    def _point_selection_changed(
        self, current: QListWidgetItem | None, _previous: QListWidgetItem | None
    ) -> None:
        self._select_point(
            current.data(Qt.ItemDataRole.UserRole) if current else None
        )

    def _add_point_toggled(self, checked: bool) -> None:
        self.add_point_button.setText(
            "Click image to add" if checked else "Enable point adding"
        )

    def _selected_point(self) -> SpectrumPoint | None:
        return next(
            (
                point
                for point in self.points
                if point.point_id == self.selected_id
            ),
            None,
        )

    def _change_point_color(self) -> None:
        point = self._selected_point()
        if point is None:
            return
        color = QColorDialog.getColor(QColor(point.color), self, "Point color")
        if color.isValid():
            point.color = color.name(QColor.NameFormat.HexRgb)
            self._refresh_point_list()
            self._update_markers()
            self._update_plot()

    def _rename_point(self) -> None:
        point = self._selected_point()
        if point is None:
            return
        text, accepted = QInputDialog.getText(
            self, "Rename point", "Point name", text=point.name
        )
        if accepted and text.strip():
            point.name = text.strip()
            self._refresh_point_list()
            self._update_markers()
            self._update_plot()

    def _delete_point(self) -> None:
        point = self._selected_point()
        if point is None:
            return
        self.points.remove(point)
        self.selected_id = self.points[-1].point_id if self.points else None
        self._refresh_point_list()
        self._update_markers()
        self._update_plot()

    def _sample_size_changed(self, text: str) -> None:
        point = self._selected_point()
        if point is not None:
            point.sample_size = _sample_size(text)
            self._update_plot()

    def _stack_controls_changed(self, *_args) -> None:
        self.offset_spin.setEnabled(not self.auto_offset_check.isChecked())
        self._update_plot()

    def _apply_scale_bars(self) -> None:
        self.scale_controls.apply(self.se_panel)
        self.scale_controls.apply(self.map_panel)

    def _spectra(self) -> list[tuple[SpectrumPoint, np.ndarray]]:
        if self.dataset is None:
            return []
        return [
            (
                point,
                extract_point_spectrum(
                    self.dataset.cl_cube,
                    point.x,
                    point.y,
                    point.sample_size,
                ),
            )
            for point in self.points
            if point.visible
        ]

    def _update_plot(self, *_args) -> None:
        self.axes.clear()
        self._line_to_point.clear()
        spectra = self._spectra()
        if self.dataset is None or not spectra:
            self.axes.text(
                0.5,
                0.5,
                "Select points on the SE image or CL map",
                ha="center",
                va="center",
                transform=self.axes.transAxes,
                color="#6e6e73",
            )
            self._apply_plot_settings(stack=False)
            self.figure.tight_layout()
            self.canvas.draw_idle()
            return

        stack = self.display_mode_combo.currentText() == "Stack"
        offset = self.offset_spin.value()
        if stack and self.auto_offset_check.isChecked():
            spans = []
            for _, values in spectra:
                p1, p99 = np.nanpercentile(values, [1, 99])
                spans.append(float(max(p99 - p1, 1.0)))
            offset = max(spans) * 1.15

        for index, (point, raw_values) in enumerate(spectra):
            values = np.asarray(raw_values, dtype=float)
            if stack and self.baseline_zero_check.isChecked():
                values = values - float(np.nanmin(values))
            display = values + (index * offset if stack else 0.0)
            linewidth = self.line_width_spin.value() + (
                0.8 if point.point_id == self.selected_id else 0.0
            )
            (line,) = self.axes.plot(
                self.dataset.wavelength_nm,
                display,
                color=point.color,
                lw=linewidth,
                alpha=1.0 if point.point_id == self.selected_id else 0.88,
                label=point.name,
                picker=5,
            )
            self._line_to_point[line] = point.point_id
            if stack and self.separator_check.isChecked():
                self.axes.axhline(
                    index * offset, color="#d2d2d7", lw=0.7, zorder=0
                )

        self._apply_plot_settings(stack=stack)
        self.axes.grid(self.grid_check.isChecked(), alpha=0.22)
        if self.show_legend_check.isChecked():
            self.axes.legend(
                frameon=True,
                framealpha=0.9,
                fontsize=self.font_size_spin.value(),
            )
        self.figure.tight_layout()
        self.canvas.draw_idle()

    def _axis_controls_changed(self, *_args) -> None:
        for widget in (self.x_min_spin, self.x_max_spin):
            widget.setEnabled(not self.auto_x_check.isChecked())
        for widget in (self.y_min_spin, self.y_max_spin):
            widget.setEnabled(not self.auto_y_check.isChecked())
        self._update_plot()

    def _apply_plot_settings(self, *, stack: bool) -> None:
        font_size = self.font_size_spin.value()
        self.axes.set_title(self.plot_title_edit.text(), fontsize=font_size + 2)
        self.axes.set_xlabel(self.x_label_edit.text(), fontsize=font_size)
        y_label = self.y_label_edit.text()
        if stack and y_label.strip() == "Intensity":
            y_label = "Intensity + offset"
        self.axes.set_ylabel(y_label, fontsize=font_size)
        self.axes.tick_params(axis="both", labelsize=font_size)

        if (
            not self.auto_x_check.isChecked()
            and self.x_min_spin.value() < self.x_max_spin.value()
        ):
            self.axes.set_xlim(
                self.x_min_spin.value(), self.x_max_spin.value()
            )
        if (
            not self.auto_y_check.isChecked()
            and self.y_min_spin.value() < self.y_max_spin.value()
        ):
            self.axes.set_ylim(
                self.y_min_spin.value(), self.y_max_spin.value()
            )

        self.axes.xaxis.set_major_locator(
            MultipleLocator(self.x_tick_spin.value())
            if self.x_tick_spin.value() > 0
            else AutoLocator()
        )
        self.axes.yaxis.set_major_locator(
            MultipleLocator(self.y_tick_spin.value())
            if self.y_tick_spin.value() > 0
            else AutoLocator()
        )

    def _line_picked(self, event) -> None:
        point_id = self._line_to_point.get(event.artist)
        if point_id is not None:
            self._select_point(point_id)

    def copy_figure(self) -> None:
        buffer = BytesIO()
        self.figure.savefig(
            buffer, format="png", dpi=300, bbox_inches="tight", pad_inches=0.25
        )
        image = QImage.fromData(buffer.getvalue(), "PNG")
        if not image.isNull():
            QApplication.clipboard().setImage(image)
            self.status_message.emit("Spectrum figure copied to clipboard")

    def copy_data(self) -> None:
        if self.dataset is None:
            return
        spectra = self._spectra()
        if not spectra:
            return
        rows = [["Wavelength (nm)", *[point.name for point, _ in spectra]]]
        for index, wavelength in enumerate(self.dataset.wavelength_nm):
            rows.append(
                [
                    f"{wavelength:.6g}",
                    *[f"{values[index]:.8g}" for _, values in spectra],
                ]
            )
        QApplication.clipboard().setText("\n".join("\t".join(row) for row in rows))
        self.status_message.emit("Spectrum data copied for Excel")

    def export_figure(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export spectrum figure",
            "spectrum.png",
            "PNG (*.png);;PDF (*.pdf);;SVG (*.svg)",
        )
        if path:
            self.figure.savefig(
                path, dpi=300, bbox_inches="tight", pad_inches=0.25
            )
            self.status_message.emit(f"Exported {Path(path).name}")

    def choose_export_data(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export spectrum data",
            "point-spectra.csv",
            "CSV (*.csv)",
        )
        if path:
            self.export_data(path)
            self.status_message.emit(f"Exported {Path(path).name}")

    def export_data(self, path: str | Path) -> None:
        if self.dataset is None:
            return
        spectra = self._spectra()
        with Path(path).open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.writer(handle)
            writer.writerow(
                ["Wavelength (nm)", *[point.name for point, _ in spectra]]
            )
            for index, wavelength in enumerate(self.dataset.wavelength_nm):
                writer.writerow(
                    [wavelength, *[values[index] for _, values in spectra]]
                )


def _sample_size(text: str) -> int:
    try:
        return int(text.split("×", 1)[0].strip())
    except ValueError:
        return 1


def _axis_spin() -> QDoubleSpinBox:
    spin = QDoubleSpinBox()
    spin.setRange(-1e15, 1e15)
    spin.setDecimals(4)
    spin.setSingleStep(1.0)
    return spin


def _tick_spin() -> QDoubleSpinBox:
    spin = QDoubleSpinBox()
    spin.setRange(0.0, 1e15)
    spin.setDecimals(4)
    spin.setSingleStep(1.0)
    spin.setSpecialValueText("Auto")
    return spin


def _color_icon(color: str) -> QIcon:
    pixmap = QPixmap(14, 14)
    pixmap.fill(QColor(color))
    return QIcon(pixmap)
