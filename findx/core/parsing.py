"""Safe parsing of user-typed mathematics into SymPy objects.

Security/robustness: user text is never passed to ``eval`` unchecked.  We
(1) restrict the character set, (2) forbid attribute access and dunders,
(3) forbid Python keywords, and (4) parse with a controlled namespace.
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

import sympy as sp
from sympy.parsing.sympy_parser import (
    convert_xor,
    implicit_multiplication_application,
    parse_expr,
    standard_transformations,
)

from ..config import NUM
from .errors import InputError

_ALLOWED = re.compile(r"^[0-9A-Za-z_+\-*/^().,=<>!\s]*$")
_ATTR = re.compile(r"[A-Za-z_\)]\s*\.\s*[A-Za-z_]")
_FORBIDDEN_WORDS = re.compile(
    r"\b(import|lambda|exec|eval|open|compile|globals|locals|getattr|setattr|"
    r"delattr|os|sys|subprocess|input|print|class|def|for|while|with|yield|"
    r"None|True|False|del|assert|raise|global|nonlocal|pass|try|except|is|not|in|and|or)\b"
)

_TRANSFORMS = standard_transformations + (convert_xor,) + (implicit_multiplication_application,)

# Namespace of recognised functions / constants
_FUNCS = {
    "sin": sp.sin, "cos": sp.cos, "tan": sp.tan, "cot": sp.cot, "sec": sp.sec, "csc": sp.csc,
    "asin": sp.asin, "acos": sp.acos, "atan": sp.atan, "arcsin": sp.asin, "arccos": sp.acos,
    "arctan": sp.atan, "sinh": sp.sinh, "cosh": sp.cosh, "tanh": sp.tanh,
    "asinh": sp.asinh, "acosh": sp.acosh, "atanh": sp.atanh,
    "exp": sp.exp, "ln": sp.log, "log": sp.log, "sqrt": sp.sqrt, "cbrt": sp.cbrt,
    "abs": sp.Abs, "Abs": sp.Abs, "sign": sp.sign, "floor": sp.floor, "ceil": sp.ceiling,
    "ceiling": sp.ceiling, "Heaviside": sp.Heaviside, "gamma": sp.gamma, "erf": sp.erf,
    "atan2": sp.atan2, "max": sp.Max, "min": sp.Min,
}
_CONSTS = {"pi": sp.pi, "e": sp.E, "E": sp.E, "I": sp.I, "oo": sp.oo, "inf": sp.oo}

_GLOBAL = {
    "Integer": sp.Integer, "Float": sp.Float, "Rational": sp.Rational, "Symbol": sp.Symbol,
    "Function": sp.Function, "Mul": sp.Mul, "Add": sp.Add, "Pow": sp.Pow,
}


def _check_text(text: str, what: str = "input") -> str:
    if text is None or not str(text).strip():
        raise InputError(f"The {what} is empty.")
    text = str(text).strip().replace("×", "*").replace("−", "-").replace("·", "*")
    text = text.replace("π", "pi").replace("√", "sqrt")
    if len(text) > NUM.max_input_len:
        raise InputError(f"The {what} is too long (limit {NUM.max_input_len} characters).")
    if not _ALLOWED.match(text):
        bad = sorted({c for c in text if not re.match(r"[0-9A-Za-z_+\-*/^().,=<>!\s]", c)})
        raise InputError(f"The {what} contains unsupported characters: {' '.join(bad)}")
    if "__" in text or _ATTR.search(text):
        raise InputError(f"The {what} contains unsupported syntax.")
    if _FORBIDDEN_WORDS.search(text):
        raise InputError(f"The {what} contains a reserved word that is not allowed.")
    depth = 0
    for ch in text:
        depth += (ch == "(") - (ch == ")")
        if depth < 0:
            break
    if depth != 0:
        raise InputError("Unbalanced parentheses.")
    return text


def parse_expression(text: str, extra: Optional[Dict[str, sp.Basic]] = None, what: str = "expression") -> sp.Expr:
    """Parse ``text`` into a SymPy expression (no relational operators)."""
    text = _check_text(text, what)
    if re.search(r"[<>]|[!=]=|=", text):
        raise InputError(f"The {what} must not contain '=' or comparison operators here.")
    local: Dict[str, object] = {}
    local.update(_FUNCS)
    local.update(_CONSTS)
    if extra:
        local.update(extra)
    try:
        expr = parse_expr(text, local_dict=local, global_dict=dict(_GLOBAL), transformations=_TRANSFORMS, evaluate=True)
    except RecursionError:
        raise InputError("The expression is too deeply nested.")
    except (SyntaxError, TypeError, ValueError, AttributeError, NameError, KeyError, sp.SympifyError, Exception) as exc:  # noqa: BLE001
        raise InputError(f"Could not understand the {what} '{text}': {_short(exc)}")
    if isinstance(expr, (tuple, list, dict, set)) or not isinstance(expr, sp.Basic):
        raise InputError(f"The {what} '{text}' is not a single mathematical expression.")
    if not isinstance(expr, sp.Expr):
        raise InputError(f"The {what} '{text}' is not an algebraic expression.")
    return expr


def parse_equation(text: str) -> sp.Eq:
    """Parse ``lhs = rhs``.  A bare expression is interpreted as ``expr = 0``."""
    text = _check_text(text, "equation")
    if re.search(r"[<>]|!=", text):
        raise InputError("Inequalities are not supported; use '=' for equations.")
    text = text.replace("==", "=")
    parts = text.split("=")
    if len(parts) > 2:
        raise InputError("An equation may contain only one '=' sign.")
    if len(parts) == 1:
        return sp.Eq(parse_expression(parts[0], what="equation"), 0, evaluate=False)
    lhs, rhs = parts
    if not lhs.strip() or not rhs.strip():
        raise InputError("Both sides of the equation must be non-empty.")
    return sp.Eq(parse_expression(lhs, what="left-hand side"), parse_expression(rhs, what="right-hand side"), evaluate=False)


def parse_symbol(text: str, what: str = "variable") -> sp.Symbol:
    text = (text or "").strip()
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", text):
        raise InputError(f"'{text}' is not a valid {what} name.")
    if text in _FUNCS or text in _CONSTS:
        raise InputError(f"'{text}' is reserved and cannot be used as a {what}.")
    return sp.Symbol(text)


def parse_symbol_list(text: str, what: str = "variables") -> List[sp.Symbol]:
    items = [t for t in re.split(r"[,\s;]+", (text or "").strip()) if t]
    if not items:
        raise InputError(f"Please enter at least one {what[:-1] if what.endswith('s') else what}.")
    return [parse_symbol(t, what) for t in items]


def parse_assignments(text: str) -> Dict[sp.Symbol, sp.Expr]:
    """Parse 'x=1, y=2' into a substitution dictionary."""
    out: Dict[sp.Symbol, sp.Expr] = {}
    for part in re.split(r"[;,]", text or ""):
        part = part.strip()
        if not part:
            continue
        if "=" not in part:
            raise InputError(f"'{part}' is not of the form variable=value.")
        name, val = part.split("=", 1)
        out[parse_symbol(name)] = parse_expression(val, what="value")
    return out


def parse_number(text: str, what: str = "value", allow_inf: bool = False) -> sp.Expr:
    expr = parse_expression(text, what=what)
    if expr.free_symbols:
        raise InputError(f"The {what} must be a constant, not an expression in {', '.join(map(str, expr.free_symbols))}.")
    if not allow_inf and expr.has(sp.oo, -sp.oo, sp.zoo, sp.nan):
        raise InputError(f"The {what} must be finite.")
    return expr


def parse_entry(text: str) -> sp.Expr:
    """Parse a matrix entry.  Decimals become exact rationals (0.1 -> 1/10)."""
    t = str(text).strip()
    if not t:
        raise InputError("Matrix entry is empty.")
    try:
        return sp.Rational(t)
    except (TypeError, ValueError, ZeroDivisionError):
        pass
    expr = parse_expression(t, what="matrix entry")
    if expr.free_symbols:
        raise InputError(f"Matrix entry '{t}' must be numeric (found symbols {', '.join(sorted(map(str, expr.free_symbols)))}).")
    return sp.nsimplify(expr, rational=True) if expr.has(sp.Float) else expr


def _short(exc: Exception) -> str:
    msg = str(exc).strip().splitlines()[0] if str(exc).strip() else type(exc).__name__
    return msg[:120]


def split_top_level(text: str, seps: str = ";\n") -> List[str]:
    return [p.strip() for p in re.split("[" + re.escape(seps) + "]", text) if p.strip()]


def to_float(x) -> float:
    return float(sp.N(x, NUM.numeric_digits))


def strip_function_prefix(text: str, var: str = "x") -> str:
    """'y = x^2', 'f(x)=x^2' -> 'x^2'."""
    m = re.match(rf"^\s*(?:[A-Za-z]\w*\s*\(\s*{var}\s*\)|y)\s*=\s*(.*)$", text)
    return m.group(1) if m else text
