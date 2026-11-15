"""Matrix Solver workspace with editable grids."""
from __future__ import annotations

from typing import List

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QComboBox, QFrame, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QPushButton,
                               QSpinBox, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from ..core import matrix as M
from ..core.errors import InputError
from .widgets import ModulePage, field_label, hint_label


class MatrixGrid(QWidget):
    """A titled, resizable grid of editable cells."""

    def __init__(self, title: str, rows: int = 3, cols: int = 3) -> None:
        super().__init__()
        lay = QVBoxLayout(self); lay.setContentsMargins(0, 0, 0, 0); lay.setSpacing(4)
        head = QHBoxLayout()
        self.title_label = field_label(f"Matrix {title}")
        head.addWidget(self.title_label)
        head.addStretch(1)
        self.rows_spin = QSpinBox(); self.rows_spin.setRange(1, M.MAX_DIM); self.rows_spin.setValue(rows)
        self.cols_spin = QSpinBox(); self.cols_spin.setRange(1, M.MAX_DIM); self.cols_spin.setValue(cols)
        for w in (self.rows_spin, self.cols_spin):
            w.setFixedWidth(58)
        lab_r, lab_c = QLabel("rows"), QLabel("cols"); lab_r.setObjectName("hint"); lab_c.setObjectName("hint")
        head.addWidget(lab_r); head.addWidget(self.rows_spin); head.addWidget(lab_c); head.addWidget(self.cols_spin)
        lay.addLayout(head)
        self.table = QTableWidget(rows, cols)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.table.horizontalHeader().setDefaultSectionSize(64)
        self.table.verticalHeader().setDefaultSectionSize(32)
        lay.addWidget(self.table)
        self.rows_spin.valueChanged.connect(self._resize)
        self.cols_spin.valueChanged.connect(self._resize)
        self._fill_blank(0, 0)
        self._fit()

    def _fill_blank(self, r0: int, c0: int) -> None:
        for r in range(self.table.rowCount()):
            for c in range(self.table.columnCount()):
                if self.table.item(r, c) is None:
                    it = QTableWidgetItem("0"); it.setTextAlignment(Qt.AlignCenter)
                    self.table.setItem(r, c, it)

    def _resize(self) -> None:
        self.table.setRowCount(self.rows_spin.value()); self.table.setColumnCount(self.cols_spin.value())
        self._fill_blank(0, 0); self._fit()

    def _fit(self) -> None:
        w = min(self.table.columnCount(), 5) * 64 + self.table.verticalHeader().width() + 4
        h = min(self.table.rowCount(), 6) * 32 + self.table.horizontalHeader().height() + 4
        self.table.setFixedSize(max(w, 120) + (14 if self.table.columnCount() > 5 else 0), h + (14 if self.table.rowCount() > 6 else 0))

    def set_dims(self, r: int, c: int) -> None:
        self.rows_spin.setValue(r); self.cols_spin.setValue(c)

    def set_values(self, rows: List[List[str]]) -> None:
        self.set_dims(len(rows), len(rows[0]))
        for r, row in enumerate(rows):
            for c, v in enumerate(row):
                self.table.item(r, c).setText(str(v))

    def rows(self) -> List[List[str]]:
        return [[(self.table.item(r, c).text() if self.table.item(r, c) else "") for c in range(self.table.columnCount())]
                for r in range(self.table.rowCount())]

    def fill(self, kind: str) -> None:
        for r in range(self.table.rowCount()):
            for c in range(self.table.columnCount()):
                self.table.item(r, c).setText("1" if (kind == "identity" and r == c) else "0")


class MatrixPage(ModulePage):
    TITLE = "Matrix Solver"
    SUBTITLE = "Exact matrix arithmetic, determinants, inverses, eigen-analysis and linear systems."
    INPUT_WIDTH = 440

    def build_inputs(self, lay: QVBoxLayout) -> None:
        lay.addWidget(field_label("Operation"))
        self.op = QComboBox(); self.op.addItems(list(M.OPERATIONS.keys())); self.op.currentTextChanged.connect(self._op_changed)
        lay.addWidget(self.op)
        self.a = MatrixGrid("A", 3, 3)
        lay.addWidget(self.a)
        row = QHBoxLayout()
        ident = QPushButton("Identity"); zero = QPushButton("Zeros")
        ident.clicked.connect(lambda: self.a.fill("identity")); zero.clicked.connect(lambda: self.a.fill("zeros"))
        row.addWidget(ident); row.addWidget(zero); row.addStretch(1)
        lay.addLayout(row)
        self.b_title = "B"
        self.b = MatrixGrid("B", 3, 3)
        lay.addWidget(self.b)
        self.scalar_label = field_label("Scalar k")
        self.scalar = QLineEdit("2"); self.scalar.setPlaceholderText("e.g. 3, -1/2, sqrt(2)")
        lay.addWidget(self.scalar_label); lay.addWidget(self.scalar)
        lay.addWidget(hint_label("Entries may be integers, decimals (0.5) or fractions (1/3); all arithmetic is exact."))
        row = QHBoxLayout()
        self.go = QPushButton("Compute"); self.go.setObjectName("primary"); self.go.clicked.connect(self.compute)
        ex = QPushButton("Example"); ex.clicked.connect(self.load_example)
        row.addWidget(self.go, 1); row.addWidget(ex)
        lay.addLayout(row)
        lay.addStretch(1)
        self.a.rows_spin.valueChanged.connect(self._sync_b)
        self.a.set_values([["2", "1", "0"], ["1", "3", "1"], ["0", "1", "4"]])
        self.b.set_values([["1", "0", "2"], ["0", "1", "1"], ["1", "1", "0"]])
        self._op_changed(self.op.currentText())

    def _kind(self) -> str:
        return M.OPERATIONS[self.op.currentText()][0]

    def _op_changed(self, _: str) -> None:
        k = self._kind()
        self.b.setVisible(k in ("binary", "system"))
        self.scalar.setVisible(k == "scalar"); self.scalar_label.setVisible(k == "scalar")
        if k == "system":
            self.b.cols_spin.setValue(1); self.b.cols_spin.setEnabled(False); self.b.rows_spin.setEnabled(False)
            self._sync_b()
            self.b.title_label.setText("VECTOR B  (A·x = b)")
        else:
            self.b.cols_spin.setEnabled(True); self.b.rows_spin.setEnabled(True)
            self.b.title_label.setText("MATRIX B")

    def _sync_b(self) -> None:
        if self._kind() == "system":
            self.b.rows_spin.setEnabled(True)
            self.b.rows_spin.setValue(self.a.rows_spin.value())
            self.b.rows_spin.setEnabled(False)

    def load_example(self) -> None:
        op = self.op.currentText()
        if self._kind() == "system":
            self.a.set_values([["2", "1", "-1"], ["-3", "-1", "2"], ["-2", "1", "2"]])
            self.b.set_values([["8"], ["-11"], ["-3"]])
        else:
            self.a.set_values([["2", "1", "0"], ["1", "3", "1"], ["0", "1", "4"]])
            self.b.set_values([["1", "0", "2"], ["0", "1", "1"], ["1", "1", "0"]])
        self.compute()

    def compute(self) -> None:
        kind, fn = M.OPERATIONS[self.op.currentText()]
        a_rows, b_rows, scalar = self.a.rows(), self.b.rows(), self.scalar.text()

        def job():
            A = M.build_matrix(a_rows)
            if kind == "unary":
                return fn(A)
            if kind == "scalar":
                return fn(A, scalar)
            B = M.build_matrix(b_rows)
            return fn(A, B)
        self.run_task(job)
