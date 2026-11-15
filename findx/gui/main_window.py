"""Main window: persistent sidebar + stacked module workspaces."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (QButtonGroup, QFrame, QHBoxLayout, QLabel, QMainWindow, QPushButton, QStackedWidget,
                               QVBoxLayout, QWidget)

from .. import APP_NAME, __version__, config as C
from .algebra_page import AlgebraPage
from .calculus_page import CalculusPage
from .diff_page import DifferentiationPage
from .graph_page import GraphPage
from .matrix_page import MatrixPage
from .widgets import hrule


class MainWindow(QMainWindow):
    MODULES = [
        ("Algebra Solver", AlgebraPage),
        ("Matrix Solver", MatrixPage),
        ("Differentiation", DifferentiationPage),
        ("Calculus", CalculusPage),
        ("2D Graphing", GraphPage),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(C.WINDOW_TITLE)
        self.setMinimumSize(1000, 640)
        self.resize(1360, 840)
        root = QWidget(); root.setObjectName("root"); self.setCentralWidget(root)
        h = QHBoxLayout(root); h.setContentsMargins(0, 0, 0, 0); h.setSpacing(0)

        side = QFrame(); side.setObjectName("sidebar"); side.setFixedWidth(230)
        sl = QVBoxLayout(side); sl.setContentsMargins(0, 26, 0, 16); sl.setSpacing(0)
        brand = QLabel(APP_NAME); brand.setObjectName("brand"); brand.setContentsMargins(22, 0, 0, 0)
        sub = QLabel("MATHEMATICAL COMPUTING"); sub.setObjectName("brandSub"); sub.setContentsMargins(24, 0, 0, 0)
        sl.addWidget(brand); sl.addWidget(sub); sl.addSpacing(22)
        rule = QFrame(); rule.setObjectName("sideRule"); sl.addWidget(rule); sl.addSpacing(10)

        self.stack = QStackedWidget()
        self.pages = []
        self.buttons = QButtonGroup(self); self.buttons.setExclusive(True)
        for i, (name, cls) in enumerate(self.MODULES):
            btn = QPushButton(f"{i + 1}   {name}"); btn.setObjectName("nav"); btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            self.buttons.addButton(btn, i); sl.addWidget(btn)
            page = cls(); self.pages.append(page); self.stack.addWidget(page)
            QShortcut(QKeySequence(f"Ctrl+{i + 1}"), self, activated=lambda i=i: self.select(i))
        sl.addStretch(1)
        foot = QLabel(f"Version {__version__}\nSymPy · NumPy · SciPy · Matplotlib"); foot.setObjectName("sideFoot")
        foot.setContentsMargins(22, 0, 0, 0); sl.addWidget(foot)
        self.buttons.idClicked.connect(self.select)
        h.addWidget(side); h.addWidget(self.stack, 1)
        self.statusBar().showMessage("Ready — exact symbolic results are labelled EXACT; numerical results are labelled APPROX.")
        self.select(0)

    def select(self, i: int) -> None:
        self.stack.setCurrentIndex(i)
        self.buttons.button(i).setChecked(True)
        self.setWindowTitle(f"{self.MODULES[i][0]} — {C.WINDOW_TITLE}")
