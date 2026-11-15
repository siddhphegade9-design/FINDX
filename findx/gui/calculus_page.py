"""Calculus workspace (integrals and limits)."""
from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLineEdit, QPushButton, QVBoxLayout

from ..core import calculus as K
from .widgets import ModulePage, examples_combo, field_label, hint_label

MODES = ["Indefinite integral", "Definite integral", "Limit"]
EXAMPLES = [
    ("∫ x·e^x dx", (MODES[0], "x*exp(x)", "x", "", "", "", "both")),
    ("∫ 1/(x^2+1) dx", (MODES[0], "1/(x^2+1)", "x", "", "", "", "both")),
    ("∫₀^π sin(x) dx", (MODES[1], "sin(x)", "x", "0", "pi", "", "both")),
    ("∫ e^(−x²) dx, −∞ to ∞", (MODES[1], "exp(-x^2)", "x", "-oo", "oo", "", "both")),
    ("Numerical: ∫₀^3 sin(x²)cos(x) dx", (MODES[1], "sin(x^2)*cos(x)", "x", "0", "3", "", "both")),
    ("lim x→0 sin(x)/x", (MODES[2], "sin(x)/x", "x", "", "", "0", "both")),
    ("lim x→0 1/x  (one-sided)", (MODES[2], "1/x", "x", "", "", "0", "both")),
    ("lim x→∞ (1+1/x)^x", (MODES[2], "(1+1/x)^x", "x", "", "", "oo", "both")),
]


class CalculusPage(ModulePage):
    TITLE = "Calculus"
    SUBTITLE = "Indefinite and definite integrals, limits and one-sided limits, exact and numerical."

    def build_inputs(self, lay: QVBoxLayout) -> None:
        lay.addWidget(field_label("Task"))
        self.mode = QComboBox(); self.mode.addItems(MODES); self.mode.currentTextChanged.connect(self._mode)
        lay.addWidget(self.mode)
        lay.addWidget(field_label("Expression f"))
        self.expr = QLineEdit("x*exp(x)"); lay.addWidget(self.expr)
        lay.addWidget(field_label("Variable (optional)"))
        self.var = QLineEdit(); self.var.setPlaceholderText("auto-detect"); lay.addWidget(self.var)
        self.lo_label, self.hi_label = field_label("Lower limit a"), field_label("Upper limit b")
        self.lo, self.hi = QLineEdit("0"), QLineEdit("1")
        for w in (self.lo_label, self.lo, self.hi_label, self.hi):
            lay.addWidget(w)
        self.pt_label, self.pt = field_label("Approach point"), QLineEdit("0")
        self.dir_label, self.dir = field_label("Direction"), QComboBox()
        self.dir.addItem("Two-sided (shows left and right)", "both")
        self.dir.addItem("Right-hand  (x → a⁺)", "+")
        self.dir.addItem("Left-hand  (x → a⁻)", "-")
        for w in (self.pt_label, self.pt, self.dir_label, self.dir):
            lay.addWidget(w)
        self.hint = hint_label("Use oo for infinity, e.g. -oo or oo.")
        lay.addWidget(self.hint)
        lay.addSpacing(6)
        lay.addWidget(examples_combo(EXAMPLES, self._example))
        row = QHBoxLayout()
        self.go = QPushButton("Compute"); self.go.setObjectName("primary"); self.go.clicked.connect(self.compute)
        clear = QPushButton("Clear"); clear.clicked.connect(self.clear)
        row.addWidget(self.go, 1); row.addWidget(clear)
        lay.addLayout(row); lay.addStretch(1)
        self._mode(self.mode.currentText())

    def _mode(self, m: str) -> None:
        definite, lim = m == MODES[1], m == MODES[2]
        for w in (self.lo_label, self.lo, self.hi_label, self.hi):
            w.setVisible(definite)
        for w in (self.pt_label, self.pt, self.dir_label, self.dir):
            w.setVisible(lim)
        self.hint.setText("Use oo for infinity, e.g. -oo or oo." if (definite or lim) else
                          "The result is shown together with the constant of integration C.")

    def _example(self, p) -> None:
        mode, e, v, lo, hi, pt, d = p
        self.mode.setCurrentText(mode); self.expr.setText(e); self.var.setText("" if v == "x" else v)
        if lo or hi:
            self.lo.setText(lo); self.hi.setText(hi)
        if pt:
            self.pt.setText(pt)
        self.dir.setCurrentIndex(max(0, self.dir.findData(d)))
        self.compute()

    def clear(self) -> None:
        self.expr.clear(); self.result_view.show_placeholder()

    def compute(self) -> None:
        m, e, v = self.mode.currentText(), self.expr.text(), self.var.text()
        if m == MODES[0]:
            self.run_task(lambda: K.integrate_indefinite(e, v))
        elif m == MODES[1]:
            lo, hi = self.lo.text(), self.hi.text()
            self.run_task(lambda: K.integrate_definite(e, lo, hi, v))
        else:
            pt, d = self.pt.text(), self.dir.currentData()
            self.run_task(lambda: K.limit(e, pt, d, v))
