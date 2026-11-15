"""Reusable GUI building blocks: result viewer, background worker, module page base."""
from __future__ import annotations

import logging
import traceback
from typing import Callable, Optional

from PySide6.QtCore import QObject, QRunnable, QThreadPool, QUrl, Qt, Signal, QCoreApplication
from PySide6.QtGui import QGuiApplication, QTextDocument
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QSplitter,
                               QTextBrowser, QVBoxLayout, QWidget, QComboBox)

from .. import config as C
from ..core.errors import FindxError
from ..core.report import Report
from .render import build_html

log = logging.getLogger("findx")


# ---------------------------------------------------------------------------
class _Signals(QObject):
    done = Signal(int, object)
    failed = Signal(int, str)


class Worker(QRunnable):
    """Runs a callable off the GUI thread and reports success or a friendly error."""

    def __init__(self, token: int, fn: Callable[[], object]):
        super().__init__()
        self.token, self.fn = token, fn
        self.signals = _Signals()

    def run(self) -> None:  # executed in a pool thread
        try:
            result = self.fn()
        except FindxError as exc:
            self.signals.failed.emit(self.token, str(exc))
        except RecursionError:
            self.signals.failed.emit(self.token, "The expression is too complex to process (recursion limit reached).")
        except MemoryError:
            self.signals.failed.emit(self.token, "Not enough memory to complete this computation.")
        except Exception as exc:  # noqa: BLE001 - last-resort guard so the GUI never crashes
            log.error("Unexpected error:\n%s", traceback.format_exc())
            self.signals.failed.emit(self.token, f"Unexpected error: {type(exc).__name__}: {exc}")
        else:
            self.signals.done.emit(self.token, result)


# ---------------------------------------------------------------------------
class ResultView(QTextBrowser):
    """Rich-text viewer for ``Report`` objects."""

    def __init__(self) -> None:
        super().__init__()
        self.setOpenLinks(False)
        self._plain = ""
        self.show_placeholder()

    def show_placeholder(self, text: str = "Results appear here.") -> None:
        self._plain = ""
        self.setHtml(f'<p style="color:{C.STONE}; font-family:{C.SERIF_FONTS}; font-size:12pt; margin-top:30px;" align="center">{text}</p>')

    def show_busy(self) -> None:
        self.setHtml(f'<p style="color:{C.STONE}; font-family:{C.SERIF_FONTS}; font-size:12pt; margin-top:30px;" align="center">Computing…</p>')

    def show_error(self, message: str) -> None:
        import html
        self._plain = "Error: " + message
        self.setHtml(f'<h3 style="font-family:{C.SERIF_FONTS}; color:{C.BRICK}; font-weight:normal;">Could not complete the calculation</h3>'
                     f'<table width="100%" cellpadding="8"><tr><td style="border-left:3px solid {C.BRICK}; background:#F1E3DD;">'
                     f'{html.escape(message)}</td></tr></table>'
                     f'<p style="color:{C.STONE};">Check the input syntax (e.g. <code>x^2 + 3*x - 4</code>, <code>sin(x)</code>, <code>sqrt(x)</code>) and try again.</p>')

    def show_report(self, report: Report) -> None:
        self._plain = report.to_text()
        html_text, images = build_html(report)
        doc: QTextDocument = self.document()
        doc.clear()
        for name, img in images.items():
            doc.addResource(QTextDocument.ImageResource, QUrl(name), img)
        self.setHtml(html_text)
        # setHtml may drop resources on some Qt builds: re-add and force relayout.
        for name, img in images.items():
            doc.addResource(QTextDocument.ImageResource, QUrl(name), img)
        doc.markContentsDirty(0, doc.characterCount())
        self.verticalScrollBar().setValue(0)

    def plain_text(self) -> str:
        return self._plain


# ---------------------------------------------------------------------------
def field_label(text: str) -> QLabel:
    lab = QLabel(text.upper()); lab.setObjectName("fieldLabel"); return lab


def hint_label(text: str) -> QLabel:
    lab = QLabel(text); lab.setObjectName("hint"); lab.setWordWrap(True); return lab


def hrule(name: str = "titleRule") -> QFrame:
    f = QFrame(); f.setObjectName(name); f.setFrameShape(QFrame.NoFrame); f.setFixedHeight(1); return f


class ModulePage(QWidget):
    """Common layout: title block, input panel on the left, result view on the right."""

    TITLE = ""
    SUBTITLE = ""
    INPUT_WIDTH = 400

    def __init__(self) -> None:
        super().__init__()
        self._token = 0
        self._pending = 0
        self._pool = QThreadPool.globalInstance()
        self._workers = {}
        outer = QVBoxLayout(self)
        outer.setContentsMargins(32, 24, 32, 20)
        outer.setSpacing(6)
        t = QLabel(self.TITLE); t.setObjectName("pageTitle")
        s = QLabel(self.SUBTITLE); s.setObjectName("pageSub")
        outer.addWidget(t); outer.addWidget(s); outer.addSpacing(8); outer.addWidget(hrule()); outer.addSpacing(10)

        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        self.input_panel = QFrame(); self.input_panel.setObjectName("panel")
        self.input_layout = QVBoxLayout(self.input_panel)
        self.input_layout.setContentsMargins(20, 18, 20, 18)
        self.input_layout.setSpacing(7)
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidget(self.input_panel)
        scroll.setMinimumWidth(330); scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.splitter.addWidget(scroll)
        self.results = self.build_results_area()
        self.splitter.setStretchFactor(0, 0); self.splitter.setStretchFactor(1, 1)
        self.splitter.setSizes([self.INPUT_WIDTH, 800])
        outer.addWidget(self.splitter, 1)
        self.build_inputs(self.input_layout)

    # -- to be overridden --------------------------------------------------
    def build_inputs(self, layout: QVBoxLayout) -> None:  # pragma: no cover
        raise NotImplementedError

    def build_results_area(self) -> QWidget:
        wrap = QWidget(); lay = QVBoxLayout(wrap); lay.setContentsMargins(0, 0, 0, 0); lay.setSpacing(6)
        self.result_view = ResultView()
        lay.addWidget(self.result_view, 1)
        bar = QHBoxLayout(); bar.addStretch(1)
        self.copy_btn = QPushButton("Copy result as text"); self.copy_btn.clicked.connect(self.copy_result)
        bar.addWidget(self.copy_btn); lay.addLayout(bar)
        self.splitter.addWidget(wrap)
        return wrap

    # -- helpers -----------------------------------------------------------
    def copy_result(self) -> None:
        QGuiApplication.clipboard().setText(self.result_view.plain_text())

    def run_task(self, fn: Callable[[], Report], on_done: Optional[Callable[[Report], None]] = None,
                 on_fail: Optional[Callable[[str], None]] = None, view: Optional[ResultView] = None) -> None:
        """Run ``fn`` in a worker thread; later results supersede earlier ones."""
        view = view or self.result_view
        self._token += 1
        token = self._token
        self._pending += 1
        view.show_busy()
        w = Worker(token, fn)
        self._workers[token] = w

        def ok(tok: int, rep: object) -> None:
            self._pending -= 1; self._workers.pop(tok, None)
            if tok != self._token:
                return
            if isinstance(rep, Report):
                view.show_report(rep)
            if on_done:
                on_done(rep)  # type: ignore[arg-type]

        def bad(tok: int, msg: str) -> None:
            self._pending -= 1; self._workers.pop(tok, None)
            if tok != self._token:
                return
            view.show_error(msg)
            if on_fail:
                on_fail(msg)

        w.signals.done.connect(ok, Qt.QueuedConnection)
        w.signals.failed.connect(bad, Qt.QueuedConnection)
        self._pool.start(w)

    def wait_idle(self, timeout_ms: int = 60000) -> bool:
        """Process events until all background work finished (used by tests)."""
        import time
        end = time.time() + timeout_ms / 1000
        while self._pending > 0 and time.time() < end:
            QCoreApplication.processEvents()
            time.sleep(0.01)
        QCoreApplication.processEvents()
        return self._pending == 0


def examples_combo(items: list[tuple[str, object]], on_pick: Callable[[object], None]) -> QComboBox:
    cb = QComboBox()
    cb.addItem("Load an example…", None)
    for label, payload in items:
        cb.addItem(label, payload)

    def picked(i: int) -> None:
        data = cb.itemData(i)
        if data is not None:
            on_pick(data)
        cb.setCurrentIndex(0)
    cb.activated.connect(picked)
    return cb
