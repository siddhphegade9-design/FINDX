import pytest
import sympy as sp

from findx.core import algebra
from findx.core.errors import InputError

x = sp.Symbol("x")


def sols(text, var=None):
    return algebra.solve_equation(text, var).data["solutions"]


def test_linear():
    assert sols("3x+7=22") == [5]


def test_quadratic_real_distinct():
    assert set(sols("x^2-5x+6=0")) == {2, 3}


def test_quadratic_repeated_root_multiplicity():
    rep = algebra.solve_equation("x^2-4x+4=0")
    assert rep.data["multiplicities"] == {"2": 2}


def test_quadratic_complex_roots():
    s = sols("x^2+2x+5=0")
    assert set(s) == {-1 + 2 * sp.I, -1 - 2 * sp.I}


def test_cubic_rational_roots():
    assert set(sols("x^3-6x^2+11x-6=0")) == {1, 2, 3}


def test_cubic_irrational_exact_and_verified():
    rep = algebra.solve_equation("x^3-2=0")
    assert len(rep.data["solutions"]) == 3
    assert rep.data["max_residual"] < 1e-12


def test_quartic():
    assert set(sols("x^4-1=0")) == {1, -1, sp.I, -sp.I}


def test_quintic_numeric_flagged():
    rep = algebra.solve_equation("x^5-x-1=0")
    assert rep.data.get("numerical_roots") is True
    real = [complex(r).real for r in rep.data["solutions"] if abs(complex(r).imag) < 1e-9]
    assert real and abs(real[0] - 1.1673039782614187) < 1e-9
    assert rep.data["max_residual"] < 1e-9


def test_higher_degree_with_multiplicity():
    rep = algebra.solve_equation("(x-2)^3*(x+1)=0")
    assert rep.data["multiplicities"]["2"] == 3 and rep.data["multiplicities"]["-1"] == 1


def test_trig_symbolic_and_numeric_fallback():
    assert sp.pi / 6 in sols("sin(x)=1/2")
    r = algebra.solve_equation("cos(x)=x")
    assert abs(float(r.data["solutions"][0]) - 0.7390851332151607) < 1e-9


def test_parametric():
    s = sols("a*x^2+b*x+c=0", "x")
    assert len(s) == 2


def test_identity_and_contradiction():
    assert algebra.solve_equation("x+1=x+1").data["solutions"] == "all"
    assert algebra.solve_equation("2=3").data["solutions"] == []


def test_system_linear_unique():
    r = algebra.solve_equation("x+y=3; x-y=1")
    assert r.data["solutions"][0] == {sp.Symbol("x"): 2, sp.Symbol("y"): 1}


def test_system_inconsistent_and_infinite():
    assert algebra.solve_system(["x+y=1", "x+y=2"]).data["solutions"] == []
    r = algebra.solve_system(["x+y=1", "2x+2y=2"])
    assert "infinitely many" in r.to_text()


def test_system_nonlinear():
    r = algebra.solve_system(["x^2+y^2=25", "x-y=1"])
    pts = {(d[sp.Symbol("x")], d[sp.Symbol("y")]) for d in r.data["solutions"]}
    assert pts == {(4, 3), (-3, -4)}


def test_factor():
    r = algebra.factor_polynomial("x^4-1")
    assert sp.expand(r.data["factored"] - (x**4 - 1)) == 0
    assert "(x**2 + 1)" in r.to_text()


def test_extraneous_root_rejected():
    r = algebra.solve_equation("sqrt(x)=x-2")
    assert r.data["solutions"] == [4]


@pytest.mark.parametrize("bad", ["", "x^2+=3", "x<3", "x=1=2"])
def test_invalid_inputs(bad):
    with pytest.raises(InputError):
        algebra.solve_equation(bad)


def test_wrong_variable():
    with pytest.raises(InputError):
        algebra.solve_equation("x^2=4", "y")
