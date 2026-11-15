"""Application bootstrap."""
from __future__ import annotations

import logging
import sys

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from . import APP_NAME
from .gui.main_window import MainWindow
from .gui.theme import apply_matplotlib_style, stylesheet


def create_app(argv=None) -> QApplication:
    app = QApplication.instance() or QApplication(argv or sys.argv)
    app.setApplicationName(APP_NAME)
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 10))
    app.setStyleSheet(stylesheet())
    apply_matplotlib_style()
    return app


def main() -> int:
    logging.basicConfig(level=logging.WARNING)
    if "--selftest" in sys.argv:
        from .selftest import run
        return run()
    app = create_app()
    win = MainWindow()
    win.show()
    return app.exec()
