"""Static matplotlib figures for CO2 series, forecasts, and comparisons."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.analysis.time_series import (
    ChangePoint,
    DecompositionResult,
    ForecastResult,
)
from src.utils.logging import get_logger
from src.visualization.themes import PALETTE, save_figure, set_theme

logger = get_logger(__name__)


def _finalize(
    figure: plt.Figure,
    output_path: Path | str | None,
    formats: tuple[str, ...] = ("png",),
) -> plt.Figure:
    if output_path:
        save_figure(figure, output_path, formats=formats)
    return figure


def plot_co2_series(
    frame: pd.DataFrame,
    output_path: Path | str | None = None,
    value_column: str = "co2_ppm",
    date_column: str = "date",
    title: str = "Atmospheric CO2 Concentration",
    changepoints: list[ChangePoint] | None = None,
    theme: str = "professional",
) -> plt.Figure:
    """Plot a CO2 time series with an optional deseasonalized overlay.

    Args:
        frame: DataFrame containing date and value columns.
        output_path: Optional output path.
        value_column: CO2 column to plot.
        date_column: Datetime column.
        title: Plot title.
        changepoints: Optional change points to annotate.
        theme: Matplotlib theme name.

    Returns:
        The created figure.
    """
    set_theme(theme)
    data = frame.copy()
    data[date_column] = pd.to_datetime(data[date_column])

    figure, axis = plt.subplots(figsize=(11, 5))
    axis.plot(
        data[date_column],
        data[value_column],
        color=PALETTE["primary"],
        linewidth=1.2,
        label="Monthly mean",
    )
    if "co2_deseasonalized" in data.columns:
        axis.plot(
            data[date_column],
            data["co2_deseasonalized"],
            color=PALETTE["accent"],
            linewidth=1.4,
            label="Seasonally adjusted",
        )
    if changepoints:
        for point in changepoints:
            if point.date is not None:
                axis.axvline(point.date, color=PALETTE["danger"], linestyle="--", alpha=0.7)
                axis.annotate(
                    f"{point.direction} ({point.magnitude:+.1f})",
                    xy=(point.date, axis.get_ylim()[1]),
                    xytext=(4, -12),
                    textcoords="offset points",
                    fontsize=8,
                    color=PALETTE["danger"],
                )

    axis.set_title(title)
    axis.set_xlabel("Date")
    axis.set_ylabel("CO2 (ppm)")
    axis.legend(loc="upper left")
    figure.tight_layout()
    return _finalize(figure, output_path)


def plot_decomposition(
    result: DecompositionResult,
    output_path: Path | str | None = None,
    title: str = "Time Series Decomposition",
    theme: str = "professional",
) -> plt.Figure:
    """Plot observed, trend, seasonal, and residual components.

    Args:
        result: Decomposition output.
        output_path: Optional output path.
        title: Figure title.
        theme: Matplotlib theme name.

    Returns:
        The created figure.
    """
    set_theme(theme)
    components = [
        ("Observed", result.observed, PALETTE["primary"]),
        ("Trend", result.trend, PALETTE["secondary"]),
        ("Seasonal", result.seasonal, PALETTE["accent"]),
        ("Residual", result.residual, PALETTE["muted"]),
    ]
    figure, axes = plt.subplots(4, 1, figsize=(11, 9), sharex=True)
    for axis, (label, series, color) in zip(axes, components, strict=True):
        axis.plot(series.index, series.to_numpy(), color=color, linewidth=1.1)
        axis.set_ylabel(label)
    axes[0].set_title(f"{title} ({result.model}, period={result.period})")
    axes[-1].set_xlabel("Date")
    figure.tight_layout()
    return _finalize(figure, output_path)


def plot_forecast(
    history: pd.Series,
    forecast: ForecastResult,
    output_path: Path | str | None = None,
    title: str = "CO2 Forecast",
    history_label: str = "Observed",
    theme: str = "professional",
) -> plt.Figure:
    """Plot historical observations and a forecast with confidence bands.

    Args:
        history: Historical series.
        forecast: Forecast result.
        output_path: Optional output path.
        title: Figure title.
        history_label: Legend label for history.
        theme: Matplotlib theme name.

    Returns:
        The created figure.
    """
    set_theme(theme)
    figure, axis = plt.subplots(figsize=(11, 5))
    axis.plot(history.index, history.to_numpy(), color=PALETTE["primary"], label=history_label)
    axis.plot(
        forecast.mean.index,
        forecast.mean.to_numpy(),
        color=PALETTE["accent"],
        linewidth=2,
        label=f"Forecast ({forecast.model})",
    )
    axis.fill_between(
        forecast.mean.index,
        forecast.lower.to_numpy(),
        forecast.upper.to_numpy(),
        color=PALETTE["accent"],
        alpha=0.2,
        label=f"{int(forecast.confidence_level * 100)}% interval",
    )
    axis.set_title(title)
    axis.set_xlabel("Date")
    axis.set_ylabel("CO2 (ppm)")
    axis.legend(loc="upper left")
    figure.tight_layout()
    return _finalize(figure, output_path)


def plot_method_comparison(
    scored: pd.DataFrame,
    output_path: Path | str | None = None,
    score_column: str = "composite_score",
    title: str = "Sequestration Method Comparison",
    theme: str = "professional",
) -> plt.Figure:
    """Plot composite scores as a horizontal bar chart.

    Args:
        scored: Scored comparison table.
        output_path: Optional output path.
        score_column: Score column to plot.
        title: Figure title.
        theme: Matplotlib theme name.

    Returns:
        The created figure.
    """
    set_theme(theme)
    ordered = scored.sort_values(score_column, ascending=True)
    labels = ordered.get("display_name", ordered["method"]).astype(str)
    figure, axis = plt.subplots(figsize=(10, max(4, 0.6 * len(ordered))))
    colors = plt.cm.Blues(np.linspace(0.35, 0.9, len(ordered)))
    axis.barh(labels, ordered[score_column].to_numpy(), color=colors)
    axis.set_xlim(0, 1.05)
    axis.set_xlabel("Composite score (0-1)")
    axis.set_title(title)
    for position, value in enumerate(ordered[score_column].to_numpy()):
        axis.text(float(value) + 0.01, position, f"{float(value):.2f}", va="center", fontsize=9)
    figure.tight_layout()
    return _finalize(figure, output_path)


def plot_pareto(
    pareto: pd.DataFrame,
    output_path: Path | str | None = None,
    cost_column: str = "cost_mean",
    benefit_column: str = "composite_score",
    title: str = "Cost vs. Benefit Pareto Frontier",
    theme: str = "professional",
) -> plt.Figure:
    """Scatter methods on cost/benefit axes, highlighting Pareto-optimal points.

    Args:
        pareto: Output of :func:`src.analysis.comparison.pareto_frontier`.
        output_path: Optional output path.
        cost_column: Cost axis column.
        benefit_column: Benefit axis column.
        title: Figure title.
        theme: Matplotlib theme name.

    Returns:
        The created figure.
    """
    set_theme(theme)
    figure, axis = plt.subplots(figsize=(8, 6))
    optimal = pareto.get("pareto_optimal", pd.Series(False, index=pareto.index))
    for flag, color, label in (
        (True, PALETTE["secondary"], "Pareto optimal"),
        (False, PALETTE["muted"], "Dominated"),
    ):
        subset = pareto[optimal.astype(bool) == flag]
        if subset.empty:
            continue
        axis.scatter(
            subset[cost_column],
            subset[benefit_column],
            color=color,
            s=80,
            label=label,
        )
    for _, row in pareto.iterrows():
        axis.annotate(
            str(row.get("method", "")),
            xy=(row[cost_column], row[benefit_column]),
            xytext=(5, 5),
            textcoords="offset points",
            fontsize=9,
        )
    axis.set_xlabel("Mean cost (USD/tCO2)")
    axis.set_ylabel("Composite score")
    axis.set_title(title)
    axis.legend()
    figure.tight_layout()
    return _finalize(figure, output_path)
