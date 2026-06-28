from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from semcl_studio.models.dataset import SemClDataset


class FilePanel(QFrame):
    file_selected = Signal(Path)
    files_added = Signal(list)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("FilePanel")
        self.setMinimumWidth(230)
        self.setMaximumWidth(330)
        self.title = QLabel("FILES")
        self.title.setObjectName("SectionTitle")
        self.open_button = QPushButton("Open")
        self.open_button.setObjectName("PrimaryButton")
        self.remove_button = QPushButton("Remove")
        self.list_widget = QListWidget()
        self.empty_label = QLabel("Open HDF5 files\nor drop them here.")
        self.empty_label.setObjectName("MutedLabel")
        self.empty_label.setWordWrap(True)
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet("background: transparent;")

        buttons = QHBoxLayout()
        buttons.setContentsMargins(0, 0, 0, 0)
        buttons.addWidget(self.open_button)
        buttons.addWidget(self.remove_button)

        self.metadata_group = QGroupBox("Selected file metadata")
        metadata_form = QFormLayout(self.metadata_group)
        self.metadata_labels: dict[str, QLabel] = {}
        for key in [
            "Voltage",
            "Beam current",
            "Magnification",
            "Exposure",
            "Pressure",
            "SE dwell",
            "Spectrometer",
            "CL pixel",
            "CL shape",
        ]:
            label = QLabel("—")
            label.setWordWrap(True)
            label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            self.metadata_labels[key] = label
            metadata_form.addRow(key, label)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 16, 12, 12)
        layout.setSpacing(10)
        layout.addWidget(self.title)
        layout.addLayout(buttons)
        layout.addWidget(self.empty_label, 1)
        layout.addWidget(self.list_widget, 1)
        layout.addWidget(self.metadata_group, 0)

        self.open_button.clicked.connect(self.choose_files)
        self.remove_button.clicked.connect(self.remove_selected)
        self.list_widget.currentItemChanged.connect(self._selection_changed)
        self._update_empty_state()

    def choose_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Open SEM-CL HDF5 files",
            "",
            "HDF5 files (*.h5 *.hdf5);;All files (*)",
        )
        if paths:
            self.add_paths([Path(path) for path in paths])
            self.files_added.emit(paths)

    def add_paths(self, paths: list[Path]) -> None:
        existing = {
            self.list_widget.item(index).data(Qt.ItemDataRole.UserRole)
            for index in range(self.list_widget.count())
        }
        first_added: QListWidgetItem | None = None
        for path in paths:
            resolved = str(path.expanduser().resolve())
            if resolved in existing:
                continue
            item = QListWidgetItem(path.name)
            item.setToolTip(resolved)
            item.setData(Qt.ItemDataRole.UserRole, resolved)
            self.list_widget.addItem(item)
            existing.add(resolved)
            first_added = first_added or item
        self._update_empty_state()
        if self.list_widget.currentItem() is None and first_added is not None:
            self.list_widget.setCurrentItem(first_added)

    def set_dataset(self, dataset: SemClDataset) -> None:
        values = dict(dataset.metadata.primary_rows())
        for key in ("Voltage", "Beam current", "Magnification", "Exposure"):
            self.metadata_labels[key].setText(values[key])
        pressure = dataset.metadata.pressure_mtorr
        dwell = dataset.metadata.dwell_seconds
        self.metadata_labels["Pressure"].setText(
            f"{pressure:g} mTorr" if pressure is not None else "—"
        )
        self.metadata_labels["SE dwell"].setText(
            f"{dwell:g} s" if dwell is not None else "—"
        )
        self.metadata_labels["Spectrometer"].setText(
            dataset.metadata.spectrometer or "—"
        )
        self.metadata_labels["CL pixel"].setText(
            f"{dataset.cl_pixel_um[0] * 1000:.2f} × "
            f"{dataset.cl_pixel_um[1] * 1000:.2f} nm"
        )
        channels, height, width = dataset.cl_shape
        self.metadata_labels["CL shape"].setText(
            f"{width} × {height} × {channels}"
        )

    def remove_selected(self) -> None:
        row = self.list_widget.currentRow()
        if row >= 0:
            self.list_widget.takeItem(row)
        self._update_empty_state()

    def _selection_changed(
        self, current: QListWidgetItem | None, _previous: QListWidgetItem | None
    ) -> None:
        if current is not None:
            self.file_selected.emit(
                Path(current.data(Qt.ItemDataRole.UserRole))
            )

    def _update_empty_state(self) -> None:
        empty = self.list_widget.count() == 0
        self.empty_label.setVisible(empty)
        self.list_widget.setVisible(not empty)
        self.remove_button.setEnabled(not empty)
        self.metadata_group.setVisible(not empty)
