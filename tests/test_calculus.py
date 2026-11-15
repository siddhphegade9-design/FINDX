import math

import pytest
import sympy as sp

from findx.core import calculus as K
from findx.core.errors import InputError

x = sp.Symbol("x")


def test_indefinite_has_constant():
    r = K.integrate_indefinite("x*exp(x)")
    assert sp.simplify(r.data["result"] - (x - 1) * sp.exp(x)) == 0
    assert "C" in r.to_text()


def test_indefinite_polynomial_and_trig():
    assert K.integrate_indefinite("3x^2+2x").data["result"] == x**3 + x**2
    assert sp.simplify(K.integrate_indefinite("cos(x)").data["result"] - sp.sin(x)) == 0


def test_non_elementary_reports_special_function_or_warns():
    r = K.integrate_indefinite("exp(-x^2)")
    assert r.data["result"] is not None  # erf


def test_definite_exact():
    assert K.integrate_definite("sin(x)", "0", "pi").data["result"] == 2
    assert K.integrate_definite("x^2", "0", "3").data["result"] == 9


def test_definite_improper_gaussian():
    assert K.integrate_definite("exp(-x^2)", "-oo", "oo").data["result"] == sp.sqrt(sp.pi)


def test_definite_numeric_cross_check_value():
    r = K.integrate_definite("sin(x^2)*cos(x)", "0", "3")
    assert abs(float(sp.N(r.data["result"])) - 0.301297712959) < 1e-9


def test_divergent_and_singular():
    r = K.integrate_definite("1/x^2", "-1", "1")
    assert "diverges" in r.to_text()


def test_equal_limits_zero():
    assert K.integrate_definite("x", "2", "2").data["result"] == 0


def test_limits():
    assert K.limit("sin(x)/x", "0").data["result"] == 1
    assert K.limit("(1+1/x)^x", "oo").data["result"] == sp.E
    assert K.limit("1/x", "0", "+").data["result"] == sp.oo
    assert K.limit("1/x", "0", "-").data["result"] == -sp.oo
    two = K.limit("1/x", "0")
    assert two.data["result"] is None and "does not exist" in two.to_text()
    assert K.limit("abs(x)/x", "0").data["result"] is None
    assert K.limit("(x^2-1)/(x-1)", "1").data["result"] == 2


@pytest.mark.parametrize("call", [lambda: K.integrate_definite("x", "a", "1"), lambda: K.limit("x", "0", "up"),
                                  lambda: K.integrate_indefinite(""), lambda: K.limit("x", "")])
def test_invalid(call):
    with pytest.raises(InputError):
        call()
