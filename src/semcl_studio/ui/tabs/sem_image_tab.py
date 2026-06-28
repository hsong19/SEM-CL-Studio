from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QFrame,
    QGroupBox,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Qt

from semcl_studio.models.dataset import SemClDataset
from semcl_studio.ui.widgets.image_panel import ImagePanel
from semcl_studio.ui.widgets.scale_bar_controls import ScaleBarControls


class SemImageTab(QWidget):
    status_message = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.dataset: SemClDataset | None = None
        self.image_panel = ImagePanel("SEM IMAGE", show_colorbar=True)
        self.source_combo = QComboBox()
        self.source_combo.addItems(["Concurrent SE", "Survey SE"])
        self.invert_check = QCheckBox("Invert grayscale")
        self.auto_button = QPushButton("Auto contrast")
        self.scale_controls = ScaleBarControls()

        inspector = QFrame()
        inspector.setObjectName("InspectorPanel")
        inspector.setMinimumWidth(240)
        inspector.setMaximumWidth(350)
        inspector_layout = QVBoxLayout(inspector)
        inspector_layout.setContentsMargins(16, 16, 16, 16)

        display_group = QGroupBox("Display")
        display_form = QFormLayout(display_group)
        display_form.addRow("Image source", self.source_combo)
        display_form.addRow(self.invert_check)
        display_form.addRow(self.auto_button)

        inspector_layout.addWidget(display_group)
        inspector_layout.addWidget(self.scale_controls)
        inspector_layout.addStretch(1)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.image_panel)
        splitter.addWidget(inspector)
        splitter.setSizes([1000, 280])
        splitter.setStretchFactor(0, 1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(splitter)

        self.source_combo.currentTextChanged.connect(self._refresh_image)
        self.invert_check.toggled.connect(self._refresh_colormap)
        self.auto_button.clicked.connect(self.image_panel.auto_levels)
        self.scale_controls.changed.connect(self._apply_scale_bar)
        self.image_panel.cursor_changed.connect(
            lambda x, y, value: self.status_message.emit(
                f"SEM  x={x:.3f} µm  y={y:.3f} µm  intensity={value:.0f}"
            )
        )

    def set_dataset(self, dataset: SemClDataset) -> None:
        self.dataset = dataset
        self._refresh_image()

    def _refresh_image(self) -> None:
        if self.dataset is None:
            return
        image, pixel_um, center_um = self.dataset.se_image(
            self.source_combo.currentText()
        )
        self.image_panel.set_image(
            image, pixel_um, center_um=center_um, colormap="gray"
        )
        self._refresh_colormap()
        self._apply_scale_bar()

    def _refresh_colormap(self) -> None:
        self.image_panel.set_colormap(
            "gray", inverted=self.invert_check.isChecked()
        )

    def _apply_scale_bar(self) -> None:
        self.scale_controls.apply(self.image_panel)
