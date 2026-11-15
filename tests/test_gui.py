"""GUI smoke / integration tests (run headless with QT_QPA_PLATFORM=offscreen)."""
import pytest

pytest.importorskip("PySide6")
from PySide6.QtWidgets import QApplication

from findx.app import create_app
from findx.core import matrix as M
from findx.gui import calculus_page, diff_page
from findx.gui.algebra_page import EXAMPLES as ALG_EX
from findx.gui.graph_page import EXAMPLES as GRAPH_EX
from findx.gui.main_window import MainWindow


@pytest.fixture(scope="module")
def win():
    app = create_app([])
    w = MainWindow()
    w.show()
    yield w
    w.close()


def text(page):
    return page.result_view.plain_text()


def test_sidebar_has_five_modules_in_order(win):
    names = [b.text().split("   ", 1)[1] for b in win.buttons.buttons()]
    assert names == ["Algebra Solver", "Matrix Solver", "Differentiation", "Calculus", "2D Graphing"]
    for i in range(5):
        win.select(i)
        assert win.stack.currentIndex() == i


@pytest.mark.parametrize("label,payload", ALG_EX)
def test_algebra_examples(win, label, payload):
    page = win.pages[0]
    page._load_example(payload)
    assert page.wait_idle()
    assert not text(page).startswith("Error"), (label, text(page))


def test_algebra_error_message(win):
    page = win.pages[0]
    page.mode.setCurrentText("Solve equation"); page.equation.setPlainText("x^2 +* 3 = 0"); page.solve()
    assert page.wait_idle()
    assert text(page).startswith("Error")


@pytest.mark.parametrize("op", list(M.OPERATIONS))
def test_every_matrix_operation(win, op):
    page = win.pages[1]
    page.op.setCurrentText(op)
    page.a.set_values([["2", "1", "0"], ["1", "3", "1"], ["0", "1", "4"]])
    if page._kind() == "system":
        page.a.set_values([["2", "1", "-1"], ["-3", "-1", "2"], ["-2", "1", "2"]])
        page.b.set_values([["8"], ["-11"], ["-3"]])
    elif page._kind() == "binary":
        page.b.set_values([["1", "0", "2"], ["0", "1", "1"], ["1", "1", "0"]])
    page.compute()
    assert page.wait_idle()
    assert not text(page).startswith("Error"), (op, text(page))
    assert "Matrix Solver" in text(page)


def test_matrix_dimension_mismatch_and_bad_entry(win):
    page = win.pages[1]
    page.op.setCurrentText("Addition (A + B)")
    page.a.set_dims(2, 2); page.b.set_dims(3, 3)
    page.compute(); assert page.wait_idle()
    assert "Cannot add" in text(page)
    page.b.set_dims(2, 2); page.a.table.item(0, 0).setText("abc")
    page.compute(); assert page.wait_idle()
    assert text(page).startswith("Error") and "Entry (1,1)" in text(page)
    page.a.table.item(0, 0).setText("0")


def test_system_b_follows_a_rows(win):
    page = win.pages[1]
    page.op.setCurrentText("Solve linear system Ax = b")
    page.a.set_dims(4, 4)
    assert page.b.rows_spin.value() == 4 and page.b.cols_spin.value() == 1
    page.a.set_dims(3, 3)


@pytest.mark.parametrize("label,payload", diff_page.EXAMPLES)
def test_diff_examples(win, label, payload):
    page = win.pages[2]
    page._example(payload); assert page.wait_idle()
    assert not text(page).startswith("Error"), (label, text(page))


@pytest.mark.parametrize("label,payload", calculus_page.EXAMPLES)
def test_calculus_examples(win, label, payload):
    page = win.pages[3]
    page._example(payload); assert page.wait_idle()
    assert not text(page).startswith("Error"), (label, text(page))


@pytest.mark.parametrize("label,funcs", GRAPH_EX)
def test_graph_examples(win, label, funcs):
    page = win.pages[4]
    page._example(funcs); assert page.wait_idle()
    assert len(page.ax.lines) >= len([l for l in funcs.splitlines() if l.strip()])
    assert page.analysis is not None
    assert "Analysing" not in page.analysis_text.toPlainText()


def test_graph_roots_markers_and_ranges(win):
    page = win.pages[4]
    page.funcs.setPlainText("x^2-4\nx+2"); page.auto_y.setChecked(False)
    page.ymin.setValue(-10); page.ymax.setValue(10); page.xmin.setValue(-5); page.xmax.setValue(5)
    page.plot(); assert page.wait_idle()
    assert page.ax.get_xlim() == pytest.approx((-5, 5)) and page.ax.get_ylim() == pytest.approx((-10, 10))
    out = page.analysis_text.toPlainText()
    assert "x = -2" in out and "x = 2" in out and "(3, 5)" in out
    page.auto_y.setChecked(True)


def test_graph_zoom_resamples_and_toggles(win):
    page = win.pages[4]
    page.funcs.setPlainText("sin(x)"); page.plot(); assert page.wait_idle()
    page.ax.set_xlim(0, 1); page._resample()
    xs = page.lines[0].get_xdata()
    assert xs[0] == pytest.approx(0) and xs[-1] == pytest.approx(1)
    page.detect_in_view(); assert page.wait_idle()
    assert "x = 0" in page.analysis_text.toPlainText()
    page.grid_cb.setChecked(False); page.legend_cb.setChecked(False); page.axes_cb.setChecked(False)
    page.grid_cb.setChecked(True); page.legend_cb.setChecked(True); page.axes_cb.setChecked(True)


def test_graph_invalid_input_reports_error(win):
    page = win.pages[4]
    page.funcs.setPlainText("x + y"); page.plot()
    assert "unknown symbol" in page.analysis_text.toPlainText()
    page.funcs.setPlainText("x"); page.xmin.setValue(5); page.xmax.setValue(1); page.plot()
    assert "x min must be smaller" in page.analysis_text.toPlainText()
    page.xmin.setValue(-6); page.xmax.setValue(6)


def test_math_rendering_produces_images(win):
    page = win.pages[0]
    page._load_example(ALG_EX[1][1]); assert page.wait_idle()
    doc = page.result_view.document()
    assert "math://1" in page.result_view.toHtml()


def test_copy_result(win):
    page = win.pages[0]
    page._load_example(ALG_EX[0][1]); assert page.wait_idle()
    page.copy_result()
    assert "Algebra Solver" in QApplication.clipboard().text()


def test_selftest_module_passes(capsys):
    from findx import selftest
    assert selftest.run() == 0
    assert "SELFTEST OK" in capsys.readouterr().out
