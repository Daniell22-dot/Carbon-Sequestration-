"""Shared plotting themes and figure persistence."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402

from src.utils.io import ensure_dir  # noqa: E402

PALETTE: dict[str, str] = {
    "primary": "#1f4e79",
    "secondary": "#2e8b57",
    "accent": "#d97706",
    "danger": "#b91c1c",
    "muted": "#6b7280",
    "grid": "#d1d5db",
    "background": "#ffffff",
}

_THEMES = {
    "professional": {
        "figure.facecolor": PALETTE["background"],
        "axes.facecolor": PALETTE["background"],
        "axes.edgecolor": PALETTE["muted"],
        "axes.labelcolor": "#111827",
        "axes.grid": True,
        "grid.color": PALETTE["grid"],
        "grid.alpha": 0.6,
        "font.size": 11,
        "axes.titlesize": 14,
        "axes.titleweight": "bold",
        "legend.frameon": False,
    },
    "dark": {
        "figure.facecolor": "#111827",
        "axes.facecolor": "#111827",
        "axes.edgecolor": "#9ca3af",
        "axes.labelcolor": "#f9fafb",
        "axes.grid": True,
        "grid.color": "#374151",
        "grid.alpha": 0.7,
        "font.size": 11,
        "axes.titlesize": 14,
        "axes.titleweight": "bold",
        "text.color": "#f9fafb",
        "legend.frameon": False,
    },
}


def set_theme(name: str = "professional") -> None:
    """Apply a named matplotlib style.

    Args:
        name: Theme name, either ``"professional"`` or ``"dark"``.

    Raises:
        ValueError: If the theme is unknown.
    """
    if name not in _THEMES:
        raise ValueError(f"Unknown theme '{name}'. Choose from {', '.join(_THEMES)}")
    plt.rcParams.update(_THEMES[name])


def save_figure(
    figure: plt.Figure,
    path: Path | str,
    dpi: int = 200,
    formats: Iterable[str] = (),
    close: bool = True,
) -> list[Path]:
    """Save a figure to one or more formats.

    Args:
        figure: Matplotlib figure.
        path: Base output path. Its suffix determines the primary format.
        dpi: Raster resolution.
        formats: Additional formats to write (for example ``("svg", "pdf")``).
        close: Close the figure after saving.

    Returns:
        Paths written.
    """
    destination = Path(path)
    ensure_dir(destination.parent)
    written: list[Path] = [destination]
    figure.savefig(destination, dpi=dpi, bbox_inches="tight")

    for suffix in formats:
        extra = destination.with_suffix(f".{suffix.lstrip('.')}")
        figure.savefig(extra, dpi=dpi, bbox_inches="tight")
        written.append(extra)

    if close:
        plt.close(figure)
    return written


def add_annotation(axis: Any, text: str, **kwargs: Any) -> None:
    """Attach a caption-style annotation to an axis."""
    axis.annotate(
        text,
        xy=(0.0, -0.16),
        xycoords="axes fraction",
        fontsize=8,
        color=PALETTE["muted"],
        ha="left",
        va="top",
        **kwargs,
    )
