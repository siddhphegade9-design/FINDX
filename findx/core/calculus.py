"""Calculus engine: integrals and limits with exact + numerical results."""
from __future__ import annotations

import math
from typing import Optional

import numpy as np
import sympy as sp
from scipy import integrate as sci_integrate

from .errors import ComputationError, InputError
from .parsing import parse_expression, parse_number, parse_symbol
from .report import Report


def _single_var(expr: sp.Expr, var_text: str, rep: Report) -> sp.Symbol:
    if var_text and var_text.strip():
        return parse_symbol(var_text)
    free = sorted(expr.free_symbols, key=lambda s: s.name)
    if not free:
        return sp.Symbol("x")
    if len(free) == 1:
        return free[0]
    x = sp.Symbol("x")
    v = x if x in free else free[0]
    rep.note(f"Several symbols found; integrating/limiting with respect to '{v}'. Others are treated as constants.")
    return v


def _strategy_hint(expr: sp.Expr, var: sp.Symbol) -> Optional[str]:
    """Name a standard technique that is plausibly relevant (heuristic description)."""
    if expr.is_polynomial(var):
        return "Polynomial: apply the power rule term by term, ∫xⁿ dx = xⁿ⁺¹/(n+1)."
    if expr.is_Add:
        return "Linearity: integrate each term separately."
    if expr.is_Mul and sum(1 for a in expr.args if a.has(var)) >= 2:
        return "Product of functions of the variable: integration by parts or substitution (selected automatically by SymPy's heuristics/Risch algorithm)."
    if expr.is_rational_function(var):
        return "Rational function: partial-fraction decomposition."
    return None


def integrate_indefinite(expression: str, variable: str = "") -> Report:
    expr = parse_expression(expression)
    rep = Report("Calculus — Indefinite integral")
    var = _single_var(expr, variable, rep)
    rep.heading("Original expression"); rep.math(sp.Integral(expr, var))
    hint = _strategy_hint(expr, var)
    if hint:
        rep.heading("Method"); rep.text(hint)
    try:
        res = sp.integrate(expr, var)
    except (NotImplementedError, ValueError, RecursionError) as exc:
        raise ComputationError(f"The integral could not be evaluated symbolically: {exc}")
    rep.heading("Result")
    if res.has(sp.Integral):
        rep.warn("SymPy could not find a closed-form antiderivative (it may not be elementary).")
        rep.math(res)
        rep.data["result"] = None
        return rep
    rep.exact(sp.Eq(sp.Symbol("∫ f dx"), res, evaluate=False) if False else res, "F(x) = ")
    rep.text("The full family of antiderivatives is F(x) + C, where C is an arbitrary constant of integration:")
    C = sp.Symbol("C")
    rep.exact(res + C, "∫ f dx = ")
    # verification
    diff_back = sp.simplify(sp.diff(res, var) - expr)
    if diff_back == 0:
        rep.text(f"Verification: d/d{var} of the result equals the integrand (exact).")
    else:
        # numeric spot check
        ok = _spot_check(sp.diff(res, var), expr, var)
        rep.text("Verification: derivative of the result matches the integrand at sample points (numeric check)."
                 if ok else "Warning: derivative check could not be confirmed symbolically.")
    rep.data["result"] = res
    return rep


def _spot_check(a: sp.Expr, b: sp.Expr, var: sp.Symbol) -> bool:
    for v in (0.37, 1.31, 2.7, -0.83):
        try:
            if abs(complex(sp.N((a - b).subs(var, v)))) > 1e-8:
                return False
        except Exception:
            continue
    return True


def _numeric_quad(expr: sp.Expr, var: sp.Symbol, a, b) -> Optional[float]:
    f = sp.lambdify(var, expr, modules=["numpy"])
    lo = -np.inf if a == -sp.oo else float(a)
    hi = np.inf if b == sp.oo else float(b)
    try:
        with np.errstate(all="ignore"):
            val, err = sci_integrate.quad(lambda t: float(np.real(f(t))), lo, hi, limit=200)
        return val if math.isfinite(val) else None
    except Exception:
        return None


def integrate_definite(expression: str, lower: str, upper: str, variable: str = "") -> Report:
    expr = parse_expression(expression)
    a = parse_number(lower, "lower limit", allow_inf=True)
    b = parse_number(upper, "upper limit", allow_inf=True)
    rep = Report("Calculus — Definite integral")
    var = _single_var(expr, variable, rep)
    rep.heading("Original expression"); rep.math(sp.Integral(expr, (var, a, b)))
    if a == b:
        rep.heading("Result"); rep.text("The limits are equal, so the integral is 0."); rep.data["result"] = sp.Integer(0)
        return rep
    rep.heading("Method")
    rep.text("Fundamental Theorem of Calculus: ∫ₐᵇ f dx = F(b) − F(a), with F an antiderivative; "
             "improper limits (±∞) are handled as limits of F.")
    try:
        anti = sp.integrate(expr, var)
    except (NotImplementedError, ValueError, RecursionError):
        anti = None
    exact = None
    if anti is not None and not anti.has(sp.Integral):
        rep.math(anti, "antiderivative F = ")
        # discontinuity inside interval?
        try:
            sing = sp.singularities(expr, var)
        except Exception:
            sing = set()
        inside = [s for s in sing if s.is_real and (a == -sp.oo or s >= a) and (b == sp.oo or s <= b)] if sing else []
        if inside:
            rep.warn(f"The integrand is singular at {', '.join(map(str, inside))} inside/at the interval, so the integral is improper there. "
                     "Evaluating F(b) − F(a) naively would be invalid; SymPy's limit-based evaluation is used instead.")
        try:
            exact = sp.integrate(expr, (var, a, b))
        except Exception:
            exact = None
    else:
        try:
            exact = sp.integrate(expr, (var, a, b))
        except Exception:
            exact = None
    if exact is not None and (exact.has(sp.Integral) or exact.has(sp.nan)):
        exact = None
    rep.heading("Result")
    num = _numeric_quad(expr, var, a, b) if not expr.free_symbols - {var} else None
    # Safety net: never trust a symbolic value that disagrees with quadrature.
    if exact is not None and num is not None and exact.is_finite is not False:
        try:
            ev = complex(sp.N(exact, 20))
            if abs(ev.imag) > 1e-9 or abs(ev.real - num) > 1e-6 * max(1.0, abs(num)):
                rep.warn("The symbolic value disagreed with an independent numerical integration, so it was discarded "
                         "and only the numerical approximation is reported.")
                exact = None
        except Exception:
            exact = None
    if exact is not None and not exact.has(sp.zoo):
        if exact == sp.oo or exact == -sp.oo:
            rep.warn("The integral diverges (infinite).")
        else:
            rep.exact(sp.simplify(exact), "exact value = ")
            if not sp.simplify(exact).is_Rational:
                rep.approx(sp.N(exact, 12), "approx = ")
        rep.data["result"] = exact
        if num is not None and not exact.has(sp.oo):
            try:
                diff = abs(num - float(sp.N(exact)))
                rep.text(f"Numerical cross-check (adaptive Gauss–Kronrod, scipy.integrate.quad): {num:.12g}  (difference {diff:.1e}).")
            except Exception:
                pass
    elif num is not None:
        rep.warn("No exact closed form was found; the value below is a numerical approximation only.")
        rep.approx(sp.Float(num, 12), "≈ ")
        rep.text("Method: adaptive Gauss–Kronrod quadrature (scipy.integrate.quad); typical accuracy 1e-8 or better for smooth integrands.")
        rep.data["result"] = num
        rep.data["numerical"] = True
    else:
        raise ComputationError("The integral could neither be evaluated exactly nor numerically (it may diverge or be singular).")
    return rep


def limit(expression: str, point: str, direction: str = "both", variable: str = "") -> Report:
    expr = parse_expression(expression)
    pt = parse_number(point, "limit point", allow_inf=True)
    if direction not in ("both", "+", "-"):
        raise InputError("Direction must be 'both', '+' (right) or '-' (left).")
    rep = Report("Calculus — Limit")
    var = _single_var(expr, variable, rep)
    rep.heading("Original expression")
    dir_sym = {"+": "⁺", "-": "⁻", "both": ""}[direction]
    rep.math(sp.Limit(expr, var, pt, "+" if direction == "+" else "-" if direction == "-" else "+-"))
    rep.heading("Method")
    rep.text("Direct substitution is tried first; indeterminate forms (0/0, ∞/∞, …) are resolved by SymPy's limit algorithm "
             "(Gruntz algorithm: series/asymptotic comparison).")
    try:
        direct = expr.subs(var, pt)
        if direct.is_finite and not direct.has(sp.nan, sp.zoo) and pt.is_finite:
            rep.text(f"Direct substitution gives {direct}, which is defined, so (for a continuous expression) the limit equals it.")
        else:
            rep.text(f"Direct substitution gives {direct}: this is indeterminate or undefined, so further analysis is required.")
    except Exception:
        pass
    rep.heading("Result")
    try:
        if direction == "both" and pt.is_finite:
            left = sp.limit(expr, var, pt, "-")
            right = sp.limit(expr, var, pt, "+")
            rep.exact(left, f"left-hand limit (x → {pt}⁻) = ")
            rep.exact(right, f"right-hand limit (x → {pt}⁺) = ")
            if sp.simplify(left - right) == 0 if (left.is_finite and right.is_finite) else left == right:
                rep.exact(right, "two-sided limit = ")
                rep.data["result"] = right
            else:
                rep.warn("The one-sided limits differ, so the two-sided limit does not exist.")
                rep.data["result"] = None
            rep.data["left"], rep.data["right"] = left, right
            res = right
        else:
            d = "+" if direction in ("both", "+") else "-"
            res = sp.limit(expr, var, pt, d)
            label = {"+": f"right-hand limit (x → {pt}⁺) = ", "-": f"left-hand limit (x → {pt}⁻) = "}[d] if pt.is_finite else f"limit (x → {pt}) = "
            rep.exact(res, label)
            rep.data["result"] = res
    except (NotImplementedError, ValueError, RecursionError) as exc:
        raise ComputationError(f"SymPy could not determine this limit: {exc}")
    if isinstance(res, sp.Limit):
        rep.warn("The limit could not be evaluated in closed form.")
        rep.data["result"] = None
    elif res.is_finite is False or res in (sp.oo, -sp.oo):
        rep.note("An infinite limit means the expression grows without bound (the limit does not exist as a finite number).")
    elif not res.is_Rational and res.is_number:
        rep.approx(sp.N(res, 12), "≈ ")
    return rep
