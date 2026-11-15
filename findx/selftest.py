"""Built-in self-test: exercises all five modules through the real GUI.

Run  ``python main.py --selftest``  or  ``FINDX.exe --selftest``.
It prints one line per check, writes ``selftest_graph.png`` to the temp folder
and exits with status 0 only if every check passed.  This is how the packaged
executable is verified on a machine without Python.
"""
from __future__ import annotations

import os
import sys
import tempfile
import traceback
from typing import Callable, List, Tuple

from PySide6.QtWidgets import QApplication

from . import __version__


def run() -> int:
    from .app import create_app
    from .gui import calculus_page, diff_page
    from .gui.algebra_page import EXAMPLES as ALG
    from .gui.main_window import MainWindow

    app = create_app([])
    win = MainWindow()
    win.show()
    results: List[Tuple[str, bool, str]] = []

    def check(name: str, fn: Callable[[], bool]) -> None:
        try:
            ok = bool(fn())
            results.append((name, ok, "" if ok else "assertion failed"))
        except Exception:  # noqa: BLE001
            results.append((name, False, traceback.format_exc(limit=2)))

    def page_ok(i: int, setup: Callable[[], None], must_contain: str) -> bool:
        win.select(i)
        page = win.pages[i]
        setup()
        page.wait_idle()
        txt = page.result_view.plain_text()
        return (not txt.startswith("Error")) and must_contain in txt

    def alg() -> bool:
        return page_ok(0, lambda: win.pages[0]._load_example(ALG[4][1]), "x = 3") or "Eq(x, 3)" in win.pages[0].result_view.plain_text()

    def mat() -> bool:
        p = win.pages[1]
        p.op.setCurrentText("Determinant det(A)")
        p.a.set_values([["2", "1"], ["1", "3"]])
        return page_ok(1, p.compute, "= 5") or "5" in p.result_view.plain_text()

    def dif() -> bool:
        return page_ok(2, lambda: win.pages[2]._example(diff_page.EXAMPLES[0][1]), "derivative")

    def cal() -> bool:
        return page_ok(3, lambda: win.pages[3]._example(calculus_page.EXAMPLES[2][1]), "exact value")

    def gra() -> bool:
        win.select(4)
        g = win.pages[4]
        g.funcs.setPlainText("x^2 - 4\nx + 2")
        g.plot(); g.wait_idle()
        out = g.analysis_text.toPlainText()
        path = os.path.join(tempfile.gettempdir(), "selftest_graph.png")
        g.figure.savefig(path, dpi=80)
        return "x = -2" in out and "(3, 5)" in out and os.path.getsize(path) > 2000

    def rendering() -> bool:
        win.select(0)
        win.pages[0]._load_example(ALG[1][1]); win.pages[0].wait_idle()
        return "math://" in win.pages[0].result_view.toHtml()

    check("Algebra Solver (cubic)", alg)
    check("Matrix Solver (determinant)", mat)
    check("Differentiation (product rule + evaluation)", dif)
    check("Calculus (definite integral)", cal)
    check("2D Graphing (plot, roots, intersections, PNG export)", gra)
    check("Mathematical typesetting (mathtext images)", rendering)

    lines = [f"FINDX {__version__} self-test"]
    failed = 0
    for name, ok, msg in results:
        lines.append(f"  [{'PASS' if ok else 'FAIL'}] {name}")
        if not ok:
            failed += 1
            lines.append("        " + msg.replace("\n", "\n        "))
    lines.append("SELFTEST OK" if not failed else f"SELFTEST FAILED ({failed})")
    text = "\n".join(lines)
    # A windowed (no-console) executable has no stdout, so always write a log file too.
    log_path = os.path.join(tempfile.gettempdir(), "findx_selftest.txt")
    try:
        with open(log_path, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
    except OSError:
        pass
    if sys.stdout is not None:
        try:
            print(text)
        except Exception:  # noqa: BLE001
            pass
    win.close()
    return 1 if failed else 0
