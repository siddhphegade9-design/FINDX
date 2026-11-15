"""Algebra engine: equations, polynomials, factorisation and systems.

Intermediate steps are only emitted when they are genuinely derived from the
input (coefficient extraction, discriminant, rational-root testing, polynomial
division, ...).  Nothing is hard-coded.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import numpy as np
import sympy as sp
from scipy.optimize import brentq

from ..config import NUM
from .errors import ComputationError, InputError
from .parsing import parse_equation, parse_expression, parse_symbol, split_top_level
from .report import Report

DEGREE_NAMES = {1: "linear", 2: "quadratic", 3: "cubic", 4: "quartic", 5: "quintic"}


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _choose_variable(free: List[sp.Symbol], requested: Optional[str], report: Report) -> sp.Symbol:
    if requested:
        v = parse_symbol(requested)
        if free and v not in free:
            raise InputError(f"The equation does not contain the variable '{v}'.")
        return v
    if not free:
        raise InputError("The equation contains no variable to solve for.")
    if len(free) == 1:
        return free[0]
    x = sp.Symbol("x")
    v = x if x in free else free[0]
    report.note(f"Several variables found ({', '.join(map(str, free))}); solving for '{v}'. "
                "Other symbols are treated as constants (symbolic parameters).")
    return v


def _sorted_syms(expr) -> List[sp.Symbol]:
    return sorted(expr.free_symbols, key=lambda s: s.name)


def _is_poly(expr: sp.Expr, var: sp.Symbol) -> bool:
    try:
        p = sp.Poly(expr, var)
        return p.degree() >= 1
    except sp.PolynomialError:
        return False


def _approx(value, digits: int = 10):
    try:
        return sp.N(value, digits)
    except Exception:  # pragma: no cover
        return value


def _root_kind(r) -> str:
    n = complex(sp.N(r))
    return "real" if abs(n.imag) < 1e-12 else "complex"


def _rational_candidates(poly: sp.Poly) -> List[sp.Rational]:
    """Candidates p/q for the Rational Root Theorem (integer-cleared poly)."""
    coeffs = poly.all_coeffs()
    lcm = sp.ilcm(*[sp.Rational(c).q for c in coeffs]) if coeffs else 1
    ints = [int(sp.Rational(c) * lcm) for c in coeffs]
    while ints and ints[-1] == 0:
        ints.pop()
    if not ints:
        return []
    a0, an = abs(ints[-1]), abs(ints[0])
    if a0 == 0 or an == 0:
        return []
    ps = sp.divisors(a0) if a0 < 10**9 else []
    qs = sp.divisors(an) if an < 10**9 else []
    cands = set()
    for p in ps:
        for q in qs:
            cands.add(sp.Rational(p, q)); cands.add(-sp.Rational(p, q))
    return sorted(cands)


# ---------------------------------------------------------------------------
# polynomial solving
# ---------------------------------------------------------------------------
def _solve_polynomial(poly: sp.Poly, var: sp.Symbol, rep: Report) -> List[Tuple[sp.Expr, int]]:
    """Solve a univariate polynomial = 0 and narrate the method.  Returns [(root, multiplicity)]."""
    deg = poly.degree()
    kind = DEGREE_NAMES.get(deg, f"degree-{deg}")
    rep.heading("Solving approach")
    rep.text(f"Rearranged to the form P({var}) = 0, this is a {kind} polynomial equation (degree {deg}).")
    rep.math(sp.Eq(poly.as_expr(), 0, evaluate=False), "P: ")
    coeffs = poly.all_coeffs()
    rep.text("Coefficients (highest power first): " + ", ".join(sp.sstr(c) for c in coeffs))

    roots: Dict[sp.Expr, int] = {}
    if deg == 1:
        a, b = coeffs
        rep.text(f"For a·{var} + b = 0 with a = {a} and b = {b}, a ≠ 0, so {var} = -b / a.")
        rep.math(sp.Eq(var, sp.nsimplify(-b / a), evaluate=False))
        roots[sp.simplify(-b / a)] = 1
    elif deg == 2:
        a, b, c = coeffs
        disc = sp.expand(b**2 - 4 * a * c)
        rep.text("Quadratic formula: x = (-b ± √(b² - 4ac)) / (2a), with")
        rep.math(f"a = {a},  b = {b},  c = {c}")
        rep.math(sp.Eq(sp.Symbol("Δ"), disc, evaluate=False), "discriminant ")
        if disc.is_number:
            if disc > 0:
                rep.text("Δ > 0: two distinct real roots.")
            elif disc == 0:
                rep.text("Δ = 0: one repeated real root (multiplicity 2).")
            else:
                rep.text("Δ < 0: two complex-conjugate roots.")
        for r in sp.roots(poly, var, multiple=True):
            roots[sp.simplify(r)] = roots.get(sp.simplify(r), 0) + 1
    else:
        # Rational Root Theorem + polynomial division, then solve the remainder.
        remaining = poly
        cands = _rational_candidates(poly)
        found: List[sp.Rational] = []
        if cands and len(cands) <= 400:
            rep.text(f"Rational Root Theorem: any rational root is p/q with p dividing the constant term and q the leading coefficient "
                     f"({len(cands)} candidates tested exactly).")
            for cnd in cands:
                while remaining.degree() >= 1 and remaining.eval(cnd) == 0:
                    found.append(cnd)
                    q, r = sp.div(remaining, sp.Poly(var - cnd, var))
                    remaining = q
            if found:
                for cnd in sorted(set(found)):
                    rep.text(f"{var} = {cnd} is a root (multiplicity {found.count(cnd)} found by repeated division by ({var} - {cnd})).")
                    roots[cnd] = found.count(cnd)
                if remaining.degree() >= 1:
                    rep.text("Reduced polynomial after dividing out the rational roots:")
                    rep.math(remaining.as_expr())
                else:
                    rep.text("Dividing out all rational roots leaves a constant: the polynomial splits completely over the rationals.")
            else:
                rep.text("No rational roots exist, so the polynomial has no linear factor over the rationals.")
        if remaining.degree() >= 1:
            rem_deg = remaining.degree()
            if rem_deg == 1:
                a, b = remaining.all_coeffs()
                roots[sp.simplify(-b / a)] = roots.get(sp.simplify(-b / a), 0) + 1
            else:
                rep.text("Factorisation of the reduced polynomial over the rationals:")
                rep.math(sp.factor(remaining.as_expr()))
                rs = sp.roots(remaining, var)
                total = sum(rs.values()) if rs else 0
                if total == rem_deg:
                    if rem_deg == 2:
                        a, b, c = remaining.all_coeffs()
                        rep.text(f"Quadratic formula with Δ = {sp.expand(b**2 - 4*a*c)}.")
                    elif rem_deg in (3, 4):
                        rep.text("Closed-form radical formulas (Cardano/Ferrari, via SymPy) give the remaining roots.")
                    for r, m in rs.items():
                        r = sp.simplify(r)
                        roots[r] = roots.get(r, 0) + m
                else:
                    rep.warn(f"No closed-form radical solution was found for the remaining degree-{rem_deg} factor "
                             "(Abel–Ruffini: general polynomials of degree ≥ 5 are not solvable in radicals). "
                             "Its roots are computed numerically (Durand–Kerner/companion-matrix via SymPy, 15 digits).")
                    for r in remaining.nroots(n=15, maxsteps=200):
                        key = sp.N(r, 12)
                        roots[key] = roots.get(key, 0) + 1
                    rep.data["numerical_roots"] = True
    # merge numerically equal duplicates
    return sorted(roots.items(), key=lambda kv: (float(sp.re(sp.N(kv[0]))), float(sp.im(sp.N(kv[0])))))


def _numeric_real_roots(f_expr: sp.Expr, var: sp.Symbol, lo: float = -50.0, hi: float = 50.0, n: int = 20001) -> List[float]:
    """Sign-change scan + Brent refinement for non-polynomial equations."""
    f = sp.lambdify(var, f_expr, modules=["numpy"])
    xs = np.linspace(lo, hi, n)
    with np.errstate(all="ignore"):
        try:
            ys = np.asarray(f(xs), dtype=complex)
        except Exception:
            ys = np.array([complex(f(x)) for x in xs])
    ys = np.where(np.abs(ys.imag) < 1e-12, ys.real, np.nan)
    roots: List[float] = []
    for i in range(len(xs) - 1):
        y0, y1 = ys[i], ys[i + 1]
        if not (np.isfinite(y0) and np.isfinite(y1)):
            continue
        if y0 == 0:
            roots.append(float(xs[i]))
        elif y0 * y1 < 0:
            try:
                r = brentq(lambda t: float(np.real(f(t))), xs[i], xs[i + 1], xtol=NUM.root_xtol)
            except Exception:
                continue
            if abs(float(np.real(f(r)))) < 1e-6:     # reject poles / jumps
                roots.append(float(r))
    out: List[float] = []
    for r in sorted(roots):
        if not out or abs(r - out[-1]) > NUM.dedupe_tol:
            out.append(r)
    return out


# ---------------------------------------------------------------------------
# public API
# ---------------------------------------------------------------------------
def solve_equation(text: str, variable: Optional[str] = None) -> Report:
    """Solve a single equation (or several separated by ';' as a system)."""
    parts = split_top_level(text)
    if not parts:
        raise InputError("Please enter an equation.")
    if len(parts) > 1:
        return solve_system(parts, variable)
    eq = parse_equation(parts[0])
    rep = Report("Algebra Solver — Equation")
    rep.heading("Original equation")
    rep.math(eq)
    expr = sp.expand(eq.lhs - eq.rhs)
    if expr == 0:
        rep.heading("Result")
        rep.text("The equation is an identity: every value of the variable is a solution.")
        rep.data["solutions"] = "all"
        return rep
    free = _sorted_syms(expr)
    if not free:
        rep.heading("Result")
        rep.text("The equation contains no variables and is false (a contradiction): no solution.")
        rep.data["solutions"] = []
        return rep
    var = _choose_variable(free, variable, rep)
    rep.data["variable"] = str(var)

    # ---- polynomial in var --------------------------------------------------
    if _is_poly(expr, var):
        poly = sp.Poly(expr, var)
        rep.heading("Rearrangement")
        rep.text(f"Move every term to one side: lhs - rhs = 0 and expand.")
        rep.math(sp.Eq(expr, 0, evaluate=False))
        if any(c.free_symbols for c in poly.all_coeffs()):
            return _solve_symbolic_parametric(expr, var, poly, rep)
        rep = _finish_polynomial(poly, var, rep)
        return rep

    # ---- general (rational / transcendental) -------------------------------
    rep.heading("Solving approach")
    rep.text("The equation is not a polynomial in the variable, so SymPy's symbolic solver is tried first.")
    sols = []
    try:
        sols = sp.solve(expr, var, dict=False)
    except (NotImplementedError, ValueError, TypeError, RecursionError):
        sols = []
    if not isinstance(sols, list):
        sols = [sols]
    sols = [s for s in sols if not (isinstance(s, sp.Basic) and s.has(sp.zoo, sp.nan))]
    rep.heading("Solutions")
    if sols:
        # Verify by substitution (rejects extraneous roots from squaring etc.)
        verified = []
        for s in sols:
            try:
                resid = abs(complex(sp.N(expr.subs(var, s), 30)))
            except Exception:
                resid = float("inf")
            if resid < 1e-8:
                verified.append(s)
        dropped = len(sols) - len(verified)
        if dropped:
            rep.note(f"{dropped} candidate(s) failed verification by substitution and were discarded (extraneous solutions).")
        for s in verified:
            rep.exact(sp.Eq(var, s, evaluate=False))
            if not s.is_Integer and not s.is_Rational:
                rep.approx(sp.Eq(var, _approx(s), evaluate=False))
        if verified:
            rep.note("These are the solutions SymPy's symbolic solver could find. "
                     "Equations with periodic or transcendental behaviour may have additional solutions not listed.")
            rep.data["solutions"] = verified
            return rep
    # numeric fallback
    rep.text("No (verified) symbolic solution was available, so a numerical scan was used.")
    if len(_sorted_syms(expr)) > 1:
        raise ComputationError("Numerical solving needs a single unknown with all other symbols numeric.")
    roots = _numeric_real_roots(expr, var)
    if not roots:
        rep.warn("No real roots were found in the search interval [-50, 50]. "
                 "This does not prove that none exist outside it, or complex ones.")
        rep.data["solutions"] = []
        return rep
    for r in roots:
        rep.approx(sp.Eq(var, sp.Float(r, 12), evaluate=False))
    rep.note("Numerical method: 20,001-point sign-change scan on [-50, 50] refined by Brent's method (xtol 1e-12). "
             "Only real roots where the function changes sign are found; double roots touching zero can be missed.")
    rep.data["solutions"] = roots
    rep.data["numerical"] = True
    return rep


def _finish_polynomial(poly: sp.Poly, var: sp.Symbol, rep: Report) -> Report:
    roots = _solve_polynomial(poly, var, rep)
    rep.heading("Factored form")
    factored = sp.factor(poly.as_expr())
    rep.math(factored)
    rep.heading("Solutions")
    total = 0
    for r, m in roots:
        total += m
        numeric_root = isinstance(r, sp.Float) or (isinstance(r, sp.Basic) and r.has(sp.Float))
        kind = _root_kind(r)
        tag = f"   ({kind}" + (f", multiplicity {m}" if m > 1 else "") + ")"
        if numeric_root:
            rep.approx(sp.Eq(var, r, evaluate=False), "", suffix=tag)
        else:
            rep.exact(sp.Eq(var, r, evaluate=False), suffix=tag)
            if not (r.is_Rational):
                rep.approx(sp.Eq(var, _approx(r), evaluate=False))
    rep.text(f"Counting multiplicities there are {total} roots, matching the degree {poly.degree()} "
             "(Fundamental Theorem of Algebra).")
    # verification
    max_resid = 0.0
    for r, _ in roots:
        try:
            max_resid = max(max_resid, abs(complex(sp.N(poly.as_expr().subs(var, r), 30))))
        except Exception:
            pass
    rep.note(f"Verification: substituting each root into P gives a maximum residual of {max_resid:.2e}.")
    rep.data["solutions"] = [r for r, _ in roots]
    rep.data["multiplicities"] = {str(r): m for r, m in roots}
    rep.data["max_residual"] = max_resid
    return rep


def _solve_symbolic_parametric(expr: sp.Expr, var: sp.Symbol, poly: sp.Poly, rep: Report) -> Report:
    rep.heading("Solving approach")
    params = sorted({s for c in poly.all_coeffs() for s in c.free_symbols}, key=lambda s: s.name)
    rep.text(f"Other symbols ({', '.join(map(str, params))}) are treated as constants. "
             f"The equation is a degree-{poly.degree()} polynomial in {var}; a symbolic solution is returned in terms of them.")
    try:
        sols = sp.solve(expr, var)
    except (NotImplementedError, ValueError) as exc:
        raise ComputationError(f"No symbolic solution found: {exc}")
    rep.heading("Solutions")
    for s in sols:
        rep.exact(sp.Eq(var, sp.simplify(s), evaluate=False))
    rep.note("Parametric results may be invalid for special parameter values (e.g. when a leading coefficient becomes 0).")
    rep.data["solutions"] = sols
    return rep


def solve_system(equations: List[str], variables: Optional[str] = None) -> Report:
    """Solve a system of equations (linear or polynomial) symbolically."""
    eqs = [parse_equation(t) for t in equations]
    rep = Report("Algebra Solver — System of equations")
    rep.heading("Original system")
    for e in eqs:
        rep.math(e)
    exprs = [sp.expand(e.lhs - e.rhs) for e in eqs]
    syms = sorted(set().union(*[x.free_symbols for x in exprs]), key=lambda s: s.name)
    if variables and variables.strip():
        from .parsing import parse_symbol_list
        syms = parse_symbol_list(variables)
    if not syms:
        raise InputError("The system contains no variables.")
    rep.heading("Solving approach")
    all_linear = all(sp.Poly(x, *syms).total_degree() <= 1 for x in exprs if x != 0) if exprs else False
    if all_linear:
        rep.text("All equations are linear in the unknowns, so the system is solved by Gaussian elimination "
                 "(SymPy `linsolve`); the coefficient matrix and rank are shown.")
        A, b = sp.linear_eq_to_matrix(exprs, syms)
        rep.math(A, "Coefficient matrix A:")
        rep.math(b, "Constant vector b:")
        rank_a = A.rank(); rank_ab = A.row_join(b).rank()
        rep.text(f"rank(A) = {rank_a}, rank([A|b]) = {rank_ab}, number of unknowns = {len(syms)}.")
        sol = sp.linsolve(exprs, syms)
        if sol == sp.EmptySet:
            rep.heading("Solutions"); rep.text("The system is inconsistent (rank(A) < rank([A|b])): no solution.")
            rep.data["solutions"] = []
        else:
            tup = list(sol)[0]
            rep.heading("Solutions")
            for s, v in zip(syms, tup):
                rep.exact(sp.Eq(s, v, evaluate=False))
            if rank_a < len(syms):
                rep.note("rank(A) is smaller than the number of unknowns, so there are infinitely many solutions "
                         "parametrised by the free variables shown.")
            rep.data["solutions"] = [dict(zip(syms, tup))]
        return rep
    rep.text("The system is non-linear; SymPy's polynomial solver (Gröbner-basis based) is used.")
    try:
        sol = sp.solve(exprs, syms, dict=True)
    except (NotImplementedError, ValueError) as exc:
        raise ComputationError(f"Could not solve this non-linear system symbolically: {exc}")
    rep.heading("Solutions")
    if not sol:
        rep.text("No solution found (the system may be inconsistent).")
    for i, d in enumerate(sol, 1):
        rep.text(f"Solution {i}:")
        for s in syms:
            if s in d:
                rep.exact(sp.Eq(s, d[s], evaluate=False))
                if not d[s].is_Rational:
                    rep.approx(sp.Eq(s, _approx(d[s]), evaluate=False))
    rep.data["solutions"] = sol
    return rep


def factor_polynomial(text: str, variable: Optional[str] = None) -> Report:
    """Factor an expression over the rationals and report irreducible factors."""
    parts = text.split("=")
    expr = parse_expression(parts[0], what="polynomial") if len(parts) == 1 else None
    if expr is None:
        eq = parse_equation(text)
        expr = eq.lhs - eq.rhs
    rep = Report("Algebra Solver — Factorisation")
    rep.heading("Original polynomial")
    rep.math(expr)
    expanded = sp.expand(expr)
    rep.text("Expanded form:")
    rep.math(expanded)
    free = _sorted_syms(expanded)
    if not free:
        raise InputError("Nothing to factor: the expression is a constant.")
    try:
        content, factors = sp.factor_list(expanded)
    except sp.PolynomialError as exc:
        raise InputError(f"Cannot factor: {exc}")
    rep.heading("Factorisation over the rationals")
    rep.math(sp.factor(expanded))
    rep.heading("Irreducible factors")
    if content != 1:
        rep.text(f"Constant content: {content}")
    for f, m in factors:
        rep.math(f"({sp.sstr(f)})" + (f"^{m}" if m > 1 else ""))
    if len(factors) == 1 and factors[0][1] == 1:
        rep.note("The polynomial is irreducible over the rationals.")
    # extended factorisation
    try:
        ext = sp.factor(expanded, extension=[sp.I])
        if ext != sp.factor(expanded):
            rep.heading("Over the Gaussian rationals (complex)")
            rep.math(ext)
    except Exception:
        pass
    rep.data["factored"] = sp.factor(expanded)
    return rep
