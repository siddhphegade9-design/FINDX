import pytest
import sympy as sp

from findx.core import differentiation as D
from findx.core.errors import InputError

x, y = sp.symbols("x y")


def test_first_derivative_and_point():
    r = D.differentiate("x^2*sin(x)", "x", 1, "x=0")
    assert sp.simplify(r.data["result"] - (2 * x * sp.sin(x) + x**2 * sp.cos(x))) == 0
    assert r.data["value"] == 0


def test_higher_order():
    r = D.differentiate("x^5", "x", 3)
    assert r.data["result"] == 60 * x**2


def test_partial_and_mixed():
    r = D.differentiate("x^2*y^3", "x", 1)
    assert r.data["result"] == 2 * x * y**3
    m = D.differentiate("x^2*y^3", "x, y", 1)
    assert m.data["result"] == 6 * x * y**2


def test_point_with_missing_variable_stays_symbolic():
    r = D.differentiate("x*y", "x", 1, "x=2")
    assert r.data["value"] == y


def test_undefined_at_point():
    r = D.differentiate("1/x", "x", 1, "x=0")
    assert r.data["value"] is None


def test_implicit_circle():
    r = D.implicit_differentiate("x^2+y^2=25", "x", "y", 1, "x=3, y=4")
    assert r.data["result"] == -x / y
    assert r.data["value"] == sp.Rational(-3, 4)
    r2 = D.implicit_differentiate("x^2+y^2=25", "x", "y", 2, "x=3, y=4")
    assert r2.data["value"] == sp.Rational(-25, 64)


def test_implicit_vertical_tangent_warns():
    r = D.implicit_differentiate("x^2+y^2=25", "x", "y", 1, "x=5, y=0")
    assert "undefined" in r.to_text()


def test_gradient():
    r = D.gradient("x^2+x*y+y^2", "x, y")
    assert list(r.data["result"]) == [2 * x + y, x + 2 * y]


@pytest.mark.parametrize("args", [("", "x", 1), ("x^2", "", 1), ("x^2", "x", 0), ("x^2", "x", 11), ("x^2", "1x", 1), ("x^2=1", "x", 1)])
def test_bad_inputs(args):
    with pytest.raises(InputError):
        D.differentiate(*args)


def test_implicit_missing_dependent():
    with pytest.raises(InputError):
        D.implicit_differentiate("x^2=4", "x", "y")


def test_derivative_wrt_absent_variable_is_zero():
    assert D.differentiate("x^2", "y", 1).data["result"] == 0
    with pytest.raises(InputError):
        D.differentiate("x^2", "x, y", 1)
