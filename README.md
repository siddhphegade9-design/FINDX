# FINDX — Advanced Mathematical Computing Application

A desktop application (Python + PySide6) with five mathematical workspaces:

| # | Module | What it does |
|---|--------|--------------|
| 1 | **Algebra Solver** | Linear, quadratic, cubic and higher-degree equations; systems (linear and polynomial); factorisation; symbolic parameters; numerical fallback; repeated and complex roots; exact vs approximate answers |
| 2 | **Matrix Solver** | A+B, A−B, A×B, k·A, Aᵀ, det, inverse, rank, trace, eigenvalues, eigenvectors, Ax=b — exact rational arithmetic, up to 10×10 |
| 3 | **Differentiation** | Derivatives of any order, partial and mixed partial derivatives, implicit differentiation (1st/2nd), gradient, evaluation at a point |
| 4 | **Calculus** | Indefinite (+C) and definite integrals (incl. improper), limits with left/right-hand limits, numerical cross-check |
| 5 | **2D Graphing** | Multiple functions, pan/zoom, grid/axes/legend, root and intersection detection with coordinates, discontinuity handling, PNG export |

Results are typeset with Computer-Modern mathematics and every result is labelled **EXACT** or **APPROX.**

## Run from source

Requires Python 3.10 – 3.13 (64-bit).

```bat
cd FINDX
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Tested with: Python 3.13, PySide6 6.12, SymPy 1.14, NumPy 2.5, SciPy 1.18, Matplotlib 3.11, pytest 9.1.

## Input syntax

* Powers: `x^2` (or `x**2`); implicit multiplication works: `2x`, `3(x+1)`, `x y`.
* Functions: `sin cos tan cot sec csc asin acos atan sinh cosh tanh exp ln log sqrt abs` — constants `pi`, `e`, `I` (imaginary unit), `oo` (infinity).
* Equations: `x^2 - 4 = 0`; a bare expression means "= 0". Systems: one equation per line.
* Multi-letter names are read as products (`ab` = a·b). Use single-letter variables.
* Matrix entries: integers, decimals (`0.5` → exactly 1/2), fractions (`1/3`), or constants such as `sqrt(2)`.

## Tests

```bat
pip install -r requirements-dev.txt
python -m pytest
```

147 automated tests (parsing, all five engines, and headless GUI integration tests). On Linux/CI set `QT_QPA_PLATFORM=offscreen`.
A built-in end-to-end check is also available — it drives every module through the real GUI:

```bat
python main.py --selftest
```

## Build the Windows executable

On a Windows 10/11 machine with Python on PATH, double-click or run:

```bat
packaging\build_windows.bat
```

This creates a clean virtual environment, installs dependencies, runs the tests, builds a **one-folder** distribution with PyInstaller
(`packaging\FINDX.spec`) and finally runs `FINDX.exe --selftest` from the `dist` folder as an independent check.
Result: `dist\FINDX\FINDX.exe` (ship the whole `FINDX` folder; no Python needed on the target PC).

Manual equivalent:

```bat
pip install -r requirements-dev.txt
pyinstaller packaging\FINDX.spec --noconfirm --clean
dist\FINDX\FINDX.exe --selftest
type %TEMP%\findx_selftest.txt
```

A one-folder build is used deliberately: one-file builds unpack ~400 MB of SciPy/Qt libraries on every start-up and are less reliable.

## Download a ready-made FINDX.exe from GitHub

Every push to `main` is tested and built on a Windows runner by `.github/workflows/build.yml`.
Open the repository's **Actions** tab, pick the latest run and download the **FINDX-windows** artifact (a zip containing the `FINDX` folder).
Pushing a tag such as `v1.0.0` also publishes the zip under **Releases**.

## Project layout

```
main.py                    entry point
findx/
  config.py                palette, fonts, numerical tolerances
  app.py, selftest.py      bootstrap and built-in end-to-end check
  core/                    pure mathematics (no GUI imports)
    parsing.py             safe parser + input validation
    algebra.py  matrix.py  differentiation.py  calculus.py  graphing.py
    report.py              structured result container
  gui/                     PySide6 presentation layer
    theme.py render.py widgets.py main_window.py
    algebra_page.py matrix_page.py diff_page.py calculus_page.py graph_page.py
tests/                     pytest suite
packaging/                 PyInstaller spec + Windows build script
docs/                      ARCHITECTURE.md, PROJECT_REPORT.pdf, screenshots, test logs
tools/make_report.py       regenerates PROJECT_REPORT.pdf
```

See `docs/ARCHITECTURE.md` and `docs/PROJECT_REPORT.pdf` for design details, algorithms, test results and limitations.
