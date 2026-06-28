from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QPushButton,
    QSpinBox,
)

from semcl_studio.ui.widgets.image_panel import ImagePanel


class ColorButton(QPushButton):
    color_changed = Signal(str)

    def __init__(self, color: str, parent=None) -> None:
        super().__init__(parent)
        self._color = QColor(color)
        self.clicked.connect(self._choose_color)
        self._refresh()

    @property
    def color(self) -> str:
        return self._color.name(QColor.NameFormat.HexArgb)

    def _choose_color(self) -> None:
        color = QColorDialog.getColor(
            self._color,
            self,
            "Choose color",
            QColorDialog.ColorDialogOption.ShowAlphaChannel,
        )
        if color.isValid():
            self._color = color
            self._refresh()
            self.color_changed.emit(self.color)

    def _refresh(self) -> None:
        foreground = "#111111" if self._color.lightnessF() > 0.55 else "#ffffff"
        self.setText(self._color.name(QColor.NameFormat.HexArgb))
        self.setStyleSheet(
            f"background:{self._color.name(QColor.NameFormat.HexArgb)};"
            f"color:{foreground};"
        )


class ScaleBarControls(QGroupBox):
    changed = Signal()

    def __init__(self, title: str = "Scale bar", parent=None) -> None:
        super().__init__(title, parent)
        self.show_check = QCheckBox("Show scale bar")
        self.show_check.setChecked(True)
        self.length_spin = QDoubleSpinBox()
        self.length_spin.setRange(0.0, 100000.0)
        self.length_spin.setDecimals(3)
        self.length_spin.setSingleStep(0.5)
        self.length_spin.setSuffix(" µm")
        self.length_spin.setSpecialValueText("Auto")
        self.thickness_spin = QSpinBox()
        self.thickness_spin.setRange(1, 20)
        self.thickness_spin.setValue(5)
        self.thickness_spin.setSuffix(" px")
        self.position_combo = QComboBox()
        self.position_combo.addItems(
            ["Bottom right", "Bottom left", "Top right", "Top left"]
        )
        self.bar_color_button = ColorButton("#ffffffff")
        self.text_color_button = ColorButton("#ffffffff")
        self.background_button = ColorButton("#88000000")
        self.border_color_button = ColorButton("#ffffffff")
        self.border_width_spin = QDoubleSpinBox()
        self.border_width_spin.setRange(0.0, 8.0)
        self.border_width_spin.setDecimals(1)
        self.border_width_spin.setValue(1.0)
        self.border_width_spin.setSuffix(" px")
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(6, 36)
        self.font_size_spin.setValue(10)
        self.font_size_spin.setSuffix(" pt")

        form = QFormLayout(self)
        form.addRow(self.show_check)
        form.addRow("Length", self.length_spin)
        form.addRow("Bar thickness", self.thickness_spin)
        form.addRow("Position", self.position_combo)
        form.addRow("Bar color", self.bar_color_button)
        form.addRow("Text color", self.text_color_button)
        form.addRow("Label background", self.background_button)
        form.addRow("Label border", self.border_color_button)
        form.addRow("Border width", self.border_width_spin)
        form.addRow("Font size", self.font_size_spin)

        self.show_check.toggled.connect(self._emit_changed)
        self.length_spin.valueChanged.connect(self._emit_changed)
        self.thickness_spin.valueChanged.connect(self._emit_changed)
        self.position_combo.currentTextChanged.connect(self._emit_changed)
        self.border_width_spin.valueChanged.connect(self._emit_changed)
        self.font_size_spin.valueChanged.connect(self._emit_changed)
        for button in (
            self.bar_color_button,
            self.text_color_button,
            self.background_button,
            self.border_color_button,
        ):
            button.color_changed.connect(self._emit_changed)

    def apply(self, panel: ImagePanel) -> None:
        panel.set_scale_bar(
            visible=self.show_check.isChecked(),
            length_um=self.length_spin.value() or None,
            thickness=self.thickness_spin.value(),
            position=self.position_combo.currentText(),
            bar_color=self.bar_color_button.color,
            text_color=self.text_color_button.color,
            label_background=self.background_button.color,
            label_border=self.border_color_button.color,
            border_width=self.border_width_spin.value(),
            font_size=self.font_size_spin.value(),
        )

    def _emit_changed(self, *_args) -> None:
        self.changed.emit()
