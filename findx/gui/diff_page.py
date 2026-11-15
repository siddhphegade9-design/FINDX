"""Differentiation workspace."""
from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLineEdit, QPushButton, QSpinBox, QVBoxLayout

from ..core import differentiation as D
from .widgets import ModulePage, examples_combo, field_label, hint_label

MODES = ["Derivative (ordinary / higher order)", "Partial derivative", "Implicit differentiation", "Gradient"]
EXAMPLES = [
    ("d/dx [x^3 sin(x)]", (MODES[0], "x^3*sin(x)", "x", 1, "x=pi")),
    ("Second derivative of exp(-x^2)", (MODES[0], "exp(-x^2)", "x", 2, "x=0")),
    ("∂²f/∂x∂y of x^2*y^3 + sin(x*y)", (MODES[1], "x^2*y^3 + sin(x*y)", "x, y", 1, "x=1, y=2")),
    ("Implicit: x^2 + y^2 = 25", (MODES[2], "x^2 + y^2 = 25", "x", 1, "x=3, y=4")),
    ("Gradient of x^2 + x*y + y^2", (MODES[3], "x^2 + x*y + y^2", "x, y", 1, "")),
]


class DifferentiationPage(ModulePage):
    TITLE = "Differentiation"
    SUBTITLE = "Symbolic derivatives of any order, partial and implicit derivatives, evaluated at points."

    def build_inputs(self, lay: QVBoxLayout) -> None:
        lay.addWidget(field_label("Task"))
        self.mode = QComboBox(); self.mode.addItems(MODES); self.mode.currentTextChanged.connect(self._mode)
        lay.addWidget(self.mode)
        self.expr_label = field_label("Expression f")
        lay.addWidget(self.expr_label)
        self.expr = QLineEdit("x^3*sin(x)")
        lay.addWidget(self.expr)
        self.var_label = field_label("With respect to")
        lay.addWidget(self.var_label)
        self.var = QLineEdit("x")
        lay.addWidget(self.var)
        self.order_label = field_label("Order")
        self.order = QSpinBox(); self.order.setRange(1, 10); self.order.setValue(1)
        lay.addWidget(self.order_label); lay.addWidget(self.order)
        self.point_label = field_label("Evaluate at (optional)")
        self.point = QLineEdit(); self.point.setPlaceholderText("e.g. x=2   or   x=1, y=3")
        lay.addWidget(self.point_label); lay.addWidget(self.point)
        self.hint = hint_label("")
        lay.addWidget(self.hint)
        lay.addSpacing(6)
        lay.addWidget(examples_combo(EXAMPLES, self._example))
        row = QHBoxLayout()
        self.go = QPushButton("Differentiate"); self.go.setObjectName("primary"); self.go.clicked.connect(self.compute)
        clear = QPushButton("Clear"); clear.clicked.connect(self.clear)
        row.addWidget(self.go, 1); row.addWidget(clear)
        lay.addLayout(row); lay.addStretch(1)
        self._mode(self.mode.currentText())

    def _mode(self, m: str) -> None:
        implicit, grad, partial = m == MODES[2], m == MODES[3], m == MODES[1]
        self.expr_label.setText("EQUATION F(x, y) = 0" if implicit else "EXPRESSION f")
        self.var_label.setText("INDEPENDENT VARIABLE" if implicit else "VARIABLES" if (partial or grad) else "WITH RESPECT TO")
        self.order.setVisible(not grad); self.order_label.setVisible(not grad)
        self.point.setVisible(not grad); self.point_label.setVisible(not grad)
        if m == MODES[0]:
            self.hint.setText("Other symbols are treated as constants.")
        elif partial:
            self.hint.setText("List variables in order, e.g. 'x, y' gives ∂²f/∂y∂x. The order applies to each variable.")
        elif implicit:
            self.hint.setText("y is treated as an unknown function of the variable; dy/dx = −Fₓ/F_y. Order 1 or 2.")
            if self.var.text().strip() not in ("x",):
                self.var.setText("x")
        else:
            self.hint.setText("All first-order partial derivatives are listed with the gradient vector.")

    def _example(self, p) -> None:
        mode, e, v, o, pt = p
        self.mode.setCurrentText(mode); self.expr.setText(e); self.var.setText(v); self.order.setValue(o); self.point.setText(pt)
        self.compute()

    def clear(self) -> None:
        self.expr.clear(); self.point.clear(); self.result_view.show_placeholder()

    def compute(self) -> None:
        m = self.mode.currentText()
        e, v, o, pt = self.expr.text(), self.var.text(), self.order.value(), self.point.text()
        if m == MODES[2]:
            self.run_task(lambda: D.implicit_differentiate(e, v.strip() or "x", "y", o, pt))
        elif m == MODES[3]:
            self.run_task(lambda: D.gradient(e, v))
        else:
            self.run_task(lambda: D.differentiate(e, v, o, pt))
