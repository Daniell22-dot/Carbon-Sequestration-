"""Forecast orchestration, backtesting, and scenario construction."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Literal

import numpy as np
import pandas as pd

from src.analysis.time_series import CarbonTimeSeriesAnalyzer, ForecastResult
from src.utils.logging import get_logger

logger = get_logger(__name__)

ForecastModel = Literal["auto", "linear", "arima"]


def forecast_series(
    series: pd.Series,
    horizon: int = 10,
    model: ForecastModel = "auto",
    confidence_level: float = 0.95,
    seasonal_period: int = 12,
) -> ForecastResult:
    """Forecast a series using the shared analyzer.

    Args:
        series: Datetime-indexed observations.
        horizon: Number of future periods.
        model: Forecast model choice.
        confidence_level: Prediction interval confidence.
        seasonal_period: Seasonal period in observations.

    Returns:
        A :class:`ForecastResult`.
    """
    analyzer = CarbonTimeSeriesAnalyzer(
        seasonal_period=seasonal_period,
        confidence_level=confidence_level,
    )
    return analyzer.forecast(series, horizon=horizon, model=model)


def _error_metrics(actual: np.ndarray, predicted: np.ndarray) -> dict[str, float]:
    mask = ~(np.isnan(actual) | np.isnan(predicted))
    actual = actual[mask]
    predicted = predicted[mask]
    if actual.size == 0:
        return {"mae": float("nan"), "rmse": float("nan"), "mape": float("nan")}
    error = actual - predicted
    mae = float(np.mean(np.abs(error)))
    rmse = float(np.sqrt(np.mean(error**2)))
    nonzero = actual != 0
    mape = (
        float(np.mean(np.abs(error[nonzero] / actual[nonzero])) * 100)
        if nonzero.any()
        else float("nan")
    )
    return {"mae": mae, "rmse": rmse, "mape": mape}


def backtest(
    series: pd.Series,
    model: ForecastModel = "linear",
    test_size: int = 12,
    seasonal_period: int = 12,
) -> dict[str, float]:
    """Backtest a forecast model on a held-out tail of the series.

    Args:
        series: Datetime-indexed observations.
        model: Forecast model choice.
        test_size: Number of final observations held out.
        seasonal_period: Seasonal period in observations.

    Returns:
        Dictionary with ``mae``, ``rmse``, and ``mape``.

    Raises:
        ValueError: If the series is too short for the requested split.
    """
    if test_size < 1:
        raise ValueError("test_size must be positive")
    if len(series) <= test_size + 3:
        raise ValueError("Series too short for the requested test_size")

    train = series.iloc[:-test_size]
    test = series.iloc[-test_size:]
    result = forecast_series(
        train,
        horizon=test_size,
        model=model,
        seasonal_period=seasonal_period,
    )
    predicted = result.mean.reindex(test.index)
    metrics = _error_metrics(
        test.to_numpy(dtype=float), predicted.to_numpy(dtype=float)
    )
    metrics["test_size"] = float(test_size)
    return metrics


def compare_forecast_methods(
    series: pd.Series,
    test_size: int = 12,
    models: Iterable[ForecastModel] = ("linear", "arima"),
    seasonal_period: int = 12,
) -> pd.DataFrame:
    """Backtest multiple forecast models and rank them by RMSE.

    Args:
        series: Datetime-indexed observations.
        test_size: Number of final observations held out.
        models: Candidate models.
        seasonal_period: Seasonal period in observations.

    Returns:
        DataFrame with one row per model and error metrics, sorted by RMSE.
    """
    records: list[dict[str, object]] = []
    for model in models:
        try:
            metrics = backtest(
                series,
                model=model,
                test_size=test_size,
                seasonal_period=seasonal_period,
            )
            records.append({"model": model, **metrics})
        except Exception as error:  # pragma: no cover - model-specific failures
            logger.warning("Backtest failed for {}: {}", model, error)
            records.append(
                {
                    "model": model,
                    "mae": float("nan"),
                    "rmse": float("nan"),
                    "mape": float("nan"),
                    "test_size": float(test_size),
                }
            )
    frame = pd.DataFrame(records)
    if not frame.empty:
        frame = frame.sort_values("rmse", na_position="last").reset_index(drop=True)
    return frame


def scenario_forecast(
    base: ForecastResult,
    adjustments: Mapping[str, float],
    annual_growth_percent: float | None = None,
    periods_per_year: int = 12,
) -> pd.DataFrame:
    """Build alternative forecast scenarios from a base forecast.

    Each scenario applies a constant multiplicative adjustment. When
    ``annual_growth_percent`` is supplied, the adjustment compounds per year.

    Args:
        base: Baseline :class:`ForecastResult`.
        adjustments: Mapping of scenario name to multiplicative factor.
        annual_growth_percent: Optional additional annual growth rate in percent.
        periods_per_year: Forecast periods per year used for compounding.

    Returns:
        Long-form DataFrame with ``date``, ``scenario``, ``forecast``,
        ``lower``, and ``upper`` columns.
    """
    records: list[dict[str, object]] = []
    horizon = len(base.mean)
    years = np.arange(horizon) / float(periods_per_year)
    means = base.mean.to_numpy(dtype=float)
    lowers = base.lower.to_numpy(dtype=float)
    uppers = base.upper.to_numpy(dtype=float)

    for scenario, factor in adjustments.items():
        growth = np.ones(horizon)
        if annual_growth_percent:
            growth = (1.0 + annual_growth_percent / 100.0) ** years
        multiplier = factor * growth
        for position, date in enumerate(base.mean.index):
            records.append(
                {
                    "date": date,
                    "scenario": scenario,
                    "forecast": float(means[position] * multiplier[position]),
                    "lower": float(lowers[position] * multiplier[position]),
                    "upper": float(uppers[position] * multiplier[position]),
                }
            )
    return pd.DataFrame(records)
