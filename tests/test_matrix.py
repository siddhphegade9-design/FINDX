import pytest
import sympy as sp

from findx.core import matrix as M
from findx.core.errors import InputError


def mat(rows):
    return M.build_matrix([[str(v) for v in r] for r in rows])


A = mat([[2, 1], [1, 3]])
B = mat([[1, 0], [0.5, 2]])


def test_build_validation():
    with pytest.raises(InputError):
        M.build_matrix([["1", "2"], ["3"]])
    with pytest.raises(InputError):
        M.build_matrix([["1", "a"]])
    with pytest.raises(InputError):
        M.build_matrix([["1", ""]])
    with pytest.raises(InputError):
        M.build_matrix([])


def test_add_sub():
    assert M.add(A, B).data["result"] == A + B
    assert M.subtract(A, B).data["result"] == A - B


def test_mismatched_dimensions():
    C = mat([[1, 2, 3]])
    for f in (M.add, M.subtract):
        with pytest.raises(InputError):
            f(A, C)
    with pytest.raises(InputError):
        M.multiply(A, C.T.T if False else mat([[1], [2], [3]]))


def test_multiply_and_scalar():
    assert M.multiply(A, B).data["result"] == A * B
    assert M.scalar_multiply(A, "-1/2").data["result"] == A * sp.Rational(-1, 2)
    with pytest.raises(InputError):
        M.scalar_multiply(A, "x")


def test_non_square_rejections():
    R = mat([[1, 2, 3], [4, 5, 6]])
    for f in (M.determinant, M.inverse, M.trace, M.eigenvalues, M.eigenvectors):
        with pytest.raises(InputError):
            f(R)


def test_transpose_rank_trace():
    R = mat([[1, 2, 3], [4, 5, 6]])
    assert M.transpose(R).data["result"] == R.T
    assert M.rank(R).data["result"] == 2
    assert M.rank(mat([[1, 2], [2, 4]])).data["result"] == 1
    assert M.trace(A).data["result"] == 5


def test_determinant_all_sizes():
    assert M.determinant(mat([[7]])).data["result"] == 7
    assert M.determinant(A).data["result"] == 5
    C = mat([[2, 0, 1], [1, 3, 2], [1, 1, 1]])
    assert M.determinant(C).data["result"] == C.det()
    D = sp.randMatrix(4, 4, -5, 5, seed=3)
    assert M.determinant(D).data["result"] == D.det()


def test_inverse_and_singular():
    inv = M.inverse(A).data["result"]
    assert A * inv == sp.eye(2)
    r = M.inverse(mat([[1, 2], [2, 4]]))
    assert r.data["singular"] is True and "no inverse" in r.to_text()


def test_eigen():
    ev = M.eigenvalues(A).data["result"]
    assert set(ev) == {sp.Rational(5, 2) - sp.sqrt(5) / 2, sp.Rational(5, 2) + sp.sqrt(5) / 2}
    d = mat([[2, 1], [0, 2]])
    txt = M.eigenvectors(d).to_text()
    assert "defective" in txt
    c = M.eigenvalues(mat([[0, -1], [1, 0]])).data["result"]
    assert set(c) == {sp.I, -sp.I}
    for val, mult, vecs in M.eigenvectors(A).data["result"]:
        for v in vecs:
            assert sp.simplify(A * v - val * v) == sp.zeros(2, 1)


def test_linear_systems():
    r = M.solve_linear_system(mat([[2, 1, -1], [-3, -1, 2], [-2, 1, 2]]), mat([[8], [-11], [-3]]))
    assert r.data["status"] == "unique" and list(r.data["result"]) == [2, 3, -1]
    assert M.solve_linear_system(mat([[1, 1], [2, 2]]), mat([[1], [3]])).data["status"] == "none"
    assert M.solve_linear_system(mat([[1, 1], [2, 2]]), mat([[1], [2]])).data["status"] == "infinite"
    with pytest.raises(InputError):
        M.solve_linear_system(A, mat([[1], [2], [3]]))


def test_operations_table_complete():
    assert len(M.OPERATIONS) == 12
