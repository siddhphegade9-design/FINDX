"""Turn a ``Report`` into rich text for QTextBrowser.

Mathematics is typeset with Matplotlib's mathtext (Computer Modern fonts) and
inserted as images; if a LaTeX string cannot be parsed by mathtext the plain
unicode form is shown in a monospaced font instead, so output is never lost.
"""
from __future__ import annotations

import html
import io
from functools import lru_cache
from typing import Dict, List, Optional, Tuple

from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
from PySide6.QtGui import QImage

from .. import config as C
from ..core.report import Block, Report


@lru_cache(maxsize=512)
def _latex_png(latex: str, color: str, size: int) -> Optional[bytes]:
    try:
        fig = Figure(figsize=(0.1, 0.1), dpi=150)
        FigureCanvasAgg(fig)
        fig.text(0, 0, f"${latex}$", fontsize=size, color=color)
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=150, bbox_inches="tight", pad_inches=0.04, transparent=True)
        return buf.getvalue()
    except Exception:
        return None


def _esc(text: str) -> str:
    return html.escape(text).replace("\n", "<br>").replace("  ", "&nbsp;&nbsp;")


TAGS = {"exact": ("EXACT", C.BRONZE), "approx": ("APPROX.", C.STONE)}


def build_html(report: Report) -> Tuple[str, Dict[str, QImage]]:
    """Return (html, resources) where resources maps image names to QImages."""
    parts: List[str] = []
    images: Dict[str, QImage] = {}
    counter = 0
    parts.append(f'<h2 style="font-family:{C.SERIF_FONTS}; font-weight:normal; color:{C.CHARCOAL}; margin:0 0 2px 0;">'
                 f'{html.escape(report.title)}</h2>')
    for b in report.blocks:
        k = b.kind
        if k == "heading":
            parts.append(f'<p style="margin:18px 0 4px 0; color:{C.BRONZE}; font-size:9pt; letter-spacing:2px;"><b>{html.escape(b.text.upper())}</b></p>'
                         f'<hr style="color:{C.BORDER}; background:{C.BORDER};">')
        elif k == "text":
            parts.append(f'<p style="margin:4px 0; color:{C.CHARCOAL};">{_esc(b.text)}</p>')
        elif k == "note":
            parts.append(f'<table width="100%" cellpadding="6" style="margin:6px 0;"><tr>'
                         f'<td style="border-left:3px solid {C.STONE}; background:{C.IVORY_DARK}; color:{C.STONE};"><i>{_esc(b.text)}</i></td></tr></table>')
        elif k == "warn":
            parts.append(f'<table width="100%" cellpadding="6" style="margin:6px 0;"><tr>'
                         f'<td style="border-left:3px solid {C.BRICK}; background:#F1E3DD; color:{C.BRICK};"><b>⚠ {_esc(b.text)}</b></td></tr></table>')
        elif k == "matrix":
            label = b.text.split("\n", 1)[0] if b.text and not b.text.startswith(("⎡", "⎢", "⎣", "[", "⎛", "⎜")) else ""
            if label:
                parts.append(f'<p style="margin:6px 0 0 8px; color:{C.STONE};">{html.escape(label)}</p>')
            cell_style = f'style="font-family:{C.MONO_FONTS}; font-size:11pt;" align="center"'
            rows_html = "".join("<tr>" + "".join(f"<td {cell_style}>{html.escape(c)}</td>" for c in row) + "</tr>" for row in (b.rows or []))
            br = f"2px solid {C.CHARCOAL}"
            parts.append(f'<table cellspacing="0" cellpadding="0" style="margin:4px 0 6px 18px;"><tr>'
                         f'<td width="5" style="border-left:{br}; border-top:{br}; border-bottom:{br};"></td>'
                         f'<td><table cellspacing="0" cellpadding="5">{rows_html}</table></td>'
                         f'<td width="5" style="border-right:{br}; border-top:{br}; border-bottom:{br};"></td></tr></table>')
        elif k == "pre":
            parts.append(f'<pre style="font-family:{C.MONO_FONTS}; font-size:10pt; margin:6px 0 6px 12px; color:{C.CHARCOAL};">{html.escape(b.text)}</pre>')
        elif k in ("math", "exact", "approx"):
            png = _latex_png(b.latex, C.CHARCOAL if k != "approx" else C.STONE, 14) if b.latex and len(b.latex) < 500 else None
            tag = TAGS.get(k)
            if png is not None:
                counter += 1
                name = f"math://{counter}"
                images[name] = QImage.fromData(png, "PNG")
                body = f'<img src="{name}">'
            else:
                body = f'<span style="font-family:{C.MONO_FONTS}; font-size:11pt;">{html.escape(b.text)}</span>'
            bar = C.BRONZE if k == "exact" else (C.STONE if k == "approx" else C.BORDER)
            tag_html = (f'<span style="color:{tag[1]}; font-size:7pt; letter-spacing:1px;">{tag[0]}</span>' if tag else "")
            parts.append(f'<table cellpadding="5" style="margin:3px 0 3px 8px;"><tr>'
                         f'<td style="border-left:3px solid {bar};" width="62">{tag_html}</td><td>{body}</td></tr></table>')
    return "\n".join(parts), images
