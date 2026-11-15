"""Structured result container produced by every engine.

Engines never format HTML; they emit a ``Report`` made of typed blocks and the
GUI decides how to render them.  ``to_text`` gives a plain-text rendering that
is used by the tests and by the "copy result" button.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional

import sympy as sp


@dataclass
class Block:
    kind: str                      # heading | text | math | pre | note | warn | exact | approx
    text: str = ""                 # plain / unicode representation
    latex: Optional[str] = None    # optional LaTeX for math rendering
    rows: Optional[List[List[str]]] = None   # matrix entries (kind == "matrix")


def _plain(v) -> str:
    """Readable single-line form of a number/expression for matrix cells."""
    t = sp.sstr(v).replace("**", "^").replace("sqrt(", "√(").replace("*", "·").replace("pi", "π")
    return t.replace("I", "i") if v.has(sp.I) else t


@dataclass
class Report:
    title: str
    blocks: List[Block] = field(default_factory=list)
    data: dict = field(default_factory=dict)   # machine-readable results (used by tests/GUI)

    # -- builders ---------------------------------------------------------
    def heading(self, text: str) -> "Report":
        self.blocks.append(Block("heading", text)); return self

    def text(self, text: str) -> "Report":
        self.blocks.append(Block("text", text)); return self

    def note(self, text: str) -> "Report":
        self.blocks.append(Block("note", text)); return self

    def warn(self, text: str) -> "Report":
        self.blocks.append(Block("warn", text)); return self

    def pre(self, text: str) -> "Report":
        self.blocks.append(Block("pre", text)); return self

    def math(self, obj: Any, label: str = "", kind: str = "math", suffix: str = "") -> "Report":
        """Add a mathematical object (SymPy expression/relational/matrix or str)."""
        if isinstance(obj, str):
            self.blocks.append(Block(kind, (label + obj), None)); return self
        if isinstance(obj, sp.MatrixBase):
            cells = [[_plain(obj[i, j]) for j in range(obj.cols)] for i in range(obj.rows)]
            self.blocks.append(Block("matrix", label + ("\n" if label else "") + sp.pretty(obj, use_unicode=True), None, cells))
            return self
        txt = label + sp.sstr(obj) + suffix
        try:
            ltx = sp.latex(obj).replace(r"\limits", "")
        except Exception:  # pragma: no cover - defensive
            ltx = None
        if label and ltx is not None:
            ltx = r"\mathrm{" + label.strip().replace(" ", r"\ ").replace("_", r"\_") + r"}\ " + ltx
        if suffix and ltx is not None:
            ltx += r"\quad\mathrm{" + suffix.strip().replace(" ", r"\ ").replace("_", r"\_") + "}"
        self.blocks.append(Block(kind, txt, ltx))
        return self

    def exact(self, obj: Any, label: str = "", suffix: str = "") -> "Report":
        return self.math(obj, label, kind="exact", suffix=suffix)

    def approx(self, obj: Any, label: str = "", suffix: str = "") -> "Report":
        return self.math(obj, label, kind="approx", suffix=suffix)

    # -- output -----------------------------------------------------------
    def to_text(self) -> str:
        out = [self.title, "=" * len(self.title)]
        for b in self.blocks:
            if b.kind == "heading":
                out += ["", b.text.upper()]
            elif b.kind == "note":
                out.append("Note: " + b.text)
            elif b.kind == "warn":
                out.append("Warning: " + b.text)
            elif b.kind == "exact":
                out.append("[exact] " + b.text)
            elif b.kind == "approx":
                out.append("[approx] " + b.text)
            else:
                out.append(b.text)
        return "\n".join(out)
