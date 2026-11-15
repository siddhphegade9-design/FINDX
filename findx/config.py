"""Application-wide configuration: palette, fonts, numerical tolerances."""
from __future__ import annotations

from dataclasses import dataclass

from . import APP_NAME, __version__

# --- Design palette (warm academic / scientific) -------------------------
IVORY = "#F4F1EA"
IVORY_DARK = "#EAE5DA"
PAPER = "#FBF9F4"
CHARCOAL = "#252723"
STONE = "#77766D"
BORDER = "#CFC9BB"
BRONZE = "#A47754"
BRONZE_DARK = "#86603F"
BRICK = "#9A4A3A"
OLIVE = "#6B7048"
OCHRE = "#B8923A"

#: Curve colours for the graphing engine (deliberately no blue/purple/cyan).
CURVE_COLOURS = [BRONZE, CHARCOAL, OLIVE, BRICK, OCHRE, "#6E4B3A", "#4F5D45", STONE]

SERIF_FONTS = "Georgia, Cambria, 'Times New Roman', serif"
SANS_FONTS = "'Segoe UI', 'Helvetica Neue', Arial, sans-serif"
MONO_FONTS = "Consolas, 'Cascadia Mono', 'DejaVu Sans Mono', monospace"


@dataclass(frozen=True)
class Numerics:
    """Numerical tolerances used across the engines (documented in the report)."""

    root_xtol: float = 1e-12       # bracketing tolerance for brentq
    root_ftol: float = 1e-7        # |f(root)| must be below this to be accepted
    dedupe_tol: float = 1e-6       # roots closer than this are merged
    plot_samples: int = 4000       # samples per curve
    jump_factor: float = 8.0       # discontinuity detection factor
    max_input_len: int = 600
    numeric_digits: int = 12


NUM = Numerics()

WINDOW_TITLE = f"{APP_NAME} {__version__} - Mathematical Computing"
