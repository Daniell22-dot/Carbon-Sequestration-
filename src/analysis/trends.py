"""Trend detection: Mann-Kendall, Sen's slope, and linear regression."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats

from src.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class MannKendallResult:
    """Result of a Mann-Kendall trend test."""

    trend: str
    statistic: float
    z_score: float
    p_value: float
    kendall_tau: float
    sen_slope_per_year: float
    significant: bool


@dataclass(frozen=True)
class LinearTrendResult:
    """Ordinary least squares trend result."""

    slope_per_period: float
    slope_per_year: float
    intercept: float
    r_squared: float
    p_value: float
    stderr: float
    significant: bool


def _clean(series: pd.Series) -> np.ndarray:
    values = pd.to_numeric(series, errors="coerce").dropna().to_numpy(dtype=float)
    if values.size < 3:
        raise ValueError("At least three non-missing observations are required")
    return values


def mann_kendall(series: pd.Series, periods_per_year: int = 12) -> MannKendallResult:
    """Run the non-parametric Mann-Kendall trend test.

    Args:
        series: Observations ordered in time.
        periods_per_year: Used to express Sen's slope on an annual basis.

    Returns:
        A :class:`MannKendallResult`.

    Raises:
        ValueError: If fewer than three observations are available.
    """
    values = _clean(series)
    n = values.size

    signs = np.sign(values[None, :] - values[:, None])
    upper = np.triu_indices(n, k=1)
    statistic = float(np.sum(signs[upper]))

    unique, counts = np.unique(values, return_counts=True)
    tie_correction = float(np.sum(counts * (counts - 1) * (2 * counts + 5)))
    variance = (n * (n - 1) * (2 * n + 5) - tie_correction) / 18.0

    if variance <= 0:
        z_score = 0.0
        p_value = 1.0
    else:
        if statistic > 0:
            z_score = (statistic - 1) / np.sqrt(variance)
        elif statistic < 0:
            z_score = (statistic + 1) / np.sqrt(variance)
        else:
            z_score = 0.0
        p_value = float(2 * (1 - stats.norm.cdf(abs(z_score))))

    denominator = n * (n - 1) / 2.0
    tau = statistic / denominator if denominator else 0.0
    slope = sen_slope(series, periods_per_year=periods_per_year)

    if p_value < 0.05 and statistic > 0:
        trend = "increasing"
    elif p_value < 0.05 and statistic < 0:
        trend = "decreasing"
    else:
        trend = "no trend"

    return MannKendallResult(
        trend=trend,
        statistic=statistic,
        z_score=float(z_score),
        p_value=p_value,
        kendall_tau=float(tau),
        sen_slope_per_year=float(slope),
        significant=bool(p_value < 0.05),
    )


def sen_slope(series: pd.Series, periods_per_year: int = 12) -> float:
    """Estimate Theil-Sen slope per year.

    Args:
        series: Observations ordered in time.
        periods_per_year: Observations per year.

    Returns:
        Median pairwise slope scaled to a per-year basis.
    """
    values = pd.to_numeric(series, errors="coerce").dropna().to_numpy(dtype=float)
    n = values.size
    if n < 2:
        raise ValueError("At least two observations are required")
    slopes: list[float] = []
    for i in range(n - 1):
        for j in range(i + 1, n):
            slopes.append((values[j] - values[i]) / (j - i))
    return float(np.median(slopes) * periods_per_year)


def linear_trend(
    series: pd.Series,
    periods_per_year: int = 12,
) -> LinearTrendResult:
    """Fit an ordinary least squares trend.

    Args:
        series: Observations ordered in time.
        periods_per_year: Observations per year.

    Returns:
        A :class:`LinearTrendResult`.

    Raises:
        ValueError: If fewer than three observations are available.
    """
    values = _clean(series)
    x = np.arange(values.size, dtype=float)
    result = stats.linregress(x, values)
    return LinearTrendResult(
        slope_per_period=float(result.slope),
        slope_per_year=float(result.slope * periods_per_year),
        intercept=float(result.intercept),
        r_squared=float(result.rvalue**2),
        p_value=float(result.pvalue),
        stderr=float(result.stderr),
        significant=bool(result.pvalue < 0.05),
    )


def rolling_trend(
    series: pd.Series,
    window: int = 60,
    periods_per_year: int = 12,
) -> pd.Series:
    """Compute a rolling OLS slope expressed per year.

    Args:
        series: Datetime-indexed observations.
        window: Rolling window length in observations.
        periods_per_year: Observations per year.

    Returns:
        Series of rolling slopes aligned to the right edge of each window.

    Raises:
        ValueError: If ``window`` exceeds the series length.
    """
    if window > len(series):
        raise ValueError("window cannot exceed the series length")

    def _slope(values: np.ndarray) -> float:
        if np.isnan(values).any():
            return float("nan")
        x = np.arange(values.size, dtype=float)
        return float(stats.linregress(x, values).slope * periods_per_year)

    return series.rolling(window=window, min_periods=window).apply(_slope, raw=True)


def summarize_trend(
    series: pd.Series,
    periods_per_year: int = 12,
) -> dict[str, object]:
    """Combine Mann-Kendall and OLS results into a serializable summary.

    Args:
        series: Observations ordered in time.
        periods_per_year: Observations per year.

    Returns:
        Dictionary of trend statistics.
    """
    mk = mann_kendall(series, periods_per_year=periods_per_year)
    ols = linear_trend(series, periods_per_year=periods_per_year)
    return {
        "mann_kendall_trend": mk.trend,
        "mann_kendall_pvalue": mk.p_value,
        "mann_kendall_tau": mk.kendall_tau,
        "sen_slope_per_year": mk.sen_slope_per_year,
        "ols_slope_per_year": ols.slope_per_year,
        "ols_r_squared": ols.r_squared,
        "ols_pvalue": ols.p_value,
        "significant": mk.significant,
    }
