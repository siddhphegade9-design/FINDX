"""2D Graphing workspace with an embedded Matplotlib canvas."""
from __future__ import annotations

from typing import List, Optional

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import (QCheckBox, QDoubleSpinBox, QFileDialog, QFrame, QGridLayout, QHBoxLayout, QLabel,
                               QPlainTextEdit, QPushButton, QSplitter, QVBoxLayout, QWidget, QComboBox)

from .. import config as C
from ..core import graphing as G
from ..core.errors import FindxError
from .widgets import ModulePage, Worker, examples_combo, field_label, hint_label

EXAMPLES = [
    ("Parabola and line", "x^2 - 4\nx + 2"),
    ("Trigonometric", "sin(x)\ncos(x)\nsin(x)/x"),
    ("Poles: tan(x) and 1/x", "tan(x)\n1/x"),
    ("Cubic with three roots", "x^3 - 6x^2 + 11x - 6"),
    ("Double root", "(x-1)^2\n-(x-1)^2 + 1"),
    ("Exponential vs logarithm", "exp(x)\nln(x)\nx"),
]


def _pretty_label(curve: G.Curve) -> str:
    return "y = " + str(curve.expr).replace("**", "^").replace("*", "·")


class GraphPage(ModulePage):
    TITLE = "2D Graphing"
    SUBTITLE = "Plot several functions, pan and zoom, and locate roots and intersections numerically."
    INPUT_WIDTH = 380

    # -- layout ------------------------------------------------------------
    def build_inputs(self, lay: QVBoxLayout) -> None:
        lay.addWidget(field_label("Functions of x (one per line)"))
        self.funcs = QPlainTextEdit(); self.funcs.setFixedHeight(120)
        self.funcs.setPlainText("x^2 - 4\nx + 2")
        lay.addWidget(self.funcs)
        lay.addWidget(hint_label("Write y = … or just the expression. Up to 8 curves."))
        grid = QGridLayout(); grid.setHorizontalSpacing(8); grid.setVerticalSpacing(4)
        self.xmin, self.xmax = self._spin(-6), self._spin(6)
        self.ymin, self.ymax = self._spin(-8), self._spin(8)
        grid.addWidget(field_label("x min"), 0, 0); grid.addWidget(field_label("x max"), 0, 1)
        grid.addWidget(self.xmin, 1, 0); grid.addWidget(self.xmax, 1, 1)
        grid.addWidget(field_label("y min"), 2, 0); grid.addWidget(field_label("y max"), 2, 1)
        grid.addWidget(self.ymin, 3, 0); grid.addWidget(self.ymax, 3, 1)
        lay.addLayout(grid)
        self.auto_y = QCheckBox("Automatic y-range"); self.auto_y.setChecked(True)
        self.auto_y.toggled.connect(lambda on: (self.ymin.setEnabled(not on), self.ymax.setEnabled(not on)))
        self.ymin.setEnabled(False); self.ymax.setEnabled(False)
        lay.addWidget(self.auto_y)
        self.grid_cb = QCheckBox("Grid"); self.grid_cb.setChecked(True)
        self.axes_cb = QCheckBox("Axes through origin"); self.axes_cb.setChecked(True)
        self.legend_cb = QCheckBox("Legend"); self.legend_cb.setChecked(True)
        self.roots_cb = QCheckBox("Detect roots"); self.roots_cb.setChecked(True)
        self.inter_cb = QCheckBox("Detect intersections"); self.inter_cb.setChecked(True)
        row = QGridLayout()
        for i, cb in enumerate((self.grid_cb, self.axes_cb, self.legend_cb, self.roots_cb, self.inter_cb)):
            row.addWidget(cb, i // 2, i % 2)
        lay.addLayout(row)
        for cb in (self.grid_cb, self.axes_cb, self.legend_cb):
            cb.toggled.connect(self._style_changed)
        lay.addSpacing(4)
        lay.addWidget(examples_combo([(l, t) for l, t in EXAMPLES], self._example))
        r1 = QHBoxLayout()
        self.plot_btn = QPushButton("Plot"); self.plot_btn.setObjectName("primary"); self.plot_btn.clicked.connect(self.plot)
        reset = QPushButton("Reset view"); reset.clicked.connect(self.reset_view)
        r1.addWidget(self.plot_btn, 1); r1.addWidget(reset)
        lay.addLayout(r1)
        r2 = QHBoxLayout()
        detect = QPushButton("Re-detect in current view"); detect.clicked.connect(self.detect_in_view)
        save = QPushButton("Save PNG…"); save.clicked.connect(self.save_png)
        r2.addWidget(detect, 1); r2.addWidget(save)
        lay.addLayout(r2)
        lay.addWidget(hint_label("Toolbar: zoom-rectangle and pan tools; mouse wheel zooms at the cursor. "
                                 "Curves are re-sampled after every zoom/pan."))
        lay.addStretch(1)

    @staticmethod
    def _spin(v: float) -> QDoubleSpinBox:
        s = QDoubleSpinBox(); s.setRange(-1e9, 1e9); s.setDecimals(4); s.setValue(v); s.setSingleStep(1.0)
        s.setGroupSeparatorShown(False)
        return s

    def build_results_area(self) -> QWidget:
        wrap = QSplitter(Qt.Vertical); wrap.setChildrenCollapsible(False)
        plot_box = QWidget(); pl = QVBoxLayout(plot_box); pl.setContentsMargins(0, 0, 0, 0); pl.setSpacing(0)
        self.figure = Figure(figsize=(6, 4.5), dpi=100)
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.toolbar = NavigationToolbar2QT(self.canvas, plot_box)
        pl.addWidget(self.toolbar); pl.addWidget(self.canvas, 1)
        self.ax = self.figure.add_subplot(111)
        self.figure.subplots_adjust(left=0.07, right=0.98, top=0.97, bottom=0.08)
        self._style_axes()
        wrap.addWidget(plot_box)
        self.analysis_text = QPlainTextEdit(); self.analysis_text.setObjectName("analysis"); self.analysis_text.setReadOnly(True)
        self.analysis_text.setPlaceholderText("Roots and intersections appear here after plotting.")
        wrap.addWidget(self.analysis_text)
        wrap.setStretchFactor(0, 4); wrap.setStretchFactor(1, 1)
        self.splitter.addWidget(wrap)
        # Result view for errors (shared infrastructure) lives inside analysis text; keep API compatible
        from .widgets import ResultView
        self.result_view = ResultView()   # not shown; used only for plain-text API compatibility
        self.copy_btn = QPushButton()
        # state
        self.curves: List[G.Curve] = []
        self.lines = []
        self.markers = []
        self.initial_view = (-6.0, 6.0, -8.0, 8.0)
        self._resample_timer = QTimer(self); self._resample_timer.setSingleShot(True); self._resample_timer.setInterval(40)
        self._resample_timer.timeout.connect(self._resample)
        self.ax.callbacks.connect("xlim_changed", lambda _ax: self._resample_timer.start())
        self.canvas.mpl_connect("scroll_event", self._on_scroll)
        self.analysis = None
        return wrap

    # -- styling -----------------------------------------------------------
    def _style_axes(self) -> None:
        ax = self.ax
        ax.grid(self.grid_cb.isChecked() if hasattr(self, "grid_cb") else True, which="major")
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        ax.set_xlabel("x"); ax.set_ylabel("y")

    def _style_changed(self) -> None:
        self._draw_decorations()
        self.canvas.draw_idle()

    def _draw_decorations(self) -> None:
        ax = self.ax
        ax.grid(self.grid_cb.isChecked())
        for ln in getattr(self, "_axis_lines", []):
            ln.remove()
        self._axis_lines = []
        if self.axes_cb.isChecked():
            self._axis_lines.append(ax.axhline(0, color=C.CHARCOAL, lw=0.9, zorder=1))
            self._axis_lines.append(ax.axvline(0, color=C.CHARCOAL, lw=0.9, zorder=1))
        leg = ax.get_legend()
        if leg:
            leg.remove()
        if self.legend_cb.isChecked() and self.lines:
            ax.legend(handles=self.lines, loc="best", fontsize=9)

    # -- actions -----------------------------------------------------------
    def _example(self, text) -> None:
        self.funcs.setPlainText(text)
        self.plot()

    def _read_inputs(self):
        lines = [l.strip() for l in self.funcs.toPlainText().splitlines() if l.strip()]
        if not lines:
            raise G.InputError("Enter at least one function.")
        if len(lines) > len(C.CURVE_COLOURS):
            raise G.InputError(f"At most {len(C.CURVE_COLOURS)} functions can be plotted at once.")
        curves = [G.compile_function(t) for t in lines]
        x0, x1 = self.xmin.value(), self.xmax.value()
        if x0 >= x1:
            raise G.InputError("x min must be smaller than x max.")
        if not self.auto_y.isChecked() and self.ymin.value() >= self.ymax.value():
            raise G.InputError("y min must be smaller than y max.")
        return curves, x0, x1

    def plot(self) -> None:
        try:
            curves, x0, x1 = self._read_inputs()
        except FindxError as exc:
            self.analysis_text.setPlainText("Error: " + str(exc)); return
        self.curves = curves
        ax = self.ax
        ax.clear(); self._axis_lines = []
        self.lines, self.markers = [], []
        for i, c in enumerate(curves):
            xs, ys = G.sample_curve(c, x0, x1)
            (ln,) = ax.plot(xs, ys, color=C.CURVE_COLOURS[i % len(C.CURVE_COLOURS)], lw=1.8, label=_pretty_label(c), zorder=3)
            self.lines.append(ln)
        if self.auto_y.isChecked():
            y0, y1 = G.auto_y_range(curves, x0, x1)
            self.ymin.setValue(y0); self.ymax.setValue(y1)
        else:
            y0, y1 = self.ymin.value(), self.ymax.value()
        self._resample_timer.stop()
        ax.set_xlim(x0, x1); ax.set_ylim(y0, y1)
        self.initial_view = (x0, x1, y0, y1)
        self._style_axes(); self._draw_decorations()
        self.canvas.draw_idle()
        self.toolbar.update()   # reset the navigation history to this view
        self.analyse_range(x0, x1)

    def reset_view(self) -> None:
        x0, x1, y0, y1 = self.initial_view
        self.ax.set_xlim(x0, x1); self.ax.set_ylim(y0, y1)
        self.canvas.draw_idle()

    def detect_in_view(self) -> None:
        if not self.curves:
            self.plot(); return
        x0, x1 = self.ax.get_xlim()
        self.analyse_range(x0, x1)

    def analyse_range(self, x0: float, x1: float) -> None:
        if not (self.roots_cb.isChecked() or self.inter_cb.isChecked()):
            self._clear_markers(); self.analysis_text.setPlainText("Root and intersection detection is switched off."); return
        curves = list(self.curves)
        roots_on, inter_on = self.roots_cb.isChecked(), self.inter_cb.isChecked()
        self._token += 1; token = self._token; self._pending += 1
        self.analysis_text.setPlainText("Analysing…")
        w = Worker(token, lambda: G.analyse(curves, x0, x1, roots_on, inter_on))
        self._workers[token] = w

        def ok(tok, res):
            self._pending -= 1; self._workers.pop(tok, None)
            if tok != self._token:
                return
            self.analysis = res
            self._show_analysis(curves, res)

        def bad(tok, msg):
            self._pending -= 1; self._workers.pop(tok, None)
            if tok == self._token:
                self.analysis_text.setPlainText("Analysis failed: " + msg)
        w.signals.done.connect(ok, Qt.QueuedConnection); w.signals.failed.connect(bad, Qt.QueuedConnection)
        self._pool.start(w)

    def _clear_markers(self) -> None:
        for m in self.markers:
            try:
                m.remove()
            except Exception:
                pass
        self.markers = []

    def _show_analysis(self, curves, res: G.AnalysisResult) -> None:
        self._clear_markers()
        total = sum(len(r) for r in res.roots) + len(res.intersections)
        annotate = total <= 8
        for i, rs in enumerate(res.roots):
            for r in rs:
                self.markers.append(self.ax.scatter([r], [0], s=46, facecolor="#FFFFFF", edgecolor=C.BRONZE, linewidths=1.8, zorder=5))
                if annotate:
                    self.markers.append(self.ax.annotate(f"({r:.4g}, 0)", (r, 0), textcoords="offset points", xytext=(5, -13),
                                                         fontsize=8, color=C.BRONZE_DARK, zorder=6))
        for p in res.intersections:
            self.markers.append(self.ax.scatter([p.x], [p.y], s=46, marker="D", facecolor="#FFFFFF", edgecolor=C.BRICK, linewidths=1.8, zorder=5))
            if annotate:
                self.markers.append(self.ax.annotate(f"({p.x:.4g}, {p.y:.4g})", (p.x, p.y), textcoords="offset points", xytext=(5, 6),
                                                     fontsize=8, color=C.BRICK, zorder=6))
        self.canvas.draw_idle()
        self.analysis_text.setPlainText(G.format_analysis(curves, res))

    # -- interactive resampling & zoom --------------------------------------
    def _resample(self) -> None:
        if not self.curves:
            return
        x0, x1 = self.ax.get_xlim()
        for c, ln in zip(self.curves, self.lines):
            try:
                xs, ys = G.sample_curve(c, x0, x1)
            except FindxError:
                continue
            ln.set_data(xs, ys)
        self.canvas.draw_idle()

    def _on_scroll(self, event) -> None:
        if event.inaxes is not self.ax or event.xdata is None:
            return
        k = 0.8 if event.button == "up" else 1.25
        x0, x1 = self.ax.get_xlim(); y0, y1 = self.ax.get_ylim()
        self.ax.set_xlim(event.xdata - (event.xdata - x0) * k, event.xdata + (x1 - event.xdata) * k)
        self.ax.set_ylim(event.ydata - (event.ydata - y0) * k, event.ydata + (y1 - event.ydata) * k)
        self.canvas.draw_idle()

    def save_png(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Save graph", "graph.png", "PNG image (*.png)")
        if path:
            self.figure.savefig(path, dpi=200, facecolor=self.figure.get_facecolor())

    def wait_idle(self, timeout_ms: int = 60000) -> bool:
        ok = super().wait_idle(timeout_ms)
        self._resample()
        return ok
