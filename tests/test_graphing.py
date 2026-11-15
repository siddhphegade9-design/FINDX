import numpy as np
import pytest

from findx.core import graphing as G
from findx.core.errors import InputError


def roots(text, a=-5, b=5):
    return G.find_roots(G.compile_function(text), a, b)


def test_prefixes_and_errors():
    assert G.compile_function("y = x^2").expr == G.compile_function("x^2").expr
    assert G.compile_function("f(x)=x^2").expr == G.compile_function("x^2").expr
    for bad in ["", "x+y", "sin(", "x=1"]:
        with pytest.raises(InputError):
            G.compile_function(bad)


def test_roots_polynomial():
    np.testing.assert_allclose(roots("x^2-4"), [-2, 2], atol=1e-9)
    np.testing.assert_allclose(roots("x^3-6x^2+11x-6", -1, 5), [1, 2, 3], atol=1e-9)


def test_tangential_double_root():
    np.testing.assert_allclose(roots("(x-1)^2"), [1.0], atol=1e-5)


def test_trig_roots():
    np.testing.assert_allclose(roots("sin(x)", -7, 7), [-2 * np.pi, -np.pi, 0, np.pi, 2 * np.pi], atol=1e-9)


def test_poles_are_not_roots():
    assert roots("1/x") == []
    r = roots("tan(x)", -1.4, 1.4)
    np.testing.assert_allclose(r, [0], atol=1e-9)


def test_intersections():
    a, b = G.compile_function("x^2-4"), G.compile_function("x+2")
    pts = G.find_intersections(a, b, -5, 5)
    np.testing.assert_allclose(sorted(pts), [(-2, 0), (3, 5)], atol=1e-8)


def test_analyse_multiple_curves():
    cs = [G.compile_function(t) for t in ["x^2", "x", "2-x"]]
    res = G.analyse(cs, -3, 3)
    assert len(res.roots) == 3 and res.roots[0] == pytest.approx([0.0], abs=1e-5)
    pairs = {p.curves for p in res.intersections}
    assert pairs == {(0, 1), (0, 2), (1, 2)}
    text = G.format_analysis(cs, res)
    assert "Intersections" in text and "Limitations" in text


def test_discontinuity_is_broken():
    c = G.compile_function("tan(x)")
    xs, ys = G.sample_curve(c, -5, 5)
    assert np.isnan(ys).sum() >= 3
    inv = G.compile_function("1/x")
    _, ys = G.sample_curve(inv, -5, 5)
    # no segment connects the two branches: finite neighbours never straddle the pole with a huge jump
    finite = np.isfinite(ys)
    jumps = np.abs(np.diff(ys))[finite[:-1] & finite[1:]]
    assert jumps.max() < 1e3


def test_steep_continuous_curve_not_broken():
    _, ys = G.sample_curve(G.compile_function("x^9"), -2, 2)
    assert np.isnan(ys).sum() == 0


def test_domain_edges_are_nan_not_errors():
    _, ys = G.sample_curve(G.compile_function("sqrt(x)"), -4, 4)
    assert np.isnan(ys[:1000]).all() and np.isfinite(ys[-1000:]).all()
    _, ys = G.sample_curve(G.compile_function("ln(x)"), -1, 3)
    assert np.isnan(ys[0])


def test_bad_range():
    with pytest.raises(InputError):
        G.sample_curve(G.compile_function("x"), 3, 1)


def test_auto_y_range_finite():
    lo, hi = G.auto_y_range([G.compile_function("1/x"), G.compile_function("x")], -5, 5)
    assert np.isfinite(lo) and np.isfinite(hi) and lo < hi
