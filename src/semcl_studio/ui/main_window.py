from __future__ import annotations

from collections import OrderedDict
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QDragEnterEvent, QDropEvent, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from semcl_studio.io.hdf5_reader import Hdf5ReadError, load_semcl_dataset
from semcl_studio.models.dataset import SemClDataset
from semcl_studio.ui.file_panel import FilePanel
from semcl_studio.ui.tabs.mapping_tab import MappingTab
from semcl_studio.ui.tabs.sem_image_tab import SemImageTab
from semcl_studio.ui.tabs.spectrum_tab import SpectrumTab
from semcl_studio.ui.widgets.empty_state import EmptyState


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("SEM-CL Studio")
        self.resize(1580, 920)
        self.setMinimumSize(1180, 720)
        self.setAcceptDrops(True)
        self._cache: OrderedDict[str, SemClDataset] = OrderedDict()
        self._active_dataset: SemClDataset | None = None

        self.file_panel = FilePanel()
        self.sem_tab = SemImageTab()
        self.mapping_tab = MappingTab()
        self.spectrum_tab = SpectrumTab()
        self.compare_tab = EmptyState("Compare", "Multi-file comparison will be added after the core single-file workflow is validated.")
        self.export_tab = EmptyState("Export", "Use Copy or Export in each view. Batch export will be added in the next milestone.")

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.addTab(self.sem_tab, "SEM Image")
        self.tabs.addTab(self.mapping_tab, "Mapping")
        self.tabs.addTab(self.spectrum_tab, "Spectrum")
        self.tabs.addTab(self.compare_tab, "Compare")
        self.tabs.addTab(self.export_tab, "Export")

        body_splitter = QSplitter(Qt.Orientation.Horizontal)
        body_splitter.addWidget(self.file_panel)
        body_splitter.addWidget(self.tabs)
        body_splitter.setSizes([225, 1320])
        body_splitter.setStretchFactor(1, 1)

        central = QWidget()
        central_layout = QVBoxLayout(central)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)
        central_layout.addWidget(self._build_top_bar())
        central_layout.addWidget(body_splitter, 1)
        self.setCentralWidget(central)
        self._build_menu()
        self.statusBar().showMessage("Open or drop SEM-CL HDF5 files to begin")

        self.file_panel.file_selected.connect(self.load_file)
        self.sem_tab.status_message.connect(self.statusBar().showMessage)
        self.mapping_tab.status_message.connect(self.statusBar().showMessage)
        self.spectrum_tab.status_message.connect(self.statusBar().showMessage)

    def _build_top_bar(self) -> QFrame:
        bar = QFrame()
        bar.setObjectName("TopBar")
        bar.setFixedHeight(58)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 8, 16, 8)
        self.open_button = QPushButton("Open Files")
        self.open_button.setObjectName("PrimaryButton")
        self.open_button.clicked.connect(self.file_panel.choose_files)
        self.copy_button = QPushButton("Copy Current")
        self.copy_button.clicked.connect(self.copy_current)
        self.export_button = QPushButton("Export Current")
        self.export_button.clicked.connect(self.export_current)
        title = QLabel("SEM-CL Studio")
        title.setObjectName("AppTitle")
        subtitle = QLabel("SEM image · CL mapping · spectrum")
        subtitle.setObjectName("MutedLabel")
        title_layout = QVBoxLayout()
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(0)
        title_layout.addWidget(title)
        title_layout.addWidget(subtitle)
        layout.addWidget(self.open_button)
        layout.addSpacing(12)
        layout.addLayout(title_layout)
        layout.addStretch(1)
        layout.addWidget(self.copy_button)
        layout.addWidget(self.export_button)
        return bar

    def _build_menu(self) -> None:
        file_menu = self.menuBar().addMenu("File")
        open_action = QAction("Open HDF5 files…", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self.file_panel.choose_files)
        export_action = QAction("Export current view…", self)
        export_action.setShortcut(QKeySequence("Ctrl+E"))
        export_action.triggered.connect(self.export_current)
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(open_action)
        file_menu.addAction(export_action)
        file_menu.addSeparator()
        file_menu.addAction(exit_action)

        view_menu = self.menuBar().addMenu("View")
        sem_action = QAction("SEM Image", self)
        sem_action.triggered.connect(lambda: self.tabs.setCurrentWidget(self.sem_tab))
        mapping_action = QAction("Mapping", self)
        mapping_action.triggered.connect(lambda: self.tabs.setCurrentWidget(self.mapping_tab))
        spectrum_action = QAction("Spectrum", self)
        spectrum_action.triggered.connect(lambda: self.tabs.setCurrentWidget(self.spectrum_tab))
        view_menu.addActions([sem_action, mapping_action, spectrum_action])

        help_menu = self.menuBar().addMenu("Help")
        about_action = QAction("About", self)
        about_action.triggered.connect(
            lambda: QMessageBox.information(
                self,
                "SEM-CL Studio",
                "SEM-CL Studio 0.1\n\nRead-only HDF5 mapping and spectrum analysis prototype.",
            )
        )
        help_menu.addAction(about_action)

    def add_files(self, paths: list[str | Path]) -> None:
        hdf5_paths = [Path(path) for path in paths if Path(path).suffix.lower() in {".h5", ".hdf5"}]
        if hdf5_paths:
            self.file_panel.add_paths(hdf5_paths)

    def load_file(self, path: Path) -> None:
        key = str(path.resolve())
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        self.statusBar().showMessage(f"Loading {path.name}…")
        try:
            if key in self._cache:
                dataset = self._cache.pop(key)
                self._cache[key] = dataset
            else:
                dataset = load_semcl_dataset(path)
                self._cache[key] = dataset
                while len(self._cache) > 2:
                    self._cache.popitem(last=False)
            self._active_dataset = dataset
            self.file_panel.set_dataset(dataset)
            self.sem_tab.set_dataset(dataset)
            self.mapping_tab.set_dataset(dataset)
            self.spectrum_tab.set_dataset(dataset)
            self.statusBar().showMessage(
                f"Loaded {path.name}  |  CL {dataset.cl_shape[2]}×{dataset.cl_shape[1]}×{dataset.cl_shape[0]}"
            )
        except (Hdf5ReadError, ValueError, OSError) as exc:
            QMessageBox.critical(self, "Could not load HDF5", str(exc))
            self.statusBar().showMessage(f"Failed to load {path.name}")
        finally:
            QApplication.restoreOverrideCursor()

    def copy_current(self) -> None:
        current = self.tabs.currentWidget()
        if current is self.sem_tab:
            self.sem_tab.image_panel.copy_view()
        elif current is self.mapping_tab:
            self.mapping_tab.cl_panel.copy_view()
        elif current is self.spectrum_tab:
            self.spectrum_tab.copy_figure()

    def export_current(self) -> None:
        current = self.tabs.currentWidget()
        if current is self.sem_tab:
            self.sem_tab.image_panel.export_view()
        elif current is self.mapping_tab:
            self.mapping_tab.cl_panel.export_view()
        elif current is self.spectrum_tab:
            self.spectrum_tab.export_figure()
        else:
            QMessageBox.information(self, "No exportable view", "Open SEM Image, Mapping, or Spectrum first.")

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if any(url.isLocalFile() and Path(url.toLocalFile()).suffix.lower() in {".h5", ".hdf5"} for url in event.mimeData().urls()):
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        self.add_files([url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()])
        event.acceptProposedAction()

