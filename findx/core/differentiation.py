"""Differentiation engine: ordinary, higher-order, partial and implicit derivatives."""
from __future__ import annotations

from typing import List, Optional

import sympy as sp

from .errors import ComputationError, InputError
from .parsing import (parse_assignments, parse_equation, parse_expression, parse_symbol,
                      parse_symbol_list)
from .report import Report


def _rule_walkthrough(expr: sp.Expr, var: sp.Symbol, rep: Report) -> None:
    """Describe the top-level differentiation rule actually applied (one level deep)."""
    if not expr.has(var):
        rep.text(f"The expression does not depend on {var}, so by the constant rule its derivative is 0.")
        return
    if expr.is_Add:
        rep.text("Sum rule: differentiate term by term.")
        for t in expr.args:
            rep.math(sp.Eq(sp.Derivative(t, var), sp.diff(t, var), evaluate=False))
    elif expr.is_Mul:
        dep = [a for a in expr.args if a.has(var)]
        const = [a for a in expr.args if not a.has(var)]
        if const:
            rep.text(f"Constant-multiple rule: factor {sp.Mul(*const)} out of the derivative.")
        if len(dep) >= 2:
            rep.text("Product rule: (fg)' = f'g + fg' (extended to n factors by summing over which factor is differentiated).")
            for a in dep:
                rep.math(sp.Eq(sp.Derivative(a, var), sp.diff(a, var), evaluate=False))
        elif len(dep) == 1:
            rep.math(sp.Eq(sp.Derivative(dep[0], var), sp.diff(dep[0], var), evaluate=False))
    elif expr.is_Pow:
        base, ex = expr.as_base_exp()
        if not ex.has(var):
            rep.text(f"Power rule: d/d{var} [u^n] = n·u^(n−1)·u' with n = {ex}" + ("" if base == var else f" and inner function u = {base} (chain rule)."))
            if base != var:
                rep.math(sp.Eq(sp.Derivative(base, var), sp.diff(base, var), evaluate=False))
        elif not base.has(var):
            rep.text(f"Exponential rule: d/d{var} [a^u] = a^u·ln(a)·u' with a = {base}, u = {ex}.")
        else:
            rep.text("Variable base and exponent: use logarithmic differentiation, d/dx[u^v] = u^v (v' ln u + v u'/u).")
    elif isinstance(expr, sp.Function) or expr.func.__name__ in ("sin", "cos", "tan", "exp", "log"):
        inner = expr.args[0] if expr.args else var
        if inner != var:
            rep.text(f"Chain rule: d/d{var} f(u) = f'(u)·u' with outer function {expr.func.__name__} and inner function u = {inner}.")
            rep.math(sp.Eq(sp.Derivative(inner, var), sp.diff(inner, var), evaluate=False))
        else:
            rep.text(f"Standard derivative of {expr.func.__name__}({var}).")


def differentiate(expression: str, variables: str = "x", order: int = 1, point: str = "") -> Report:
    """Derivative of ``expression`` w.r.t. one or more variables.

    ``variables``: 'x' (ordinary / higher order) or 'x, y' (mixed partial: ∂/∂x then ∂/∂y).
    """
    if not isinstance(order, int) or order < 1 or order > 10:
        raise InputError("The order must be an integer between 1 and 10.")
    expr = parse_expression(expression)
    syms = parse_symbol_list(variables)
    if len(syms) > 1:
        for s in syms:
            if not expr.has(s):
                raise InputError(f"The expression does not contain the variable '{s}'.")
    partial = len(expr.free_symbols) > 1 or len(syms) > 1
    rep = Report("Differentiation — Partial derivative" if partial else "Differentiation")
    rep.heading("Original expression")
    rep.math(expr, "f = ")
    rep.heading("Operation")
    if len(syms) == 1:
        v = syms[0]
        rep.text(f"Differentiate with respect to {v}, order {order}" + (" (treating all other symbols as constants)." if partial else "."))
        rep.math(sp.Derivative(expr, (v, order)))
    else:
        args = []
        for v in syms:
            args.append((v, order))
        rep.text("Mixed partial derivative: differentiate successively with respect to " + ", ".join(
            f"{v}" + (f" ({order} times)" if order > 1 else "") for v in syms) + ".")
        rep.math(sp.Derivative(expr, *args))
    if len(syms) == 1 and order >= 1:
        rep.heading("Rules applied (first step)")
        _rule_walkthrough(expr, syms[0], rep)
    # compute
    try:
        if len(syms) == 1:
            res = sp.diff(expr, syms[0], order)
        else:
            res = sp.diff(expr, *[(v, order) for v in syms])
    except (ValueError, NotImplementedError, TypeError) as exc:
        raise ComputationError(f"Could not differentiate: {exc}")
    if len(syms) == 1 and order > 1:
        rep.heading("Successive derivatives")
        cur = expr
        for k in range(1, order + 1):
            cur = sp.diff(cur, syms[0])
            rep.math(sp.simplify(cur), f"order {k}: ")
    simp = sp.simplify(res)
    rep.heading("Result")
    rep.exact(simp, "derivative = ")
    if sp.srepr(simp) != sp.srepr(res) and sp.count_ops(res) != sp.count_ops(simp):
        rep.text("Unsimplified form:"); rep.math(res)
    rep.data["result"] = simp
    # evaluation
    if point.strip():
        subs = parse_assignments(point)
        missing = [s for s in simp.free_symbols if s not in subs]
        rep.heading("Evaluation at a point")
        rep.text("Point: " + ", ".join(f"{k} = {v}" for k, v in subs.items()))
        val = simp.subs(subs)
        if missing:
            rep.text("Still depends on: " + ", ".join(map(str, missing)))
            rep.exact(sp.simplify(val))
            rep.data["value"] = sp.simplify(val)
        else:
            if val.has(sp.zoo, sp.nan, sp.oo, -sp.oo):
                rep.warn("The derivative is undefined (or infinite) at this point.")
                rep.data["value"] = None
            else:
                val = sp.simplify(val)
                rep.exact(val, "value = ")
                if not val.is_Rational:
                    rep.approx(sp.N(val, 12), "≈ ")
                rep.data["value"] = val
    return rep


def implicit_differentiate(equation: str, x: str = "x", y: str = "y", order: int = 1, point: str = "") -> Report:
    """dy/dx (and d²y/dx²) of F(x, y) = 0 via the implicit-function theorem."""
    if order not in (1, 2):
        raise InputError("Implicit differentiation supports first and second derivatives.")
    eq = parse_equation(equation)
    xs, ys = parse_symbol(x, "independent variable"), parse_symbol(y, "dependent variable")
    if xs == ys:
        raise InputError("The independent and dependent variables must differ.")
    F = sp.expand(eq.lhs - eq.rhs)
    if not F.has(ys):
        raise InputError(f"The equation does not contain the dependent variable '{ys}'.")
    rep = Report("Differentiation — Implicit")
    rep.heading("Original equation"); rep.math(eq)
    rep.heading("Method")
    rep.text(f"Write F({xs}, {ys}) = lhs − rhs = 0 and treat {ys} as a function of {xs}. "
             f"Differentiating F({xs}, {ys}({xs})) = 0 with the chain rule gives Fₓ + F_y·dy/dx = 0, hence dy/dx = −Fₓ / F_y.")
    rep.math(F, "F = ")
    Fx, Fy = sp.diff(F, xs), sp.diff(F, ys)
    rep.math(Fx, f"F_{xs} = "); rep.math(Fy, f"F_{ys} = ")
    if sp.simplify(Fy) == 0:
        raise ComputationError(f"F_{ys} is identically 0, so dy/dx cannot be solved for.")
    dydx = sp.simplify(-Fx / Fy)
    rep.heading("Result")
    rep.exact(sp.Eq(sp.Symbol(f"d{ys}/d{xs}"), dydx, evaluate=False))
    rep.data["result"] = dydx
    final = dydx
    if order == 2:
        # d/dx(dydx) with y' substituted
        d2 = sp.diff(dydx, xs) + sp.diff(dydx, ys) * dydx
        d2 = sp.simplify(d2)
        rep.text(f"Second derivative: d²y/dx² = ∂/∂x(y') + ∂/∂y(y')·y', with y' as above.")
        rep.exact(sp.Eq(sp.Symbol(f"d²{ys}/d{xs}²"), d2, evaluate=False))
        rep.data["result2"] = d2
        final = d2
    if point.strip():
        subs = parse_assignments(point)
        rep.heading("Evaluation at a point")
        on_curve = sp.simplify(F.subs(subs))
        if on_curve != 0:
            rep.warn(f"The point does not lie on the curve (F = {on_curve} ≠ 0); the value below is the formal expression evaluated there.")
        val = sp.simplify(final.subs(subs))
        if val.has(sp.zoo, sp.nan):
            rep.warn("The derivative is undefined here (F_y = 0: vertical tangent or singular point).")
        else:
            rep.exact(val, "value = ")
            if not val.is_Rational:
                rep.approx(sp.N(val, 12), "≈ ")
        rep.data["value"] = val
    return rep


def gradient(expression: str, variables: str) -> Report:
    """Gradient vector (all first-order partials)."""
    expr = parse_expression(expression)
    syms = parse_symbol_list(variables)
    rep = Report("Differentiation — Gradient")
    rep.heading("Original expression"); rep.math(expr, "f = ")
    rep.heading("Partial derivatives")
    grads = []
    for s in syms:
        g = sp.simplify(sp.diff(expr, s)); grads.append(g)
        rep.exact(g, f"∂f/∂{s} = ")
    rep.heading("Gradient"); rep.math(sp.Matrix(grads), "∇f:")
    rep.data["result"] = grads
    return rep
