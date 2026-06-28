from __future__ import annotations

from pathlib import Path

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from semcl_studio.analysis.mapping import percentile_levels


class ImagePanel(QFrame):
    clicked = Signal(float, float)
    cursor_changed = Signal(float, float, float)
    hovered = Signal(float, float)
    hover_left = Signal()

    def __init__(
        self, title: str, *, show_colorbar: bool = True, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.setObjectName("ImageCard")
        self.setFrameShape(QFrame.Shape.NoFrame)
        self._data: np.ndarray | None = None
        self._pixel_um = (1.0, 1.0)
        self._image_rect = QRectF(0.0, 0.0, 1.0, 1.0)
        self._colormap_name = "viridis"
        self._scale_line: pg.PlotDataItem | None = None
        self._scale_text: pg.TextItem | None = None
        self._scale_visible = True
        self._scale_length_um: float | None = None
        self._scale_thickness = 5
        self._scale_position = "Bottom right"
        self._scale_bar_color = "#ffffff"
        self._scale_text_color = "#ffffff"
        self._scale_label_background = "#88000000"
        self._scale_label_border = "#ffffff"
        self._scale_border_width = 1.0
        self._scale_font_size = 10
        self._fit_range: tuple[list[float], list[float]] | None = None
        self._pending_fit = False
        self._at_fit = True

        self.title_label = QLabel(title)
        self.title_label.setObjectName("SectionTitle")
        self.fit_button = QPushButton("Fit")
        self.fit_button.setToolTip("Fit the entire image in the view")
        self.copy_button = QPushButton("Copy")
        self.export_button = QPushButton("Export")

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.addWidget(self.title_label)
        header.addStretch(1)
        header.addWidget(self.fit_button)
        header.addWidget(self.copy_button)
        header.addWidget(self.export_button)

        self.graphics = pg.GraphicsLayoutWidget()
        self.graphics.setBackground("w")
        self.graphics.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.plot = self.graphics.addPlot(row=0, col=0)
        self.plot.setAspectLocked(True)
        self.plot.showGrid(x=False, y=False)
        self.plot.hideAxis("bottom")
        self.plot.hideAxis("left")
        self.plot.invertY(True)
        self.plot.setMouseEnabled(x=True, y=True)
        self.image_item = pg.ImageItem(axisOrder="row-major")
        self.plot.addItem(self.image_item)
        self.overlay_item = pg.ImageItem(axisOrder="row-major")
        self.overlay_item.setZValue(5)
        self.overlay_item.hide()
        self.plot.addItem(self.overlay_item)
        crosshair_pen = pg.mkPen("#ffcc00", width=1.2, style=Qt.PenStyle.DashLine)
        self.crosshair_x = pg.InfiniteLine(angle=90, movable=False, pen=crosshair_pen)
        self.crosshair_y = pg.InfiniteLine(angle=0, movable=False, pen=crosshair_pen)
        for item in (self.crosshair_x, self.crosshair_y):
            item.setZValue(70)
            item.hide()
            self.plot.addItem(item)

        self.colorbar: pg.ColorBarItem | None = None
        if show_colorbar:
            self.colorbar = pg.ColorBarItem(
                values=(0.0, 1.0),
                colorMap=pg.colormap.get("viridis"),
                interactive=True,
                width=14,
            )
            self.colorbar.setImageItem(self.image_item)
            self.graphics.addItem(self.colorbar, row=0, col=1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)
        layout.addLayout(header)
        layout.addWidget(self.graphics, 1)

        self.fit_button.clicked.connect(self.fit_to_view)
        self.copy_button.clicked.connect(self.copy_view)
        self.export_button.clicked.connect(self.export_view)
        self.graphics.scene().sigMouseMoved.connect(self._mouse_moved)
        self.graphics.scene().sigMouseClicked.connect(self._mouse_clicked)
        self.plot.getViewBox().sigRangeChangedManually.connect(
            self._view_changed_manually
        )

    @property
    def pixel_um(self) -> tuple[float, float]:
        return self._pixel_um

    @property
    def image_rect(self) -> QRectF:
        return QRectF(self._image_rect)

    def set_image(
        self,
        image: np.ndarray,
        pixel_um: tuple[float, float],
        *,
        center_um: tuple[float, float] = (0.0, 0.0),
        colormap: str | None = None,
        auto_levels: bool = True,
        fit: bool = True,
    ) -> None:
        data = np.asarray(image)
        if data.ndim != 2:
            raise ValueError(f"ImagePanel requires 2D data, got {data.shape}")
        self._data = data
        self._pixel_um = pixel_um
        height, width = data.shape
        physical_width = width * pixel_um[0]
        physical_height = height * pixel_um[1]
        rect = QRectF(
            center_um[0] - physical_width / 2.0,
            center_um[1] - physical_height / 2.0,
            physical_width,
            physical_height,
        )
        self._image_rect = rect
        self.image_item.setImage(data, autoLevels=False)
        self.image_item.setRect(rect)
        self.set_colormap(colormap or self._colormap_name)
        if auto_levels:
            self.auto_levels()
        self._update_scale_bar()
        if fit:
            self._pending_fit = True
            if self.isVisible():
                QTimer.singleShot(0, self._deferred_fit)

    def set_colormap(self, name: str, *, inverted: bool = False) -> None:
        self._colormap_name = name
        if name == "gray":
            colors = (
                [QColor("white"), QColor("black")]
                if inverted
                else [QColor("black"), QColor("white")]
            )
            cmap = pg.ColorMap([0.0, 1.0], colors)
        else:
            try:
                cmap = pg.colormap.get(name)
            except Exception:
                cmap = pg.colormap.get("viridis")
        self.image_item.setLookupTable(cmap.getLookupTable(nPts=256))
        if self.colorbar is not None:
            self.colorbar.setColorMap(cmap)

    def auto_levels(self) -> None:
        if self._data is None:
            return
        levels = percentile_levels(self._data)
        self.image_item.setLevels(levels)
        if self.colorbar is not None:
            self.colorbar.setLevels(levels)

    def set_overlay(
        self,
        image: np.ndarray | None,
        pixel_um: tuple[float, float] | None = None,
        *,
        center_um: tuple[float, float] = (0.0, 0.0),
        opacity: float = 0.35,
    ) -> None:
        if image is None:
            self.overlay_item.hide()
            return
        data = np.asarray(image, dtype=np.float32)
        low, high = percentile_levels(data)
        normalized = np.clip((data - low) / max(high - low, 1e-12), 0.0, 1.0)
        self.overlay_item.setImage(normalized, autoLevels=False, levels=(0.0, 1.0))
        px = pixel_um or self._pixel_um
        height, width = data.shape
        physical_width = width * px[0]
        physical_height = height * px[1]
        self.overlay_item.setRect(
            QRectF(
                center_um[0] - physical_width / 2.0,
                center_um[1] - physical_height / 2.0,
                physical_width,
                physical_height,
            )
        )
        gray = pg.ColorMap([0.0, 1.0], [QColor("black"), QColor("white")])
        self.overlay_item.setLookupTable(gray.getLookupTable(nPts=256))
        self.overlay_item.setOpacity(float(np.clip(opacity, 0.0, 1.0)))
        self.overlay_item.show()

    def set_scale_bar(
        self,
        *,
        visible: bool = True,
        length_um: float | None = None,
        thickness: int = 5,
        position: str = "Bottom right",
        bar_color: str = "#ffffff",
        text_color: str = "#ffffff",
        label_background: str = "#88000000",
        label_border: str = "#ffffff",
        border_width: float = 1.0,
        font_size: int = 10,
    ) -> None:
        self._scale_visible = visible
        self._scale_length_um = length_um if length_um and length_um > 0 else None
        self._scale_thickness = max(1, int(thickness))
        self._scale_position = position
        self._scale_bar_color = bar_color
        self._scale_text_color = text_color
        self._scale_label_background = label_background
        self._scale_label_border = label_border
        self._scale_border_width = max(0.0, float(border_width))
        self._scale_font_size = max(6, int(font_size))
        self._update_scale_bar()

    def fit_to_view(self) -> None:
        if self._data is None:
            return
        view_box = self.plot.getViewBox()
        view_box.setLimits(
            xMin=None,
            xMax=None,
            yMin=None,
            yMax=None,
            maxXRange=None,
            maxYRange=None,
        )
        self.plot.setRange(self._image_rect, padding=0.0)
        x_range, y_range = view_box.viewRange()
        self._fit_range = (list(x_range), list(y_range))
        self._pending_fit = False
        self._at_fit = True
        view_box.setLimits(
            xMin=x_range[0],
            xMax=x_range[1],
            yMin=y_range[0],
            yMax=y_range[1],
            maxXRange=x_range[1] - x_range[0],
            maxYRange=y_range[1] - y_range[0],
        )

    def _deferred_fit(self) -> None:
        if self._data is not None and self.isVisible():
            self.fit_to_view()

    def _view_changed_manually(self, *_args) -> None:
        self._at_fit = False

    def link_view(self, other: "ImagePanel") -> None:
        self.plot.setXLink(other.plot)
        self.plot.setYLink(other.plot)

    def set_crosshair(
        self, x_um: float | None = None, y_um: float | None = None
    ) -> None:
        if x_um is None or y_um is None:
            self.crosshair_x.hide()
            self.crosshair_y.hide()
            return
        self.crosshair_x.setValue(x_um)
        self.crosshair_y.setValue(y_um)
        self.crosshair_x.show()
        self.crosshair_y.show()

    def copy_view(self) -> None:
        QApplication.clipboard().setPixmap(self.graphics.grab())

    def export_view(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Export image", "", "PNG image (*.png)"
        )
        if path:
            self.graphics.grab().save(str(Path(path)), "PNG")

    def _update_scale_bar(self) -> None:
        if self._scale_line is not None:
            self.plot.removeItem(self._scale_line)
            self._scale_line = None
        if self._scale_text is not None:
            self.plot.removeItem(self._scale_text)
            self._scale_text = None
        if not self._scale_visible or self._data is None:
            return

        width = self._image_rect.width()
        height = self._image_rect.height()
        size = min(
            self._scale_length_um or _nice_scale_length(width),
            width * 0.90,
        )
        margin_x = width * 0.05
        margin_y = height * 0.05
        right = self._scale_position.endswith("right")
        bottom = self._scale_position.startswith("Bottom")
        if right:
            x2 = self._image_rect.right() - margin_x
            x1 = x2 - size
        else:
            x1 = self._image_rect.left() + margin_x
            x2 = x1 + size
        y = (
            self._image_rect.bottom() - margin_y
            if bottom
            else self._image_rect.top() + margin_y
        )
        self._scale_line = pg.PlotDataItem(
            [x1, x2],
            [y, y],
            pen=pg.mkPen(self._scale_bar_color, width=self._scale_thickness),
        )
        self._scale_line.setZValue(50)
        self.plot.addItem(self._scale_line)
        label = f"{size:g} µm"
        self._scale_text = pg.TextItem(
            label,
            color=self._scale_text_color,
            anchor=(0.5, 1.15 if bottom else -0.15),
            border=(
                pg.mkPen(
                    self._scale_label_border,
                    width=self._scale_border_width,
                )
                if self._scale_border_width > 0
                else None
            ),
            fill=pg.mkBrush(QColor(self._scale_label_background)),
        )
        font = QFont()
        font.setPointSize(self._scale_font_size)
        self._scale_text.setFont(font)
        self._scale_text.setPos((x1 + x2) / 2.0, y)
        self._scale_text.setZValue(51)
        self.plot.addItem(self._scale_text)

    def _scene_position(self, scene_pos) -> tuple[float, float] | None:
        if not self.plot.sceneBoundingRect().contains(scene_pos):
            return None
        point = self.plot.getViewBox().mapSceneToView(scene_pos)
        return float(point.x()), float(point.y())

    def _data_index(self, x_um: float, y_um: float) -> tuple[int, int] | None:
        if self._data is None or not self._image_rect.contains(x_um, y_um):
            return None
        height, width = self._data.shape
        x = int((x_um - self._image_rect.left()) / self._image_rect.width() * width)
        y = int((y_um - self._image_rect.top()) / self._image_rect.height() * height)
        if 0 <= x < width and 0 <= y < height:
            return x, y
        return None

    def _mouse_moved(self, scene_pos) -> None:
        mapped = self._scene_position(scene_pos)
        if mapped is None or self._data is None:
            return
        index = self._data_index(*mapped)
        if index is not None:
            x, y = index
            self.hovered.emit(mapped[0], mapped[1])
            self.cursor_changed.emit(mapped[0], mapped[1], float(self._data[y, x]))
        else:
            self.hover_left.emit()

    def _mouse_clicked(self, event) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return
        mapped = self._scene_position(event.scenePos())
        if mapped is not None and self._data_index(*mapped) is not None:
            self.clicked.emit(*mapped)

    def leaveEvent(self, event) -> None:
        self.hover_left.emit()
        super().leaveEvent(event)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if self._pending_fit or self._at_fit:
            QTimer.singleShot(0, self._deferred_fit)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._pending_fit or self._at_fit:
            QTimer.singleShot(0, self._deferred_fit)


def _nice_scale_length(width_um: float) -> float:
    target = max(width_um * 0.2, 1e-6)
    exponent = float(np.floor(np.log10(target)))
    base = 10.0**exponent
    factor = min((1.0, 2.0, 5.0), key=lambda item: abs(item * base - target))
    return factor * base
