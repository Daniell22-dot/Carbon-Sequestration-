"""Interactive Plotly figures (optional dependency)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from src.analysis.time_series import ForecastResult
from src.utils.io import ensure_dir
from src.utils.logging import get_logger

logger = get_logger(__name__)


def _require_plotly() -> Any:
    try:
        import plotly.graph_objects as go
    except ImportError as error:  # pragma: no cover - depends on environment
        raise ImportError(
            "plotly is required for interactive figures; install with "
            "'pip install plotly'"
        ) from error
    return go


def co2_figure(
    frame: pd.DataFrame,
    date_column: str = "date",
    value_column: str = "co2_ppm",
    title: str = "Atmospheric CO2 Concentration",
) -> Any:
    """Create an interactive CO2 line chart.

    Args:
        frame: DataFrame with date and value columns.
        date_column: Datetime column name.
        value_column: Value column name.
        title: Chart title.

    Returns:
        A ``plotly.graph_objects.Figure``.

    Raises:
        ImportError: If plotly is not installed.
    """
    go = _require_plotly()
    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=frame[date_column],
            y=frame[value_column],
            mode="lines",
            name="CO2",
        )
    )
    figure.update_layout(
        title=title,
        xaxis_title="Date",
        yaxis_title="CO2 (ppm)",
        template="plotly_white",
    )
    return figure


def forecast_figure(
    history: pd.Series,
    forecast: ForecastResult,
    title: str = "CO2 Forecast",
) -> Any:
    """Create an interactive forecast chart with a confidence band.

    Args:
        history: Historical series.
        forecast: Forecast result.
        title: Chart title.

    Returns:
        A ``plotly.graph_objects.Figure``.

    Raises:
        ImportError: If plotly is not installed.
    """
    go = _require_plotly()
    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=history.index,
            y=history.to_numpy(),
            mode="lines",
            name="Observed",
        )
    )
    figure.add_trace(
        go.Scatter(
            x=forecast.mean.index,
            y=forecast.upper.to_numpy(),
            mode="lines",
            line={"width": 0},
            showlegend=False,
            hoverinfo="skip",
        )
    )
    figure.add_trace(
        go.Scatter(
            x=forecast.mean.index,
            y=forecast.lower.to_numpy(),
            mode="lines",
            line={"width": 0},
            fill="tonexty",
            fillcolor="rgba(217, 119, 6, 0.2)",
            name=f"{int(forecast.confidence_level * 100)}% interval",
        )
    )
    figure.add_trace(
        go.Scatter(
            x=forecast.mean.index,
            y=forecast.mean.to_numpy(),
            mode="lines",
            name="Forecast",
        )
    )
    figure.update_layout(
        title=title,
        xaxis_title="Date",
        yaxis_title="CO2 (ppm)",
        template="plotly_white",
    )
    return figure


def save_interactive(
    figure: Any,
    path: Path | str,
    include_plotlyjs: str = "cdn",
) -> Path:
    """Write a Plotly figure to standalone HTML.

    Args:
        figure: Plotly figure.
        path: Destination HTML path.
        include_plotlyjs: Plotly.js inclusion mode.

    Returns:
        The destination path.
    """
    destination = Path(path)
    ensure_dir(destination.parent)
    figure.write_html(str(destination), include_plotlyjs=include_plotlyjs)
    return destination


def save_png(figure: Any, path: Path | str) -> Path | None:
    """Attempt to export a Plotly figure to PNG.

    Args:
        figure: Plotly figure.
        path: Destination path.

    Returns:
        The destination path, or ``None`` when the Kaleido exporter is absent.
    """
    destination = Path(path)
    ensure_dir(destination.parent)
    try:
        figure.write_image(str(destination))
    except (ValueError, ImportError) as error:  # pragma: no cover
        logger.warning("Plotly PNG export unavailable: {}", error)
        return None
    return destination
