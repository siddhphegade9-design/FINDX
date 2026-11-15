"""Design system: one stylesheet + Matplotlib style shared by every module."""
from __future__ import annotations

import matplotlib as mpl

from .. import config as C


def stylesheet() -> str:
    return f"""
* {{ font-family: {C.SANS_FONTS}; font-size: 10pt; color: {C.CHARCOAL}; }}
QMainWindow, QWidget#root {{ background: {C.IVORY}; }}
QWidget {{ background: transparent; }}
QToolTip {{ background: {C.PAPER}; color: {C.CHARCOAL}; border: 1px solid {C.BORDER}; padding: 4px; }}

/* ---- sidebar ---- */
QFrame#sidebar {{ background: {C.CHARCOAL}; border: none; }}
QFrame#sidebar QLabel {{ color: {C.IVORY}; }}
QLabel#brand {{ font-family: {C.SERIF_FONTS}; font-size: 22pt; letter-spacing: 4px; color: {C.IVORY}; }}
QLabel#brandSub {{ color: {C.STONE}; font-size: 8pt; letter-spacing: 1px; }}
QLabel#sideFoot {{ color: {C.STONE}; font-size: 8pt; }}
QPushButton#nav {{ text-align: left; padding: 11px 18px 11px 20px; border: none; border-left: 3px solid transparent;
    color: #CFCBC0; background: transparent; font-size: 10.5pt; border-radius: 0; }}
QPushButton#nav:hover {{ background: #30322D; color: {C.IVORY}; }}
QPushButton#nav:checked {{ background: #34362F; color: {C.IVORY}; border-left: 3px solid {C.BRONZE}; }}
QFrame#sideRule {{ background: #3B3D37; max-height: 1px; min-height: 1px; border: none; }}

/* ---- page chrome ---- */
QLabel#pageTitle {{ font-family: {C.SERIF_FONTS}; font-size: 20pt; color: {C.CHARCOAL}; }}
QLabel#pageSub {{ color: {C.STONE}; font-size: 10pt; }}
QFrame#titleRule {{ background: {C.BORDER}; max-height: 1px; min-height: 1px; border: none; }}
QLabel#fieldLabel {{ color: {C.STONE}; font-size: 8.5pt; letter-spacing: 1px; }}
QLabel#hint {{ color: {C.STONE}; font-size: 8.5pt; }}
QFrame#panel {{ background: {C.PAPER}; border: 1px solid {C.BORDER}; }}
QLabel#panelTitle {{ font-family: {C.SERIF_FONTS}; font-size: 11.5pt; color: {C.CHARCOAL}; }}

/* ---- inputs ---- */
QLineEdit, QPlainTextEdit, QTextEdit, QDoubleSpinBox, QComboBox {{
    background: #FFFFFF; border: 1px solid {C.BORDER}; padding: 6px 8px; selection-background-color: {C.BRONZE};
    selection-color: {C.IVORY}; border-radius: 0; }}
QLineEdit, QPlainTextEdit {{ font-family: {C.MONO_FONTS}; font-size: 10.5pt; }}
QLineEdit:focus, QPlainTextEdit:focus, QDoubleSpinBox:focus, QComboBox:focus {{ border: 1px solid {C.BRONZE}; }}
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{ width: 0px; border: none; }}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox QAbstractItemView {{ background: #FFFFFF; border: 1px solid {C.BORDER}; selection-background-color: {C.BRONZE};
    selection-color: {C.IVORY}; outline: none; }}
QCheckBox {{ spacing: 8px; }}
QCheckBox::indicator {{ width: 14px; height: 14px; border: 1px solid {C.STONE}; background: #FFFFFF; }}
QCheckBox::indicator:checked {{ background: {C.BRONZE}; border: 1px solid {C.BRONZE_DARK}; }}

/* ---- buttons ---- */
QPushButton {{ border: 1px solid {C.STONE}; padding: 8px 18px; background: transparent; border-radius: 0; }}
QPushButton:hover {{ background: {C.IVORY_DARK}; }}
QPushButton:pressed {{ background: {C.BORDER}; }}
QPushButton:disabled {{ color: {C.STONE}; border-color: {C.BORDER}; }}
QPushButton#primary {{ background: {C.BRONZE}; color: {C.PAPER}; border: 1px solid {C.BRONZE_DARK}; font-weight: 600; }}
QPushButton#primary:hover {{ background: {C.BRONZE_DARK}; }}
QPushButton#primary:disabled {{ background: {C.BORDER}; color: {C.STONE}; border-color: {C.BORDER}; }}

/* ---- results ---- */
QTextBrowser {{ background: {C.PAPER}; border: 1px solid {C.BORDER}; padding: 14px; }}
QPlainTextEdit#analysis {{ background: {C.PAPER}; font-size: 9.5pt; }}

/* ---- tables (matrix input) ---- */
QTableWidget {{ background: #FFFFFF; border: 1px solid {C.BORDER}; gridline-color: {C.BORDER}; selection-background-color: #E6D8C9;
    selection-color: {C.CHARCOAL}; font-family: {C.MONO_FONTS}; }}
QTableWidget QLineEdit {{ padding: 0 4px; border: 1px solid {C.BRONZE}; }}
QHeaderView::section {{ background: {C.IVORY_DARK}; color: {C.STONE}; border: none; border-right: 1px solid {C.BORDER};
    border-bottom: 1px solid {C.BORDER}; padding: 3px; font-size: 8pt; }}

QSplitter::handle {{ background: {C.IVORY}; }}
QScrollBar:vertical {{ background: {C.IVORY}; width: 10px; margin: 0; }}
QScrollBar::handle:vertical {{ background: {C.BORDER}; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: {C.STONE}; }}
QScrollBar:horizontal {{ background: {C.IVORY}; height: 10px; margin: 0; }}
QScrollBar::handle:horizontal {{ background: {C.BORDER}; min-width: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QStatusBar {{ background: {C.IVORY_DARK}; color: {C.STONE}; border-top: 1px solid {C.BORDER}; }}
QStatusBar QLabel {{ color: {C.STONE}; }}
QToolBar {{ background: {C.IVORY}; border: none; spacing: 4px; }}
QToolBar QToolButton {{ background: transparent; border: 1px solid transparent; padding: 3px; }}
QToolBar QToolButton:hover {{ border: 1px solid {C.BORDER}; background: {C.IVORY_DARK}; }}
QToolBar QToolButton:checked {{ background: #E6D8C9; border: 1px solid {C.BRONZE}; }}
"""


def _pick_font() -> str:
    from matplotlib import font_manager
    names = {f.name for f in font_manager.fontManager.ttflist}
    for cand in ("Segoe UI", "Helvetica Neue", "Arial", "DejaVu Sans"):
        if cand in names:
            return cand
    return "sans-serif"


def apply_matplotlib_style() -> None:
    mpl.rcParams.update({
        "font.family": _pick_font(),
        "mathtext.fontset": "cm",
        "axes.facecolor": "#FFFFFF",
        "figure.facecolor": C.PAPER,
        "axes.edgecolor": C.STONE,
        "axes.labelcolor": C.STONE,
        "axes.linewidth": 0.8,
        "xtick.color": C.STONE,
        "ytick.color": C.STONE,
        "grid.color": "#D9D4C7",
        "grid.linewidth": 0.6,
        "text.color": C.CHARCOAL,
        "legend.frameon": True,
        "legend.facecolor": C.PAPER,
        "legend.edgecolor": C.BORDER,
        "legend.framealpha": 0.95,
        "axes.prop_cycle": mpl.cycler(color=C.CURVE_COLOURS),
    })
