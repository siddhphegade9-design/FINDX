import pytest
import sympy as sp

from findx.core.errors import InputError
from findx.core.parsing import (parse_assignments, parse_entry, parse_equation, parse_expression, parse_symbol)

x, y = sp.symbols("x y")


def test_implicit_multiplication_and_powers():
    assert parse_expression("2x^2+3x-5") == 2 * x**2 + 3 * x - 5
    assert parse_expression("xy + 2(x+1)") == x * y + 2 * x + 2


def test_constants_and_functions():
    assert parse_expression("e^x") == sp.exp(x)
    assert parse_expression("ln(x)") == sp.log(x)
    assert parse_expression("arcsin(x)") == sp.asin(x)
    assert parse_expression("pi") == sp.pi


def test_equation_parsing():
    eq = parse_equation("x^2 = 4")
    assert eq.lhs == x**2 and eq.rhs == 4
    assert parse_equation("x^2-4").rhs == 0


@pytest.mark.parametrize("bad", ["", "   ", "2+", "(x", "x)", "x$", "__import__('os')", "x.is_real", "lambda x: x",
                                 "import os", "x=1", "a" * 700])
def test_rejects_bad_expressions(bad):
    with pytest.raises(InputError):
        parse_expression(bad)


@pytest.mark.parametrize("bad", ["x=1=2", "x<3", "=3", "3="])
def test_rejects_bad_equations(bad):
    with pytest.raises(InputError):
        parse_equation(bad)


def test_entries_are_exact():
    assert parse_entry("0.1") == sp.Rational(1, 10)
    assert parse_entry("1/3") == sp.Rational(1, 3)
    assert parse_entry("sqrt(2)") == sp.sqrt(2)
    with pytest.raises(InputError):
        parse_entry("x")
    with pytest.raises(InputError):
        parse_entry("")


def test_symbols_and_assignments():
    assert parse_symbol("x") == x
    with pytest.raises(InputError):
        parse_symbol("1x")
    with pytest.raises(InputError):
        parse_symbol("sin")
    assert parse_assignments("x=1, y=2") == {x: 1, y: 2}
    with pytest.raises(InputError):
        parse_assignments("x")
