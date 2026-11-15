# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for FINDX (one-folder build, windowed).

Build (from the project root, inside the virtual environment):
    pyinstaller packaging/FINDX.spec --noconfirm --clean
Result:  dist/FINDX/FINDX.exe
"""
import os
import sys

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))

hiddenimports = []
# SymPy imports many modules lazily; mpmath is its numerical backend.
hiddenimports += collect_submodules("sympy")
hiddenimports += collect_submodules("mpmath")
# SciPy sub-packages used by the engines (optimize/integrate pull in special + linalg + sparse).
for pkg in ("scipy.optimize", "scipy.integrate", "scipy.special", "scipy.linalg", "scipy.sparse", "scipy._lib"):
    hiddenimports += collect_submodules(pkg)
hiddenimports += [
    "matplotlib.backends.backend_qtagg",
    "matplotlib.backends.backend_agg",
    "matplotlib.backends.qt_compat",
    "matplotlib.mathtext",
    "PySide6.QtSvg",
]

datas = []
datas += collect_data_files("sympy")           # printing / test data referenced at import time
datas += collect_data_files("matplotlib")      # mpl-data: fonts (incl. Computer Modern for mathtext), styles
datas += [(os.path.join(ROOT, "assets", "icon.png"), "assets"),
          (os.path.join(ROOT, "assets", "icon.ico"), "assets")]

excludes = [
    "tkinter", "unittest.mock", "pytest", "IPython", "notebook", "jupyter",
    "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.QtWebEngineQuick",
    "PySide6.QtQuick", "PySide6.QtQml", "PySide6.Qt3DCore", "PySide6.QtMultimedia",
    "PySide6.QtCharts", "PySide6.QtDataVisualization", "PySide6.QtPdf", "PySide6.QtPdfWidgets",
    "matplotlib.backends.backend_tkagg", "matplotlib.backends.backend_wx",
]

a = Analysis(
    [os.path.join(ROOT, "main.py")],
    pathex=[ROOT],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
)
pyz = PYZ(a.pure)

icon_path = os.path.join(ROOT, "assets", "icon.ico") if sys.platform == "win32" else None

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,           # one-folder: more reliable than one-file for SciPy/Qt
    name="FINDX",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,                       # UPX corrupts some Qt/SciPy DLLs
    console=False,                   # windowed application
    icon=icon_path,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="FINDX",
)
