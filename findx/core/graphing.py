"""2D graphing engine: sampling, discontinuity handling, roots and intersections.

Pure NumPy/SciPy/SymPy -- no Matplotlib or Qt imports, so it is fully testable.

Numerical method summary
------------------------
* Curves are sampled on a uniform grid (``NUM.plot_samples`` points).
* Complex results and non-finite values are masked (NaN) so Matplotlib draws gaps.
* Discontinuities: a segment between two samples is broken (NaN inserted) when
  the jump |Δy| exceeds ``jump_factor`` times the median absolute step *and*
  the sign flips or the jump is large relative to the data range (poles such
  as tan(x), 1/x).
* Roots: sign changes between adjacent samples are bracketed and refined with
  Brent's method (xtol 1e-12).  A candidate is rejected if |f(root)| > 1e-7
  (this removes false "roots" at poles, where the sign flips without crossing
  zero).  Tangential roots (even multiplicity, no sign change) are found by
  locating local minima of |f| and refining them with a bounded scalar
  minimiser; they are accepted only if |f| < 1e-9.
* Intersections of f and g are the roots of h = f − g, using the same routine.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from itertools import combinations
from typing import Callable, List, Optional, Tuple

import numpy as np
import sympy as sp
from scipy.optimize import brentq, minimize_scalar

from ..config import NUM
from .errors import InputError
from .parsing import parse_expression, strip_function_prefix

X = sp.Symbol("x")


@dataclass
class Curve:
    source: str
    expr: sp.Expr
    func: Callable[[np.ndarray], np.ndarray]
    label: str


@dataclass
class Point:
    x: float
    y: float
    kind: str                 # "root" | "intersection"
    curves: Tuple[int, ...]   # indices of the involved curves


@dataclass
class AnalysisResult:
    roots: List[List[float]] = field(default_factory=list)          # per-curve
    intersections: List[Point] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)


def compile_function(text: str) -> Curve:
    """Parse 'y = x^2', 'f(x) = sin(x)' or 'x^2' into a vectorised callable."""
    raw = text.strip()
    if not raw:
        raise InputError("Empty function.")
    body = strip_function_prefix(raw)
    expr = parse_expression(body, what=f"function '{raw}'")
    extra = expr.free_symbols - {X}
    if extra:
        raise InputError(f"Function '{raw}' uses unknown symbol(s): {', '.join(sorted(map(str, extra)))}. "
                         "Only the variable x is allowed.")
    if expr.has(sp.zoo, sp.nan, sp.oo, -sp.oo):
        raise InputError(f"Function '{raw}' is not a finite expression.")
    raw_f = sp.lambdify(X, expr, modules=["numpy", {"Heaviside": lambda v, h=0.5: np.heaviside(v, h)}])

    def f(xs: np.ndarray) -> np.ndarray:
        xs = np.asarray(xs, dtype=float)
        with np.errstate(all="ignore"):
            try:
                ys = raw_f(xs.astype(complex) if _needs_complex(expr) else xs)
            except Exception:
                ys = np.array([_scalar(raw_f, v) for v in xs])
        ys = np.asarray(ys)
        if ys.shape == ():
            ys = np.full(xs.shape, ys)
        if np.iscomplexobj(ys):
            ys = np.where(np.abs(ys.imag) <= 1e-12 * np.maximum(1, np.abs(ys.real)), ys.real, np.nan)
        ys = ys.astype(float)
        ys[~np.isfinite(ys)] = np.nan
        return ys

    return Curve(source=raw, expr=expr, func=f, label=f"y = {sp.sstr(expr)}")


def _needs_complex(expr: sp.Expr) -> bool:
    """Even roots/logs of negative reals should give NaN, not warnings; handle via real arithmetic."""
    return False


def _scalar(fn, v):
    try:
        out = complex(fn(float(v)))
        return out.real if abs(out.imag) < 1e-12 else np.nan
    except Exception:
        return np.nan


def sample_curve(curve: Curve, xmin: float, xmax: float, n: Optional[int] = None) -> Tuple[np.ndarray, np.ndarray]:
    """Sample a curve and break the line at discontinuities."""
    if not (np.isfinite(xmin) and np.isfinite(xmax)) or xmin >= xmax:
        raise InputError("Invalid x-range: x-min must be less than x-max.")
    n = n or NUM.plot_samples
    xs = np.linspace(xmin, xmax, n)
    ys = curve.func(xs)
    return insert_breaks(xs, ys)


def insert_breaks(xs: np.ndarray, ys: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    ys = ys.copy()
    finite = np.isfinite(ys)
    if finite.sum() < 3:
        return xs, ys
    dy = np.abs(np.diff(ys))
    valid = np.isfinite(dy)
    if valid.sum() == 0:
        return xs, ys
    med = np.median(dy[valid])
    # Robust scale of the data (ignoring extreme outliers)
    lo, hi = np.nanpercentile(ys[finite], [5, 95])
    spread = max(hi - lo, 1e-12)
    big = valid & (dy > max(NUM.jump_factor * med, 0.5 * spread)) & (dy > 10 * (med + 1e-12))
    sign_flip = np.sign(ys[:-1]) * np.sign(ys[1:]) < 0
    # A jump is a pole/discontinuity when the step is huge; keep steep-but-continuous
    # curves (e.g. x^9) by requiring a sign flip OR a step far above the spread.
    brk = big & (sign_flip | (dy > 5 * spread))
    # Also break at the edge of the domain (finite next to NaN is natural gap).
    idx = np.where(brk)[0]
    if idx.size:
        ys[idx] = ys[idx]  # no-op: keep copy semantic
        ys[idx + 1] = np.where(brk[idx], ys[idx + 1], ys[idx + 1])
        # Insert NaN after each breaking sample by masking the *larger* side
        ys[idx] = np.nan
    return xs, ys


# ---------------------------------------------------------------------------
# root finding
# ---------------------------------------------------------------------------
def find_roots_numeric(func: Callable[[np.ndarray], np.ndarray], xmin: float, xmax: float,
                       n: int = 20001, ftol: float = NUM.root_ftol) -> List[float]:
    """Real roots of ``func`` on [xmin, xmax] (see module docstring for the method)."""
    xs = np.linspace(xmin, xmax, n)
    ys = func(xs)
    roots: List[float] = []

    def scalar(t: float) -> float:
        v = func(np.array([t]))[0]
        return float(v)

    scale = max(1.0, float(np.nanmax(np.abs(ys[np.isfinite(ys)])))) if np.isfinite(ys).any() else 1.0
    # 1. exact zeros on the grid
    for i in np.where(ys == 0)[0]:
        roots.append(float(xs[i]))
    # 2. sign changes
    s = np.sign(ys)
    ch = np.where((s[:-1] * s[1:] < 0) & np.isfinite(ys[:-1]) & np.isfinite(ys[1:]))[0]
    for i in ch:
        try:
            r = brentq(scalar, xs[i], xs[i + 1], xtol=NUM.root_xtol, rtol=1e-14, maxiter=200)
        except (ValueError, RuntimeError):
            continue
        fr = scalar(r)
        # Reject poles: |f| must be tiny at the located point.
        if np.isfinite(fr) and abs(fr) <= max(ftol, ftol * scale * 1e-2):
            roots.append(float(r))
    # 3. tangential roots (local minima of |f| without a sign change)
    a = np.abs(ys)
    for i in range(1, n - 1):
        if np.isfinite(a[i - 1]) and np.isfinite(a[i]) and np.isfinite(a[i + 1]) \
                and a[i] <= a[i - 1] and a[i] <= a[i + 1] and a[i] < 1e-2 * scale and (s[i - 1] * s[i + 1] >= 0):
            try:
                res = minimize_scalar(lambda t: abs(scalar(t)), bounds=(xs[i - 1], xs[i + 1]), method="bounded",
                                      options={"xatol": 1e-13})
            except Exception:
                continue
            if res.fun < 1e-9 * max(1.0, scale):
                roots.append(float(res.x))
    roots.sort()
    out: List[float] = []
    for r in roots:
        if not out or abs(r - out[-1]) > max(NUM.dedupe_tol, 1e-9 * (abs(r) + 1)):
            out.append(r)
    # tidy near-zero values
    return [0.0 if abs(r) < 1e-12 else r for r in out]


def find_roots(curve: Curve, xmin: float, xmax: float) -> List[float]:
    return find_roots_numeric(curve.func, xmin, xmax)


def find_intersections(c1: Curve, c2: Curve, xmin: float, xmax: float) -> List[Tuple[float, float]]:
    def diff(xs: np.ndarray) -> np.ndarray:
        return c1.func(xs) - c2.func(xs)
    pts = []
    for r in find_roots_numeric(diff, xmin, xmax):
        y1, y2 = float(c1.func(np.array([r]))[0]), float(c2.func(np.array([r]))[0])
        y = y1 if np.isfinite(y1) else y2
        if np.isfinite(y):
            pts.append((r, y))
    return pts


def analyse(curves: List[Curve], xmin: float, xmax: float, roots: bool = True, intersections: bool = True) -> AnalysisResult:
    res = AnalysisResult()
    for c in curves:
        res.roots.append(find_roots(c, xmin, xmax) if roots else [])
    if intersections:
        for (i, a), (j, b) in combinations(list(enumerate(curves)), 2):
            for x, y in find_intersections(a, b, xmin, xmax):
                res.intersections.append(Point(x, y, "intersection", (i, j)))
    res.notes.append(f"Search interval: x in [{xmin:.6g}, {xmax:.6g}]; 20,001-point scan; "
                     f"Brent xtol {NUM.root_xtol:g}; roots accepted when |f| < {NUM.root_ftol:g}.")
    res.notes.append("Limitations: roots/intersections are real, found only inside the interval, and very close "
                     "double roots or rapidly oscillating functions may be missed.")
    return res


def format_analysis(curves: List[Curve], res: AnalysisResult) -> str:
    lines: List[str] = []
    for i, (c, rs) in enumerate(zip(curves, res.roots)):
        lines.append(f"[{i + 1}] {c.label}")
        if rs:
            for r in rs:
                lines.append(f"     root:  x = {r:.8g}   (x, y) = ({r:.6g}, 0)")
        else:
            lines.append("     no roots found in the interval")
    if len(curves) > 1:
        lines.append("")
        lines.append("Intersections:")
        if res.intersections:
            for p in res.intersections:
                a, b = p.curves
                lines.append(f"     [{a + 1}] ∩ [{b + 1}]:  ({p.x:.8g}, {p.y:.8g})")
        else:
            lines.append("     none found in the interval")
    lines.append("")
    lines += res.notes
    return "\n".join(lines)


def auto_y_range(curves: List[Curve], xmin: float, xmax: float) -> Tuple[float, float]:
    """Choose a readable y-range from the 2nd-98th percentile of finite values."""
    vals = []
    xs = np.linspace(xmin, xmax, 2000)
    for c in curves:
        y = c.func(xs)
        y = y[np.isfinite(y)]
        if y.size:
            vals.append(y)
    if not vals:
        return -10.0, 10.0
    allv = np.concatenate(vals)
    lo, hi = np.percentile(allv, [2, 98])
    if hi - lo < 1e-9:
        lo, hi = lo - 1, hi + 1
    pad = 0.1 * (hi - lo)
    return float(lo - pad), float(hi + pad)
