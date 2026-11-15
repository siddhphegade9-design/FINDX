"""Algebra Solver workspace."""
from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLineEdit, QPlainTextEdit, QPushButton, QVBoxLayout

from ..core import algebra
from .widgets import ModulePage, examples_combo, field_label, hint_label

MODES = ["Solve equation", "Solve system of equations", "Factor polynomial"]

EXAMPLES = [
    ("Linear:  3x + 7 = 22", ("Solve equation", "3x + 7 = 22")),
    ("Quadratic:  x^2 - 5x + 6 = 0", ("Solve equation", "x^2 - 5x + 6 = 0")),
    ("Complex roots:  x^2 + 2x + 5 = 0", ("Solve equation", "x^2 + 2x + 5 = 0")),
    ("Repeated root:  (x-2)^3 = 0", ("Solve equation", "(x-2)^3 = 0")),
    ("Cubic:  x^3 - 6x^2 + 11x - 6 = 0", ("Solve equation", "x^3 - 6x^2 + 11x - 6 = 0")),
    ("Quintic (numerical):  x^5 - x - 1 = 0", ("Solve equation", "x^5 - x - 1 = 0")),
    ("Transcendental:  cos(x) = x", ("Solve equation", "cos(x) = x")),
    ("Parametric:  a*x^2 + b*x + c = 0", ("Solve equation", "a*x^2 + b*x + c = 0")),
    ("Linear system", ("Solve system of equations", "2x + y = 5\nx - y = 1")),
    ("Non-linear system", ("Solve system of equations", "x^2 + y^2 = 25\nx - y = 1")),
    ("Factor:  x^4 - 1", ("Factor polynomial", "x^4 - 1")),
]


class AlgebraPage(ModulePage):
    TITLE = "Algebra Solver"
    SUBTITLE = "Linear, quadratic, cubic and higher-degree equations, systems, and factorisation."

    def build_inputs(self, lay: QVBoxLayout) -> None:
        lay.addWidget(field_label("Task"))
        self.mode = QComboBox(); self.mode.addItems(MODES); self.mode.currentTextChanged.connect(self._mode_changed)
        lay.addWidget(self.mode)
        self.eq_label = field_label("Equation")
        lay.addWidget(self.eq_label)
        self.equation = QPlainTextEdit(); self.equation.setFixedHeight(96)
        self.equation.setPlainText("x^2 - 5x + 6 = 0")
        lay.addWidget(self.equation)
        self.eq_hint = hint_label("Use ^ for powers, * is optional (2x), sqrt(), sin(), exp(), pi.")
        lay.addWidget(self.eq_hint)
        self.var_label = field_label("Solve for (optional)")
        lay.addWidget(self.var_label)
        self.variable = QLineEdit(); self.variable.setPlaceholderText("auto-detect, e.g. x")
        lay.addWidget(self.variable)
        lay.addSpacing(6)
        self.examples = examples_combo(EXAMPLES, self._load_example)
        lay.addWidget(self.examples)
        row = QHBoxLayout()
        self.solve_btn = QPushButton("Solve"); self.solve_btn.setObjectName("primary"); self.solve_btn.clicked.connect(self.solve)
        clear = QPushButton("Clear"); clear.clicked.connect(self.clear)
        row.addWidget(self.solve_btn, 1); row.addWidget(clear)
        lay.addLayout(row)
        lay.addStretch(1)
        self._mode_changed(self.mode.currentText())

    def _mode_changed(self, mode: str) -> None:
        if mode == "Solve system of equations":
            self.eq_label.setText("EQUATIONS (ONE PER LINE)")
            self.eq_hint.setText("Separate equations with new lines or semicolons. Linear and polynomial systems are supported.")
            self.var_label.setText("UNKNOWNS (OPTIONAL)")
            self.variable.setPlaceholderText("auto-detect, e.g. x, y")
        elif mode == "Factor polynomial":
            self.eq_label.setText("POLYNOMIAL")
            self.eq_hint.setText("Factorised over the rationals; the Gaussian-rational factorisation is added when it differs.")
            self.var_label.setText("VARIABLE (OPTIONAL)")
            self.variable.setPlaceholderText("auto-detect")
        else:
            self.eq_label.setText("EQUATION")
            self.eq_hint.setText("Use ^ for powers, * is optional (2x), sqrt(), sin(), exp(), pi. Letters other than the unknown act as parameters.")
            self.var_label.setText("SOLVE FOR (OPTIONAL)")
            self.variable.setPlaceholderText("auto-detect, e.g. x")

    def _load_example(self, payload) -> None:
        mode, text = payload
        self.mode.setCurrentText(mode); self.equation.setPlainText(text)
        self.solve()

    def clear(self) -> None:
        self.equation.clear(); self.variable.clear(); self.result_view.show_placeholder()

    def solve(self) -> None:
        mode = self.mode.currentText()
        text = self.equation.toPlainText()
        var = self.variable.text().strip() or None
        if mode == "Solve equation":
            fn = lambda: algebra.solve_equation(text, var)
        elif mode == "Solve system of equations":
            def fn():
                parts = [p for p in text.replace(";", "\n").splitlines() if p.strip()]
                if len(parts) < 2:
                    from ..core.errors import InputError
                    raise InputError("Enter at least two equations (one per line) for a system.")
                return algebra.solve_system(parts, var)
        else:
            fn = lambda: algebra.factor_polynomial(text, var)
        self.run_task(fn)
