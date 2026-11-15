# FINDX — Technical Architecture

## 1. Layering

```
┌────────────────────────────── gui/ (PySide6) ───────────────────────────────┐
│ MainWindow ─ sidebar ─ QStackedWidget ─ {Algebra, Matrix, Diff, Calculus,    │
│                                          Graph}Page(ModulePage)               │
│ widgets.py: ModulePage, Worker(QRunnable), ResultView   render.py: Report→HTML│
└───────────────▲──────────────────────────────────────────────────────────────┘
                │ Report objects / plain Python values (no Qt types cross this line)
┌───────────────┴──────────────── core/ (pure Python) ─────────────────────────┐
│ parsing.py  →  algebra.py │ matrix.py │ differentiation.py │ calculus.py │ graphing.py │
│ report.py (Block/Report)   errors.py (FindxError ▸ InputError, ComputationError)       │
└───────────────▲──────────────────────────────────────────────────────────────┘
                │
        config.py (palette, fonts, tolerances)
```

Rules enforced by structure: `core/` never imports Qt or Matplotlib's Qt backend; the GUI never performs mathematics — pages only collect strings, call a `core` function inside a worker thread and display the returned `Report`.

## 2. Data flow of one calculation

1. Page reads raw strings from widgets (`compute()`).
2. `ModulePage.run_task(fn)` wraps `fn` in a `Worker` (QRunnable) on the global thread-pool; the view shows "Computing…".
3. The engine validates input (`parsing.py`), computes with SymPy/NumPy/SciPy and returns a `Report` (typed blocks: heading, text, math, exact, approx, matrix, note, warn).
4. `Worker` converts `FindxError` into a friendly message and any unexpected exception into "Unexpected error: …" (logged with traceback). The GUI therefore cannot crash from a calculation.
5. Signals are delivered with queued connections to the GUI thread; `ResultView.show_report` typesets maths via Matplotlib mathtext (images) and matrices as HTML tables.
6. A token counter drops stale results if the user starts a new calculation before the previous one finishes.

## 3. Modules

| File | Responsibility |
|------|----------------|
| `core/parsing.py` | character whitelist, forbidden-word/attribute checks, length limit, balanced parentheses, controlled SymPy namespace; parsers for expressions, equations, symbols, assignments, matrix entries (decimals → exact rationals) |
| `core/algebra.py` | polynomial solving narrative (coefficients, discriminant, Rational Root Theorem + exact polynomial division, factorisation, radical/numeric roots with multiplicities), non-polynomial solving with verification by substitution and numerical fallback, systems (Rouché–Capelli for linear, Gröbner for non-linear), factorisation |
| `core/matrix.py` | 12 operations with validation, derived explanations and self-verification (A·A⁻¹=I, A·v=λv, A·x=b) |
| `core/differentiation.py` | ordinary/higher/partial/mixed, implicit (−Fₓ/F_y, second derivative), gradient, rule walkthrough (top-level rule actually used), evaluation incl. undefined points |
| `core/calculus.py` | indefinite (+C, differentiation check), definite/improper (singularity warning, quadrature cross-check, symbolic value discarded if it disagrees), limits (left/right/two-sided, existence decision) |
| `core/graphing.py` | safe function compilation, sampling, discontinuity breaking, root finding (sign change + Brent, tangential minima), pairwise intersections, auto y-range, textual analysis |
| `gui/graph_page.py` | embedded `FigureCanvasQTAgg` + navigation toolbar, wheel zoom, debounced re-sampling on x-limit change, markers/annotations, analysis worker |
| `selftest.py` | drives every module through the real GUI; writes `%TEMP%/findx_selftest.txt` (used to verify the frozen executable) |

## 4. Design system

Palette in `config.py` (ivory `#F4F1EA`, charcoal `#252723`, stone `#77766D`, muted bronze `#A47754`, plus brick/olive/ochre for data). One QSS string in `gui/theme.py` styles all widgets (1 px borders, no gradients, no glow, square corners, bronze only as accent). Curves use bronze/charcoal/olive/brick/ochre/earth tones — no blue, purple or cyan anywhere.

## 5. Packaging

`packaging/FINDX.spec` — one-folder, windowed, UPX off. Hidden imports collected for SymPy, mpmath, SciPy optimize/integrate/special/linalg/sparse; Matplotlib Qt backend; data files for SymPy and Matplotlib (fonts incl. Computer Modern). `packaging/build_windows.bat` automates venv → tests → build → `--selftest` of the built exe.
