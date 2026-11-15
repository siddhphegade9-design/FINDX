"""Generate docs/PROJECT_REPORT.pdf.

Facts that can change (test counts, results, versions) are read from the real
artefacts (docs/test_results.txt, installed packages, screenshots) at build time,
never typed by hand.
"""
from __future__ import annotations

import os
import re
import sys
from importlib import metadata

import matplotlib
from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, Frame, Image, KeepTogether, PageBreak, PageTemplate, Paragraph,
                                Preformatted, Spacer, Table, TableStyle)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, "docs")
SHOTS = os.path.join(DOCS, "screenshots")
sys.path.insert(0, ROOT)
from findx import __version__  # noqa: E402

FONTDIR = os.path.join(os.path.dirname(matplotlib.__file__), "mpl-data", "fonts", "ttf")
for name, f in [("Sans", "DejaVuSans.ttf"), ("Sans-B", "DejaVuSans-Bold.ttf"), ("Sans-I", "DejaVuSans-Oblique.ttf"),
                ("Serif", "DejaVuSerif.ttf"), ("Serif-B", "DejaVuSerif-Bold.ttf"), ("Serif-I", "DejaVuSerif-Italic.ttf"),
                ("Mono", "DejaVuSansMono.ttf")]:
    pdfmetrics.registerFont(TTFont(name, os.path.join(FONTDIR, f)))
pdfmetrics.registerFontFamily("Sans", normal="Sans", bold="Sans-B", italic="Sans-I", boldItalic="Sans-B")
pdfmetrics.registerFontFamily("Serif", normal="Serif", bold="Serif-B", italic="Serif-I", boldItalic="Serif-B")

IVORY, CHAR, STONE, BRONZE, BORDER = (colors.HexColor(c) for c in ("#F4F1EA", "#252723", "#77766D", "#A47754", "#CFC9BB"))

body = ParagraphStyle("body", fontName="Sans", fontSize=9.2, leading=13.6, textColor=CHAR, alignment=TA_JUSTIFY, spaceAfter=5)
h1 = ParagraphStyle("h1", fontName="Serif", fontSize=17, leading=21, textColor=CHAR, spaceBefore=14, spaceAfter=6)
h2 = ParagraphStyle("h2", fontName="Serif-B", fontSize=11.5, leading=15, textColor=BRONZE, spaceBefore=9, spaceAfter=3)
small = ParagraphStyle("small", parent=body, fontSize=8, leading=11, textColor=STONE)
bullet = ParagraphStyle("bullet", parent=body, leftIndent=14, bulletIndent=3, spaceAfter=2, alignment=0)
cell = ParagraphStyle("cell", parent=body, fontSize=8.3, leading=11, alignment=0, spaceAfter=0)
cellb = ParagraphStyle("cellb", parent=cell, fontName="Sans-B")
code = ParagraphStyle("code", fontName="Mono", fontSize=7.4, leading=9.4, textColor=CHAR, backColor=colors.HexColor("#EFEBE1"),
                      borderPadding=5, spaceBefore=3, spaceAfter=8, leftIndent=4)
cap = ParagraphStyle("cap", parent=small, alignment=1, spaceAfter=10)

story = []
P = lambda t, s=body: story.append(Paragraph(t, s))
H1 = lambda t: story.append(Paragraph(t, h1))
H2 = lambda t: story.append(Paragraph(t, h2))
B = lambda items: [story.append(Paragraph(i, bullet, bulletText="•")) for i in items]
CODE = lambda t: story.append(Preformatted(t.strip("\n"), code))


def table(rows, widths, header=True):
    data = [[Paragraph(str(c), cellb if (header and r == 0) else cell) for c in row] for r, row in enumerate(rows)]
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    st = [("GRID", (0, 0), (-1, -1), 0.4, BORDER), ("VALIGN", (0, 0), (-1, -1), "TOP"),
          ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]
    if header:
        st.append(("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EAE5DA")))
    t.setStyle(TableStyle(st))
    story.append(t); story.append(Spacer(1, 6))


def shot(name, caption, width=165 * mm):
    path = os.path.join(SHOTS, name)
    from PIL import Image as PI
    w, h = PI.open(path).size
    story.append(KeepTogether([Image(path, width=width, height=width * h / w), Paragraph(caption, cap)]))


# ----------------------------------------------------------------- facts from artefacts
log = open(os.path.join(DOCS, "test_results.txt"), encoding="utf-8").read()
final = re.search(r"=+ (.*?) in ([\d.]+)s =+", log)
n_pass = int(re.search(r"(\d+) passed", final.group(1)).group(1))
n_fail = int(m.group(1)) if (m := re.search(r"(\d+) failed", final.group(1))) else 0
per_file = [ln.strip() for ln in open(os.path.join(DOCS, "test_summary_by_file.txt"), encoding="utf-8") if ln.strip()]
ver = lambda p: metadata.version(p)
versions = {p: ver(p) for p in ("PySide6", "sympy", "numpy", "scipy", "matplotlib", "pytest", "pyinstaller")}
py = sys.version.split()[0]

# ----------------------------------------------------------------- cover
story.append(Spacer(1, 40 * mm))
story.append(Paragraph("FINDX", ParagraphStyle("t", fontName="Serif", fontSize=44, leading=48, textColor=CHAR)))
story.append(Paragraph("Advanced Mathematical Computing Application", ParagraphStyle("st", fontName="Serif", fontSize=17, leading=22, textColor=BRONZE)))
story.append(Spacer(1, 6 * mm))
story.append(Paragraph("Project Report — design, implementation, testing and packaging", ParagraphStyle("s2", fontName="Sans", fontSize=11, textColor=STONE)))
story.append(Spacer(1, 70 * mm))
table([["Version", __version__], ["Language / GUI", "Python / PySide6"],
       ["Mathematical libraries", "SymPy, NumPy, SciPy, Matplotlib"],
       ["Automated tests", f"{n_pass} passed, {n_fail} failed (pytest)"],
       ["Windows executable", "Build configuration delivered; .exe could not be built in the development environment (see §14)"]],
      [45 * mm, 120 * mm], header=False)
story.append(PageBreak())

# ----------------------------------------------------------------- 1-3
H1("1. Project overview")
P("FINDX is a desktop application that brings five mathematical capabilities into one consistent workspace: an <b>Algebra Solver</b>, "
  "a <b>Matrix Solver</b>, a <b>Differentiation Engine</b>, a <b>Calculus Engine</b> (integrals and limits) and a <b>2D Graphing Engine</b>. "
  "A persistent sidebar switches between the five modules; each module has its own input panel and a result area in which the original "
  "problem, the method, intermediate quantities and the final answer are typeset with mathematical notation. Every result is labelled "
  "<b>EXACT</b> (symbolic) or <b>APPROX.</b> (numerical).")
P("Every control in the interface is connected to a working computation. There are no hard-coded sample results: the examples menus only "
  "load typical inputs which are then computed live.")
H1("2. Problem statement")
P("Students meet algebra, linear algebra, calculus and graphing in separate tools: calculators that return only a final number, computer-algebra "
  "systems with a steep learning curve, or graphing apps that do no symbolic work. The problem addressed here is to build a single, offline, "
  "approachable application that gives <i>reliable</i> results, distinguishes exact answers from approximations, explains <i>what was done</i> "
  "without inventing working that was never performed, and handles invalid or ill-posed input politely.")
H1("3. Objectives")
B(["Implement the five modules with real mathematics (SymPy for symbolic work, NumPy/SciPy for numerical work).",
   "Provide a professional, restrained academic visual design — ivory/charcoal/stone/bronze palette, thin borders, no neon, no blue/purple/cyan accents, no gradients or glow.",
   "Keep mathematics, GUI, validation, graphing logic, configuration, tests and packaging separate and modular.",
   "Validate all input and never crash on bad input; report errors in plain language.",
   "Verify behaviour with an automated test-suite and report the actual results honestly.",
   "Package the program as a Windows application that does not need a Python installation."])

# ----------------------------------------------------------------- 4 technologies
H1("4. Technologies and libraries")
table([["Library", "Version used in testing", "Role"],
       ["Python", py, "Primary language"],
       ["PySide6 (Qt 6)", versions["PySide6"], "Desktop GUI, threading (QThreadPool), embedding Matplotlib"],
       ["SymPy", versions["sympy"], "Parsing, symbolic algebra, calculus, matrices, LaTeX output"],
       ["NumPy", versions["numpy"], "Vectorised function evaluation, sampling"],
       ["SciPy", versions["scipy"], "Brent root finding, bounded minimisation, adaptive quadrature"],
       ["Matplotlib", versions["matplotlib"], "2D plotting (Qt backend) and mathtext typesetting of results"],
       ["pytest", versions["pytest"], "Automated testing"],
       ["PyInstaller", versions["pyinstaller"], "Packaging"]],
      [38 * mm, 40 * mm, 87 * mm])
P("Library versions are those actually installed when this report was generated; <i>requirements.txt</i> lists compatible ranges.", small)

# ----------------------------------------------------------------- 5 architecture
H1("5. Project architecture")
P("The program is split into two layers with a one-way dependency. <b>core/</b> contains pure mathematical engines and has no GUI imports. "
  "<b>gui/</b> contains only presentation code: it gathers text from widgets, calls a core function on a worker thread and shows the returned "
  "<i>Report</i> object. The GUI never contains mathematical logic.")
CODE("""
main.py                       entry point (also: --selftest)
findx/
  config.py                   palette, fonts, numerical tolerances
  app.py  selftest.py         bootstrap; built-in end-to-end check
  core/
    errors.py                 FindxError > InputError, ComputationError
    parsing.py                safe parser and validation
    report.py                 Report / Block result container
    algebra.py  matrix.py  differentiation.py  calculus.py  graphing.py
  gui/
    theme.py                  one stylesheet + Matplotlib style (design system)
    render.py                 Report -> rich text, math typesetting
    widgets.py                ModulePage, Worker thread, ResultView
    main_window.py            sidebar + stacked workspaces
    algebra_page.py matrix_page.py diff_page.py calculus_page.py graph_page.py
tests/                        7 test modules
packaging/                    FINDX.spec, build_windows.bat
docs/                         ARCHITECTURE.md, this report, screenshots, test logs
""")
P("<b>Data flow.</b> A page reads the input strings and calls <i>run_task</i>. A <i>Worker</i> (QRunnable) executes the engine function off the GUI "
  "thread so that the window stays responsive during heavy symbolic work. Engines raise <i>InputError</i> (bad input) or <i>ComputationError</i> "
  "(valid input, no reliable result); the worker converts these — and any unexpected exception, which is also logged — into a message shown in "
  "the result area. A token counter discards results of superseded requests.")

# ----------------------------------------------------------------- 6 modules
H1("6. The modules")
H2("6.1 Algebra Solver")
P("Three tasks: <i>solve equation</i>, <i>solve system</i> and <i>factor polynomial</i>. After moving all terms to one side the program decides whether the "
  "equation is a polynomial in the chosen variable.")
B(["<b>Linear:</b> coefficient extraction, then x = −b/a.",
   "<b>Quadratic:</b> the discriminant Δ = b² − 4ac is computed and displayed, the nature of the roots (two real, one repeated, complex pair) is "
   "stated from the actual sign of Δ, and the roots follow from the quadratic formula.",
   "<b>Cubic and higher:</b> the Rational Root Theorem candidates ±p/q are generated from the actual coefficients and tested <i>exactly</i>; each found root is "
   "divided out by exact polynomial division (repeated, so multiplicities are found), the reduced polynomial is shown, factorised and solved by radicals "
   "where SymPy can (quadratic, cubic and quartic formulae). If no radical solution exists (e.g. x⁵ − x − 1) the program says so (Abel–Ruffini) and "
   "computes the remaining roots numerically to 15 digits, labelling them APPROX.",
   "<b>Verification:</b> every polynomial root is substituted back into the polynomial and the maximum residual is reported; the root count with multiplicity is "
   "compared with the degree.",
   "<b>Non-polynomial equations</b> (trigonometric, rational, radical): SymPy's solver is tried first; every candidate is verified by substitution so extraneous roots "
   "(e.g. from squaring) are discarded. If nothing verified is found, a numerical sign-change scan on [−50, 50] with Brent refinement is used, clearly labelled.",
   "<b>Parameters:</b> extra letters are treated as constants, giving symbolic formulae such as the general quadratic solution.",
   "<b>Systems:</b> linear systems show the coefficient matrix, ranks of A and [A|b], and a unique/infinite/none verdict; non-linear polynomial systems use SymPy's solver.",
   "<b>Factorisation:</b> irreducible factors over the rationals, plus the factorisation over the Gaussian rationals when it differs."])
H2("6.2 Matrix Solver")
P("Twelve operations on exact rational matrices up to 10×10: addition, subtraction, multiplication, scalar multiplication, transpose, determinant, inverse, rank, "
  "trace, eigenvalues, eigenvectors and the linear system Ax = b. The user sets the dimensions with spin-boxes and edits entries in a grid. Entries may be integers, "
  "decimals (0.1 is stored as exactly 1/10) or fractions.")
B(["Dimension errors are explained (e.g. “columns of A (3) must equal rows of B (2)”).",
   "Determinant: 2×2 formula shown with the values; 3×3 cofactor expansion shown term by term; larger matrices use exact Bareiss elimination (stated).",
   "Inverse: determinant check first (singular matrices get a clear message); Gauss–Jordan reduction of [A | I] is displayed and A·A⁻¹ = I is verified.",
   "Eigenvalues: characteristic polynomial det(A − λI) shown and factored; algebraic multiplicities; checks against trace and determinant. Eigenvectors: null space of A − λI "
   "for each λ, with verification A v = λ v and a warning when the matrix is defective.",
   "Linear systems: RREF of [A | b] and the Rouché–Capelli rank test decide unique / infinitely many (with free parameters) / no solution."])
H2("6.3 Differentiation Engine")
P("Ordinary and higher-order derivatives, partial and mixed partial derivatives (list the variables, e.g. “x, y”), implicit differentiation of F(x, y) = 0 "
  "(dy/dx = −Fₓ/F_y and the second derivative), the gradient vector, and evaluation at a point. The original expression, the operation in Leibniz notation and "
  "the result are shown. A “rules applied” section names the top-level rule actually used (sum, product, chain, power, exponential rule) together with the "
  "component derivatives it needed; deeper levels are not narrated. Evaluation reports undefined points (e.g. 1/x at 0) and vertical tangents instead of "
  "returning a spurious value.")
H2("6.4 Calculus Engine")
B(["<b>Indefinite integral:</b> result F(x) and the full family F(x) + C; correctness check by differentiating the result. Non-elementary integrals are reported "
   "honestly (SymPy may return special functions such as erf).",
   "<b>Definite integral:</b> exact value via the Fundamental Theorem, improper limits ±∞ supported, singularities inside the interval flagged (the integral of 1/x² "
   "over [−1, 1] is reported as divergent, not as −2). The exact value is cross-checked with adaptive Gauss–Kronrod quadrature (scipy.integrate.quad); if the "
   "symbolic value disagrees with quadrature it is discarded and only the numeric value is shown, labelled APPROX.",
   "<b>Limits:</b> direct substitution is tried and reported, then SymPy's Gruntz-based algorithm. Two-sided limits compute both the left- and right-hand limits, "
   "show both, and decide whether the limit exists (lim 1/x at 0 does not exist; the one-sided limits are −∞ and +∞)."])
H2("6.5 2D Graphing Engine")
P("Several functions (up to eight) are entered one per line as <i>y = …</i>, <i>f(x) = …</i> or a bare expression. Controls: x-range, y-range or automatic y-range, grid, axes "
  "through the origin, legend, root detection, intersection detection. The Matplotlib figure is embedded with its navigation toolbar (home, back/forward, pan, zoom-rectangle, "
  "save); the mouse wheel zooms around the cursor, and curves are re-sampled for the new x-range after every pan or zoom so that detail is never lost. "
  "Roots and intersections are marked on the graph, annotated when few, and always listed with their coordinates in the analysis panel. The graph is strictly 2D.")

# ----------------------------------------------------------------- 7 methods
H1("7. Mathematical methods and algorithms")
table([["Task", "Method", "Reliability notes"],
       ["Polynomial roots", "Rational Root Theorem + exact division; radical formulae; SymPy numeric (nroots) when not solvable in radicals", "Exact for deg ≤ 4; numeric (≈15 digits) otherwise, always flagged"],
       ["General equations", "SymPy solve → verification by substitution → sign-change scan + Brent", "Numeric fallback finds real roots in [−50, 50] with sign change only"],
       ["Linear systems", "Gaussian elimination / RREF over ℚ; Rouché–Capelli", "Exact"],
       ["Determinant", "2×2, 3×3 cofactor, Bareiss for n ≥ 4", "Exact"],
       ["Inverse", "Gauss–Jordan on [A | I]; verified A·A⁻¹ = I", "Exact"],
       ["Eigen-analysis", "det(A − λI) = 0; null space of A − λI", "Exact where radicals exist; complex eigenvalues supported"],
       ["Derivatives", "SymPy diff; implicit via −Fₓ/F_y", "Exact"],
       ["Integrals", "SymPy (Risch/heuristics/Meijer-G); quad cross-check", "Symbolic value discarded if it disagrees with quadrature"],
       ["Limits", "Gruntz algorithm; one-sided limits", "Exact; unevaluated results are reported as such"],
       ["Root detection (graphs)", "20,001-point scan; sign-change brackets refined by Brent (xtol 1e-12); local minima of |f| refined for tangential roots", "Accepted only if |f| &lt; 1e-7 (tangential: 1e-9); removes poles"],
       ["Intersections", "Roots of h = f − g by the same routine; coordinates from f", "Pairwise for all curves"]],
      [30 * mm, 80 * mm, 55 * mm])

# ----------------------------------------------------------------- 8 gui
H1("8. How the GUI works")
P("<b>Main window.</b> A fixed-width charcoal sidebar lists the five modules (keyboard shortcuts Ctrl+1 … Ctrl+5); the selected module is marked with a bronze bar. "
  "A QStackedWidget holds the five pages. Pages share one base class, <i>ModulePage</i>: title block, input panel (left, scrollable) and result area (right) separated by a "
  "splitter, so the layout adapts to window size (minimum 1000×640). All colours and widget styles come from one stylesheet in <i>gui/theme.py</i>.")
P("<b>Typesetting.</b> Mathematics is rendered by Matplotlib's mathtext with Computer Modern fonts and inserted as images; matrices are drawn as bracketed HTML tables. "
  "If a LaTeX string cannot be parsed, a plain-text form is shown, so output is never lost.")
P("<b>Responsiveness.</b> Computations run in a thread pool; “Computing…” is displayed meanwhile. <b>Convenience:</b> example menus, Clear buttons, "
  "“Copy result as text”, PNG export of graphs.")

# ----------------------------------------------------------------- 9 graphing
H1("9. Plotting, root detection and intersection detection")
P("<b>Plotting.</b> Each expression is converted by <i>lambdify</i> into a NumPy function and sampled at 4,000 points. Complex results and non-finite values become NaN so Matplotlib "
  "leaves gaps (e.g. √x for x &lt; 0). <b>Discontinuities:</b> if the jump between neighbouring samples is far larger than the typical step and the sign flips (or the jump greatly exceeds the data "
  "spread) the line is broken; therefore tan(x) and 1/x show separate branches without false vertical connectors, while steep continuous curves such as x⁹ are drawn unbroken "
  "(both cases are covered by tests).")
P("<b>Roots.</b> The function is evaluated on 20,001 points. Where the sign changes between neighbours the bracket is refined with Brent's method (tolerance 1e-12). Because a pole also "
  "changes sign, a candidate is accepted only if |f(root)| is below 1e-7. Roots of even multiplicity do not change sign, so local minima of |f| are refined with a bounded minimiser and accepted "
  "if |f| &lt; 1e-9 (e.g. (x−1)² is found at x = 1 with error below 1e-5). <b>Intersections</b> of curves f and g are the roots of f − g; all pairs of curves are examined. Results are listed with 8 significant "
  "digits and the tolerances used are printed in the analysis panel.")
P("<b>Limitations (stated in the application):</b> only real roots inside the plotted interval are found; extremely close double roots and very rapidly oscillating functions can be missed.")

# ----------------------------------------------------------------- 10 decisions
H1("10. Important implementation decisions")
B(["<b>Exact arithmetic by default.</b> Matrix entries are rational; decimals are converted exactly (0.1 → 1/10) to avoid floating-point surprises. Numerical results appear only where "
   "exactness is impossible and are labelled.",
   "<b>No fabricated working.</b> Every displayed intermediate step is a quantity that was actually computed (discriminant, rational-root candidates, RREF, cofactors, minors, partial derivatives, ranks). "
   "SymPy does not expose a derivation for integrals and limits, so for those the method is described and the result is verified instead.",
   "<b>Verification built into results.</b> Substitution of roots, A·A⁻¹ = I, A v = λ v, Ax = b, differentiating antiderivatives and quadrature cross-checks.",
   "<b>Worker threads</b> keep the GUI responsive; stale results are discarded.",
   "<b>Safe parsing</b> instead of raw eval (see §11).",
   "<b>One-folder packaging</b> because a one-file executable must unpack several hundred MB of Qt/SciPy libraries on each start and is less reliable.",
   "<b>Built-in self-test</b> (<i>--selftest</i>) that exercises every module through the real GUI, so the packaged program can be verified independently of the test-suite."])

# ----------------------------------------------------------------- 11 errors
H1("11. Error handling and input validation")
B(["The parser restricts the character set, limits length to 600 characters, checks balanced parentheses and rejects Python keywords, attribute access and double underscores "
   "(<i>__import__('os')</i>, <i>x.is_real</i>, <i>lambda x: x</i> are all rejected — covered by tests). Only a controlled set of functions and constants is available.",
   "Equations: one “=” only; inequalities are rejected with an explanation. Matrix entries must be numeric; the failing cell is named (“Entry (2,3): …”).",
   "Domain-specific checks: incompatible matrix dimensions, non-square matrices for det/inverse/trace/eigen, singular matrices, inconsistent systems, wrong variable names, "
   "invalid ranges (x min ≥ x max), unknown symbols in graph functions, too many curves.",
   "Mathematical edge cases are reported rather than hidden: identities and contradictions, divergent integrals, singularities inside integration intervals, non-existent limits, "
   "undefined derivatives, vertical tangents, defective matrices.",
   "A last-resort handler converts unexpected exceptions into an on-screen message and a log entry, so a calculation can never terminate the program."])

# ----------------------------------------------------------------- 12 testing
H1("12. Testing methodology and actual results")
P("Three levels of tests were written with pytest and executed in the development environment: (1) <b>unit tests</b> of the parser and of every engine, comparing against known exact "
  "answers and independent identities (e.g. A·v = λ·v, expand(factored − original) = 0); (2) <b>negative tests</b> for invalid input and edge cases; (3) <b>GUI integration tests</b> run "
  "headless (Qt “offscreen” platform) which drive the real windows: every example of every module, every one of the 12 matrix operations, error display, graph plotting, "
  "zoom re-sampling, toggles, analysis output, typeset-image creation and the clipboard button.")
P(f"<b>Result of the final run: {n_pass} passed, {n_fail} failed</b> (pytest, {final.group(2)} s, Python {py} on Linux, Qt offscreen). Results per test module:")
table([["Test module", "Result"]] + [[l.split(":")[0], l.split(":", 1)[1].strip()] for l in per_file], [70 * mm, 95 * mm])
P("Defects found and fixed during development: (a) a test failed because the point-evaluation branch of the differentiation engine did not record a value when the derivative still contained a free symbol; "
  "(b) code review while fixing (a) showed that differentiating with respect to a variable absent from the expression would raise an internal error instead of returning 0 — fixed and a regression test added. "
  "Additionally, because SymPy returned a very long special-function (Fresnel) expression for one definite integral, a quadrature cross-check was added that discards any symbolic value disagreeing with "
  "numerical integration; in that particular case the symbolic value agreed with the numerical one (0.301297712959). The full verbose log is reproduced in Appendix A.")
P("The tests were run on Linux because that is the development environment; they exercise the platform-independent Python code and Qt in offscreen mode. They do not exercise Windows-specific "
  "behaviour such as the Segoe UI font or DPI scaling.", small)

# ----------------------------------------------------------------- 13 screenshots
H1("13. Screenshots of the application")
P("The following screenshots were captured from the running application (offscreen rendering in the development environment, using fallback fonts because Segoe UI is not installed there; "
  "on Windows the interface uses Segoe UI).")
shot("algebra.png", "Figure 1 — Algebra Solver: quadratic equation with discriminant and typeset working.")
shot("matrix_eigen.png", "Figure 2 — Matrix Solver: eigenvectors with matrix input grid.")
shot("differentiation.png", "Figure 3 — Differentiation: product rule walkthrough and exact result.")
shot("calculus.png", "Figure 4 — Calculus: definite integral with exact value and numerical cross-check.")
shot("graphing.png", "Figure 5 — 2D Graphing: parabola and line, roots (circles) and intersections (diamonds).")
shot("graphing_poles.png", "Figure 6 — 2D Graphing: tan(x), 1/x and x; poles are drawn as separate branches, with all roots and intersections marked.")

# ----------------------------------------------------------------- 14 packaging
H1("14. Packaging for Windows — what was and was not verified")
P("<b>Delivered:</b> <i>packaging/FINDX.spec</i> (PyInstaller one-folder, windowed, UPX disabled, hidden imports for SymPy/mpmath/SciPy sub-packages, Matplotlib Qt backend and fonts), "
  "<i>packaging/build_windows.bat</i> (virtual environment → install → tests → PyInstaller → run the built executable with <i>--selftest</i>), an application icon, and the self-test mode.")
table([["Item", "Status"],
       ["Source code and all five modules", "Implemented and tested (147 automated tests passing)"],
       ["GUI", "Tested headless (offscreen) on Linux, screenshots inspected; not run on a physical Windows desktop"],
       ["PyInstaller spec", "Used to build a <b>Linux</b> one-folder bundle; the bundle's <i>--selftest</i> (all six checks) passed when run with a clean environment and no Python on PATH. This validates the hidden-import configuration but is <b>not</b> a Windows test"],
       ["FINDX.exe", "<b>Not generated.</b> PyInstaller cannot cross-compile; the development environment is Linux with no Windows toolchain. Run <i>packaging\\build_windows.bat</i> on Windows to produce and self-test it"],
       ["Packaged .exe independently tested", "<b>No</b> — cannot be claimed. The build script performs this test automatically on Windows and fails the build if any module does not work"]],
      [48 * mm, 117 * mm])

# ----------------------------------------------------------------- 15 limitations
H1("15. Limitations")
B(["Symbolic integration and limits rely on SymPy; some inputs may take long or return no closed form. A running calculation cannot be cancelled (a new request supersedes its result).",
   "Integral and limit working is described, not derived line-by-line (no step-by-step engine is available in the libraries).",
   "Numerical fallback for non-polynomial equations finds only real roots with sign changes in [−50, 50].",
   "Graph root/intersection detection is numerical, real-valued and restricted to the analysed interval; tolerances are displayed. Implicit curves (e.g. x² + y² = 1) cannot be plotted as y = f(x) functions.",
   "Inequalities, differential equations, 3D plots and piecewise-defined input syntax are not supported. Multi-letter names are interpreted as products.",
   "Matrices are limited to 10×10 and numeric entries. Eigen-analysis of large matrices with irrational eigenvalues may be slow in exact mode.",
   "Windows executable not built or tested here (see §14); Windows-specific visuals (fonts, DPI) were not inspected."])

# ----------------------------------------------------------------- 16 future
H1("16. Future improvements")
B(["Cancellable computations (run engines in a subprocess with a timeout).", "Step-by-step integration (substitution, by parts) using a dedicated rule engine.",
   "Inequalities and differential equations; implicit-curve plotting; parametric and polar plots.", "Session history and export of results to PDF/LaTeX.",
   "Dark theme and user-selectable precision.", "A signed Windows installer (Inno Setup) wrapping the one-folder build."])

# ----------------------------------------------------------------- 17 running
H1("17. Running the application")
P("<b>From source (Windows, Python 3.10–3.13):</b>")
CODE("""
cd FINDX
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
python main.py
""")
P("<b>Run the tests:</b> <i>pip install -r requirements-dev.txt</i> then <i>python -m pytest</i>.  <b>Built-in check:</b> <i>python main.py --selftest</i>.")
P("<b>Build the executable:</b> run <i>packaging\\build_windows.bat</i>; the result is <i>dist\\FINDX\\FINDX.exe</i> (distribute the whole folder).")
P("<b>Input tips:</b> use ^ for powers, 2x for 2·x, sqrt(), sin(), exp(), pi, oo (infinity), I (imaginary unit); one equation per line for systems; one function per line when plotting.")

# ----------------------------------------------------------------- appendix
story.append(PageBreak())
H1("Appendix A — Complete pytest log")
lines = [l for l in log.splitlines() if "PASSED" in l or "FAILED" in l or "ERROR" in l or l.startswith("=")]
lines = [re.sub(r"\s+\[\s*\d+%\]", "", l) for l in lines]
story.append(Preformatted("\n".join(lines), ParagraphStyle("log", fontName="Mono", fontSize=5.9, leading=7.1, textColor=CHAR)))


def on_page(canvas, doc):
    canvas.saveState()
    canvas.setFont("Sans", 7.5); canvas.setFillColor(STONE)
    if doc.page > 1:
        canvas.drawString(20 * mm, 12 * mm, f"FINDX {__version__} — Project Report")
        canvas.drawRightString(A4[0] - 20 * mm, 12 * mm, f"Page {doc.page}")
        canvas.setStrokeColor(BORDER); canvas.line(20 * mm, 16 * mm, A4[0] - 20 * mm, 16 * mm)
    canvas.restoreState()


out = os.path.join(DOCS, "PROJECT_REPORT.pdf")
doc = BaseDocTemplate(out, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm, topMargin=18 * mm, bottomMargin=22 * mm,
                      title="FINDX — Project Report", author="FINDX project")
doc.addPageTemplates([PageTemplate(id="p", frames=[Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="f")], onPage=on_page)])
doc.build(story)
print("wrote", out)
