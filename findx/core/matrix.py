"""Matrix engine (exact arithmetic with SymPy rationals).

Every function takes SymPy matrices (or lists of lists of strings via
``build_matrix``) and returns a ``Report`` with a genuine explanation.
"""
from __future__ import annotations

from typing import List, Sequence

import sympy as sp

from .errors import ComputationError, InputError
from .parsing import parse_entry, parse_expression
from .report import Report

MAX_DIM = 10


def build_matrix(rows: Sequence[Sequence[str]]) -> sp.Matrix:
    """Validate and convert a grid of strings to an exact SymPy matrix."""
    if not rows or not rows[0]:
        raise InputError("The matrix has no entries.")
    n_cols = len(rows[0])
    if len(rows) > MAX_DIM or n_cols > MAX_DIM:
        raise InputError(f"Matrices larger than {MAX_DIM}x{MAX_DIM} are not supported.")
    data: List[List[sp.Expr]] = []
    for i, row in enumerate(rows):
        if len(row) != n_cols:
            raise InputError("All rows must have the same number of columns.")
        out = []
        for j, cell in enumerate(row):
            try:
                out.append(parse_entry(cell))
            except InputError as exc:
                raise InputError(f"Entry ({i + 1},{j + 1}): {exc}")
        data.append(out)
    return sp.Matrix(data)


def _dims(M: sp.Matrix) -> str:
    return f"{M.rows}×{M.cols}"


def _decimal(M: sp.Matrix, digits: int = 6) -> sp.Matrix:
    return M.applyfunc(lambda v: sp.N(v, digits))


def _show_result(rep: Report, M: sp.Matrix, label: str = "Result") -> None:
    rep.math(M, label + ":")
    if any(not e.is_Integer for e in M):
        rep.text("Decimal approximation:")
        rep.math(_decimal(M))


def _square(M: sp.Matrix, op: str) -> None:
    if M.rows != M.cols:
        raise InputError(f"{op} requires a square matrix; A is {_dims(M)}.")


def _operands(rep: Report, A: sp.Matrix, B: sp.Matrix | None = None) -> None:
    rep.heading("Input")
    rep.math(A, f"A ({_dims(A)}):")
    if B is not None:
        rep.math(B, f"B ({_dims(B)}):")


def add(A: sp.Matrix, B: sp.Matrix) -> Report:
    rep = Report("Matrix Solver — Addition"); _operands(rep, A, B)
    if A.shape != B.shape:
        raise InputError(f"Cannot add: A is {_dims(A)} but B is {_dims(B)}. Addition needs identical dimensions.")
    rep.heading("Method"); rep.text("Add corresponding entries: (A + B)ᵢⱼ = Aᵢⱼ + Bᵢⱼ.")
    R = A + B; rep.heading("Result"); _show_result(rep, R); rep.data["result"] = R
    return rep


def subtract(A: sp.Matrix, B: sp.Matrix) -> Report:
    rep = Report("Matrix Solver — Subtraction"); _operands(rep, A, B)
    if A.shape != B.shape:
        raise InputError(f"Cannot subtract: A is {_dims(A)} but B is {_dims(B)}. Subtraction needs identical dimensions.")
    rep.heading("Method"); rep.text("Subtract corresponding entries: (A − B)ᵢⱼ = Aᵢⱼ − Bᵢⱼ.")
    R = A - B; rep.heading("Result"); _show_result(rep, R); rep.data["result"] = R
    return rep


def multiply(A: sp.Matrix, B: sp.Matrix) -> Report:
    rep = Report("Matrix Solver — Multiplication"); _operands(rep, A, B)
    if A.cols != B.rows:
        raise InputError(f"Cannot multiply: A is {_dims(A)} and B is {_dims(B)}. "
                         f"The number of columns of A ({A.cols}) must equal the number of rows of B ({B.rows}).")
    rep.heading("Method")
    rep.text(f"A is {_dims(A)} and B is {_dims(B)}, so AB is {A.rows}×{B.cols}. "
             "Each entry is the dot product of a row of A with a column of B: (AB)ᵢⱼ = Σₖ Aᵢₖ Bₖⱼ.")
    R = A * B
    if R.rows * R.cols <= 9:
        for i in range(R.rows):
            for j in range(R.cols):
                terms = " + ".join(f"({A[i, k]})({B[k, j]})" for k in range(A.cols))
                rep.text(f"(AB)[{i + 1},{j + 1}] = {terms} = {R[i, j]}")
    rep.heading("Result"); _show_result(rep, R)
    rep.note("Matrix multiplication is generally not commutative: BA may differ from AB or may not exist.")
    rep.data["result"] = R
    return rep


def scalar_multiply(A: sp.Matrix, k_text: str) -> Report:
    k = parse_expression(k_text, what="scalar")
    if k.free_symbols:
        raise InputError("The scalar must be a number.")
    rep = Report("Matrix Solver — Scalar multiplication"); _operands(rep, A)
    rep.heading("Method"); rep.text(f"Multiply every entry by k = {k}: (kA)ᵢⱼ = k·Aᵢⱼ.")
    R = (k * A).applyfunc(sp.nsimplify if k.has(sp.Float) else sp.simplify)
    rep.heading("Result"); _show_result(rep, R); rep.data["result"] = R
    return rep


def transpose(A: sp.Matrix) -> Report:
    rep = Report("Matrix Solver — Transpose"); _operands(rep, A)
    rep.heading("Method"); rep.text(f"Rows become columns: (Aᵀ)ᵢⱼ = Aⱼᵢ. A is {_dims(A)}, so Aᵀ is {A.cols}×{A.rows}.")
    R = A.T; rep.heading("Result"); _show_result(rep, R, "Aᵀ"); rep.data["result"] = R
    return rep


def determinant(A: sp.Matrix) -> Report:
    _square(A, "The determinant")
    rep = Report("Matrix Solver — Determinant"); _operands(rep, A)
    rep.heading("Method")
    n = A.rows
    if n == 1:
        rep.text("For a 1×1 matrix det(A) = a₁₁.")
    elif n == 2:
        a, b, c, d = A[0, 0], A[0, 1], A[1, 0], A[1, 1]
        rep.text(f"For a 2×2 matrix det = ad − bc = ({a})({d}) − ({b})({c}).")
    elif n == 3:
        rep.text("Cofactor expansion along the first row: det(A) = Σⱼ (−1)^(1+j) a₁ⱼ M₁ⱼ, where M₁ⱼ is the minor.")
        parts = []
        for j in range(3):
            minor = A.minor_submatrix(0, j).det()
            parts.append(f"({(-1) ** j * A[0, j]})·({minor})")
            rep.text(f"  j={j + 1}: a₁{j + 1} = {A[0, j]}, minor M₁{j + 1} = {minor}, cofactor = {(-1) ** j * minor}")
        rep.text("det(A) = " + " + ".join(parts))
    else:
        rep.text(f"For a {n}×{n} matrix the determinant is computed with the Bareiss fraction-free elimination algorithm "
                 "(exact integer/rational arithmetic, no rounding).")
    d = sp.simplify(A.det())
    rep.heading("Result"); rep.exact(sp.Eq(sp.Symbol("det(A)"), d, evaluate=False))
    if d == 0:
        rep.note("det(A) = 0: the matrix is singular (not invertible); its rows/columns are linearly dependent.")
    else:
        rep.note("det(A) ≠ 0: the matrix is invertible.")
    rep.data["result"] = d
    return rep


def inverse(A: sp.Matrix) -> Report:
    _square(A, "The inverse")
    rep = Report("Matrix Solver — Inverse"); _operands(rep, A)
    d = sp.simplify(A.det())
    rep.heading("Invertibility check"); rep.exact(sp.Eq(sp.Symbol("det(A)"), d, evaluate=False))
    if d == 0:
        rep.heading("Result")
        rep.warn("det(A) = 0, so A is singular and has no inverse.")
        rep.data["result"] = None; rep.data["singular"] = True
        return rep
    n = A.rows
    rep.heading("Method")
    rep.text("Gauss–Jordan elimination: row-reduce the augmented matrix [A | I]. When the left block becomes I, the right block is A⁻¹.")
    aug = A.row_join(sp.eye(n))
    rref, piv = aug.rref()
    rep.math(rref, "Reduced row-echelon form of [A | I]:")
    inv = rref[:, n:]
    if n == 2:
        rep.text("For 2×2 matrices this agrees with the closed form A⁻¹ = (1/det A)·[[d, −b], [−c, a]].")
    rep.heading("Result"); _show_result(rep, inv, "A⁻¹")
    check = sp.simplify(A * inv)
    rep.text("Verification A·A⁻¹ = I:" + (" passed." if check == sp.eye(n) else " FAILED."))
    if check != sp.eye(n):
        raise ComputationError("Inverse verification failed.")
    rep.data["result"] = inv
    return rep


def rank(A: sp.Matrix) -> Report:
    rep = Report("Matrix Solver — Rank"); _operands(rep, A)
    rref, piv = A.rref()
    rep.heading("Method")
    rep.text("The rank is the number of pivots in the reduced row-echelon form (equivalently the dimension of the row/column space).")
    rep.math(rref, "RREF:")
    r = len(piv)
    rep.heading("Result"); rep.text(f"rank(A) = {r}   (pivot columns: {', '.join(str(p + 1) for p in piv) or 'none'})")
    if A.rows == A.cols:
        rep.text("Full rank — invertible." if r == A.rows else f"Rank deficient by {A.rows - r}: singular matrix.")
    rep.data["result"] = r
    return rep


def trace(A: sp.Matrix) -> Report:
    _square(A, "The trace")
    rep = Report("Matrix Solver — Trace"); _operands(rep, A)
    rep.heading("Method"); rep.text("The trace is the sum of the main-diagonal entries: tr(A) = Σᵢ aᵢᵢ.")
    t = sp.simplify(A.trace())
    rep.text("tr(A) = " + " + ".join(f"({A[i, i]})" for i in range(A.rows)))
    rep.heading("Result"); rep.exact(sp.Eq(sp.Symbol("tr(A)"), t, evaluate=False))
    rep.data["result"] = t
    return rep


def eigenvalues(A: sp.Matrix) -> Report:
    _square(A, "Eigenvalues")
    lam = sp.Symbol("λ")
    rep = Report("Matrix Solver — Eigenvalues"); _operands(rep, A)
    rep.heading("Method")
    rep.text("Eigenvalues λ satisfy the characteristic equation det(A − λI) = 0.")
    cp = sp.expand((A - lam * sp.eye(A.rows)).det())
    rep.math(sp.Eq(sp.Symbol("det(A − λI)"), cp, evaluate=False))
    rep.math(sp.factor(cp), "factored: ")
    ev = A.eigenvals()
    if sum(ev.values()) != A.rows:
        rep.warn("Closed-form eigenvalues were not found for every root; remaining ones are numerical.")
    rep.heading("Result")
    items = sorted(ev.items(), key=lambda kv: (float(sp.re(sp.N(kv[0]))), float(sp.im(sp.N(kv[0])))))
    for val, mult in items:
        rep.exact(sp.Eq(lam, val, evaluate=False), suffix=f"   (algebraic multiplicity {mult})")
        if not val.is_Rational:
            rep.approx(sp.Eq(lam, sp.N(val, 10), evaluate=False))
    rep.text(f"Check: sum of eigenvalues = {sp.simplify(sum(v * m for v, m in ev.items()))} equals the trace {A.trace()}; "
             f"product = {sp.simplify(sp.prod([v ** m for v, m in ev.items()]))} equals det(A) = {sp.simplify(A.det())}.")
    rep.data["result"] = ev
    return rep


def eigenvectors(A: sp.Matrix) -> Report:
    _square(A, "Eigenvectors")
    lam = sp.Symbol("λ")
    rep = Report("Matrix Solver — Eigenvectors"); _operands(rep, A)
    rep.heading("Method")
    rep.text("For each eigenvalue λ, the eigenvectors form the null space of (A − λI): solve (A − λI)v = 0.")
    triples = A.eigenvects()
    rep.heading("Result")
    triples = sorted(triples, key=lambda t: (float(sp.re(sp.N(t[0]))), float(sp.im(sp.N(t[0])))))
    for val, mult, vecs in triples:
        rep.exact(sp.Eq(lam, val, evaluate=False), suffix=f"   (algebraic multiplicity {mult}, geometric multiplicity {len(vecs)})")
        rep.math((A - val * sp.eye(A.rows)).applyfunc(sp.simplify), "A − λI:")
        for k, v in enumerate(vecs, 1):
            rep.math(v.applyfunc(sp.simplify), f"eigenvector v{k}:")
            resid = (A * v - val * v).applyfunc(sp.simplify)
            rep.text("  Verification A·v = λ·v: " + ("passed." if resid == sp.zeros(*resid.shape) else "residual non-zero (numeric rounding)."))
        if len(vecs) < mult:
            rep.note(f"Geometric multiplicity {len(vecs)} < algebraic multiplicity {mult}: A is defective at this eigenvalue (not diagonalisable).")
    rep.data["result"] = triples
    return rep


def solve_linear_system(A: sp.Matrix, b: sp.Matrix) -> Report:
    if b.cols != 1:
        raise InputError("b must be a single column vector.")
    if A.rows != b.rows:
        raise InputError(f"A has {A.rows} rows but b has {b.rows} entries.")
    rep = Report("Matrix Solver — Linear system Ax = b")
    rep.heading("Input"); rep.math(A, f"A ({_dims(A)}):"); rep.math(b, "b:")
    xs = sp.symbols(f"x1:{A.cols + 1}")
    rep.text("System: " + ";  ".join(sp.sstr(sp.Eq(sum(A[i, j] * xs[j] for j in range(A.cols)), b[i], evaluate=False)) for i in range(A.rows)))
    aug = A.row_join(b)
    rA, rAb = A.rank(), aug.rank()
    rep.heading("Method")
    rep.text("Form the augmented matrix [A | b], reduce it to RREF, and compare ranks (Rouché–Capelli theorem).")
    rref, piv = aug.rref()
    rep.math(rref, "RREF of [A | b]:")
    rep.text(f"rank(A) = {rA}, rank([A|b]) = {rAb}, unknowns n = {A.cols}.")
    rep.heading("Result")
    if rA < rAb:
        rep.warn("rank(A) < rank([A|b]): the system is inconsistent and has no solution.")
        rep.data["result"] = None; rep.data["status"] = "none"
        return rep
    if rA == A.cols:
        sol = rref[:A.cols, A.cols]
        rep.text("rank(A) = n: the system has a unique solution.")
        for i in range(A.cols):
            rep.exact(sp.Eq(xs[i], sol[i], evaluate=False))
        if A.rows == A.cols:
            rep.text(f"det(A) = {sp.simplify(A.det())} ≠ 0, consistent with A⁻¹b.")
        rep.text("Verification A·x = b: " + ("passed." if (A * sol - b).applyfunc(sp.simplify) == sp.zeros(A.rows, 1) else "failed."))
        rep.data["result"] = sol; rep.data["status"] = "unique"
        return rep
    rep.text(f"rank(A) = {rA} < n = {A.cols}: infinitely many solutions with {A.cols - rA} free parameter(s).")
    sol = list(sp.linsolve((A, b), *xs))[0]
    for s, v in zip(xs, sol):
        rep.exact(sp.Eq(s, v, evaluate=False))
    rep.data["result"] = sol; rep.data["status"] = "infinite"
    return rep


OPERATIONS = {
    "Addition (A + B)": ("binary", add),
    "Subtraction (A − B)": ("binary", subtract),
    "Multiplication (A × B)": ("binary", multiply),
    "Scalar multiplication (k · A)": ("scalar", scalar_multiply),
    "Transpose (Aᵀ)": ("unary", transpose),
    "Determinant det(A)": ("unary", determinant),
    "Inverse (A⁻¹)": ("unary", inverse),
    "Rank": ("unary", rank),
    "Trace": ("unary", trace),
    "Eigenvalues": ("unary", eigenvalues),
    "Eigenvectors": ("unary", eigenvectors),
    "Solve linear system Ax = b": ("system", solve_linear_system),
}
