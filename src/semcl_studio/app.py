from __future__ import annotations

import sys
from pathlib import Path

import pyqtgraph as pg
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from semcl_studio.ui.main_window import MainWindow
from semcl_studio.ui.theme import APP_STYLESHEET


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv if argv is None else argv)
    pg.setConfigOptions(imageAxisOrder="row-major", antialias=True)
    application = QApplication(arguments)
    application.setApplicationName("SEM-CL Studio")
    application.setOrganizationName("SEM-CL Studio")
    application.setStyle("Fusion")
    application.setFont(QFont("Segoe UI", 9))
    application.setStyleSheet(APP_STYLESHEET)
    window = MainWindow()
    window.show()
    file_arguments = [Path(value) for value in arguments[1:] if Path(value).suffix.lower() in {".h5", ".hdf5"}]
    if file_arguments:
        window.add_files(file_arguments)
    return application.exec()
