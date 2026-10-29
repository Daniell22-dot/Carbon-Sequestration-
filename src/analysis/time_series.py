"""Time series analysis for atmospheric CO2 and sequestration data.

The analyzer prefers :mod:`statsmodels` when installed and falls back to
deterministic numpy/pandas implementations so that core analytics remain
available in constrained environments. Fallbacks are logged explicitly.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from typing import Literal

import numpy as np
import pandas as pd
from scipy import stats

from src.utils.helpers import calculate_cagr
from src.utils.logging import get_logger

logger = get_logger(__name__)

try:  # pragma: no cover - import availability depends on environment
    from statsmodels.tsa.seasonal import seasonal_decompose as _seasonal_decompose
    from statsmodels.tsa.statespace.sarimax import SARIMAX as _SARIMAX
    from statsmodels.tsa.stattools import adfuller as _adfuller
    from statsmodels.tsa.stattools import kpss as _kpss

    _STATSMODELS_AVAILABLE = True
except ImportError:  # pragma: no cover
    _seasonal_decompose = None
    _adfuller = None
    _kpss = None
    _SARIMAX = None
    _STATSMODELS_AVAILABLE = False

DecompositionModel = Literal["additive", "multiplicative"]
ForecastModel = Literal["auto", "linear", "arima"]


@dataclass(frozen=True)
class DecompositionResult:
    """Trend, seasonal, and residual components of a series."""

    observed: pd.Series
    trend: pd.Series
    seasonal: pd.Series
    residual: pd.Series
    model: str
    period: int

    def to_frame(self) -> pd.DataFrame:
        """Return all components as a single DataFrame."""
        return pd.DataFrame(
            {
                "observed": self.observed,
                "trend": self.trend,
                "seasonal": self.seasonal,
                "residual": self.residual,
            }
        )


@dataclass(frozen=True)
class ChangePoint:
    """A detected mean shift in a time series."""

    position: int
    date: pd.Timestamp | None
    mean_before: float
    mean_after: float
    magnitude: float
    statistic: float

    @property
    def direction(self) -> str:
        """Return ``"increase"`` or ``"decrease"``."""
        return "increase" if self.magnitude >= 0 else "decrease"


@dataclass(frozen=True)
class GrowthResult:
    """Growth metrics for a time series."""

    yoy_percent: pd.Series
    cagr_percent: float
    acceleration_percent: float
    start_value: float
    end_value: float
    years: float


@dataclass(frozen=True)
class ForecastResult:
    """Point forecasts with prediction intervals."""

    mean: pd.Series
    lower: pd.Series
    upper: pd.Series
    horizon: int
    model: str
    confidence_level: float
    diagnostics: dict[str, float] = field(default_factory=dict)

    def to_frame(self) -> pd.DataFrame:
        """Return forecasts as a tidy DataFrame."""
        return pd.DataFrame(
            {
                "forecast": self.mean,
                "lower": self.lower,
                "upper": self.upper,
            }
        )


@dataclass(frozen=True)
class StationarityResult:
    """ADF and KPSS stationarity test outcomes."""

    adf_statistic: float
    adf_pvalue: float
    kpss_statistic: float
    kpss_pvalue: float
    stationary: bool
    interpretation: str


def _as_series(series: pd.Series, name: str = "value") -> pd.Series:
    if not isinstance(series, pd.Series):
        raise TypeError("Expected a pandas Series")
    if not isinstance(series.index, pd.DatetimeIndex):
        raise ValueError("Series must have a DatetimeIndex")
    prepared = series.astype(float).sort_index()
    prepared = prepared[~prepared.index.duplicated(keep="last")]
    if prepared.isna().any():
        prepared = prepared.interpolate(method="linear").bfill().ffill()
    prepared.name = series.name or name
    return prepared


def _infer_frequency(index: pd.DatetimeIndex) -> str:
    if len(index) < 3:
        return "MS"
    inferred = pd.infer_freq(index)
    if inferred:
        return inferred
    median_days = float(np.median(np.diff(index.values).astype("timedelta64[D]").astype(int)))
    if median_days <= 2:
        return "D"
    if median_days <= 9:
        return "W"
    if median_days <= 45:
        return "MS"
    if median_days <= 120:
        return "QS"
    return "YS"


class CarbonTimeSeriesAnalyzer:
    """Analyze CO2 and sequestration time series.

    Args:
        seasonal_period: Observations per seasonal cycle (12 for monthly data).
        confidence_level: Confidence level for forecast intervals.
        changepoint_threshold: Minimum absolute t-statistic for a mean shift.
        max_changepoints: Safety cap on detected change points.

    Example:
        >>> analyzer = CarbonTimeSeriesAnalyzer(seasonal_period=12)
        >>> result = analyzer.calculate_growth_rates(series)  # doctest: +SKIP
    """

    def __init__(
        self,
        seasonal_period: int = 12,
        confidence_level: float = 0.95,
        changepoint_threshold: float = 3.0,
        max_changepoints: int = 10,
    ) -> None:
        if seasonal_period < 2:
            raise ValueError("seasonal_period must be at least 2")
        if not 0 < confidence_level < 1:
            raise ValueError("confidence_level must be between 0 and 1")
        self.seasonal_period = seasonal_period
        self.confidence_level = confidence_level
        self.changepoint_threshold = changepoint_threshold
        self.max_changepoints = max_changepoints

    def decompose(
        self,
        series: pd.Series,
        model: DecompositionModel = "additive",
        period: int | None = None,
    ) -> DecompositionResult:
        """Decompose a series into trend, seasonal, and residual components.

        Args:
            series: Datetime-indexed observations.
            model: ``"additive"`` or ``"multiplicative"``.
            period: Seasonal period; defaults to the analyzer setting.

        Returns:
            A :class:`DecompositionResult`.

        Raises:
            ValueError: If the series is too short for the requested period.
        """
        prepared = _as_series(series)
        resolved_period = period or self.seasonal_period
        if len(prepared) < 2 * resolved_period:
            raise ValueError(
                f"Need at least {2 * resolved_period} observations for period "
                f"{resolved_period}; received {len(prepared)}"
            )

        if _STATSMODELS_AVAILABLE:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                decomposition = _seasonal_decompose(
                    prepared,
                    model=model,
                    period=resolved_period,
                    extrapolate_trend="freq",
                )
            return DecompositionResult(
                observed=prepared,
                trend=decomposition.trend,
                seasonal=decomposition.seasonal,
                residual=decomposition.resid,
                model=model,
                period=resolved_period,
            )

        logger.warning("statsmodels unavailable; using moving-average decomposition")
        if model == "multiplicative":
            raise ValueError(
                "Multiplicative decomposition requires statsmodels; use additive"
            )
        trend = prepared.rolling(
            resolved_period, center=True, min_periods=1
        ).mean()
        detrended = prepared - trend
        seasonal = detrended.groupby(detrended.index.month).transform("mean")
        residual = prepared - trend - seasonal
        return DecompositionResult(
            observed=prepared,
            trend=trend,
            seasonal=seasonal,
            residual=residual,
            model=model,
            period=resolved_period,
        )

    def detect_changepoints(
        self,
        series: pd.Series,
        threshold: float | None = None,
        min_segment: int = 6,
    ) -> list[ChangePoint]:
        """Detect mean shifts using binary segmentation.

        Each candidate split is scored with a Welch-style t-statistic comparing
        the means of the segments on either side.

        Args:
            series: Datetime-indexed observations.
            threshold: Minimum absolute t-statistic. Defaults to the analyzer
                setting.
            min_segment: Minimum observations on each side of a split.

        Returns:
            Change points ordered by position.
        """
        prepared = _as_series(series)
        values = prepared.to_numpy(dtype=float)
        resolved_threshold = (
            self.changepoint_threshold if threshold is None else threshold
        )

        def best_split(start: int, end: int) -> tuple[float, int]:
            segment = values[start:end]
            length = len(segment)
            best_stat, best_index = 0.0, -1
            if length < 2 * min_segment:
                return best_stat, best_index
            for offset in range(min_segment, length - min_segment + 1):
                left = segment[:offset]
                right = segment[offset:]
                denominator = np.sqrt(
                    left.var(ddof=1) / len(left) + right.var(ddof=1) / len(right)
                )
                if denominator == 0 or np.isnan(denominator):
                    continue
                statistic = abs(left.mean() - right.mean()) / denominator
                if statistic > best_stat:
                    best_stat, best_index = statistic, start + offset
            return best_stat, best_index

        segments: list[tuple[int, int]] = [(0, len(values))]
        splits: list[tuple[float, int]] = []
        while segments and len(splits) < self.max_changepoints:
            next_segments: list[tuple[int, int]] = []
            found = False
            for start, end in segments:
                statistic, index = best_split(start, end)
                if index > 0 and statistic >= resolved_threshold:
                    splits.append((statistic, index))
                    next_segments.extend([(start, index), (index, end)])
                    found = True
                else:
                    next_segments.append((start, end))
            if not found:
                break
            segments = next_segments

        points: list[ChangePoint] = []
        for statistic, index in sorted(splits, key=lambda item: item[1]):
            before = values[:index]
            after = values[index:]
            points.append(
                ChangePoint(
                    position=index,
                    date=prepared.index[index],
                    mean_before=float(before.mean()),
                    mean_after=float(after.mean()),
                    magnitude=float(after.mean() - before.mean()),
                    statistic=float(statistic),
                )
            )
        return points

    def calculate_growth_rates(
        self,
        series: pd.Series,
        periods_per_year: int = 12,
    ) -> GrowthResult:
        """Calculate year-over-year growth, CAGR, and acceleration.

        Args:
            series: Datetime-indexed observations.
            periods_per_year: Observations per year (12 for monthly data).

        Returns:
            A :class:`GrowthResult`.

        Raises:
            ValueError: If the series has fewer than two observations.
        """
        prepared = _as_series(series)
        if len(prepared) < 2:
            raise ValueError("Need at least two observations to calculate growth")

        yoy = prepared.pct_change(periods=periods_per_year).dropna() * 100.0
        if yoy.empty:
            yoy = prepared.pct_change().dropna() * 100.0

        years = (prepared.index[-1] - prepared.index[0]).days / 365.25
        cagr = calculate_cagr(
            float(prepared.iloc[0]), float(prepared.iloc[-1]), years
        )

        if len(yoy) >= 4:
            midpoint = len(yoy) // 2
            early = float(yoy.iloc[:midpoint].mean())
            late = float(yoy.iloc[midpoint:].mean())
        else:
            early = late = float(yoy.mean()) if not yoy.empty else float("nan")
        acceleration = late - early

        return GrowthResult(
            yoy_percent=yoy,
            cagr_percent=float(cagr),
            acceleration_percent=float(acceleration),
            start_value=float(prepared.iloc[0]),
            end_value=float(prepared.iloc[-1]),
            years=float(years),
        )

    def forecast(
        self,
        series: pd.Series,
        horizon: int = 10,
        model: ForecastModel = "auto",
        confidence_level: float | None = None,
    ) -> ForecastResult:
        """Generate forecasts with prediction intervals.

        Args:
            series: Datetime-indexed observations.
            horizon: Number of future periods to forecast.
            model: ``"auto"``, ``"linear"``, or ``"arima"``.
            confidence_level: Interval confidence; defaults to the analyzer
                setting.

        Returns:
            A :class:`ForecastResult`.

        Raises:
            ValueError: If ``horizon`` is not positive or the series is too short.
        """
        if horizon <= 0:
            raise ValueError("horizon must be positive")
        prepared = _as_series(series)
        if len(prepared) < 3:
            raise ValueError("Need at least three observations to forecast")

        level = confidence_level or self.confidence_level
        resolved_model = model
        if resolved_model == "auto":
            resolved_model = "arima" if _STATSMODELS_AVAILABLE and len(prepared) >= 24 else "linear"

        if resolved_model == "arima":
            if not _STATSMODELS_AVAILABLE:
                logger.warning("statsmodels unavailable; falling back to linear forecast")
                resolved_model = "linear"
            else:
                return self._forecast_arima(prepared, horizon, level)

        return self._forecast_linear(prepared, horizon, level)

    def _forecast_linear(
        self,
        prepared: pd.Series,
        horizon: int,
        confidence_level: float,
    ) -> ForecastResult:
        values = prepared.to_numpy(dtype=float)
        x = np.arange(len(values), dtype=float)
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, values)
        trend = intercept + slope * x
        residual = values - trend

        months = prepared.index.month
        seasonal = pd.Series(residual).groupby(months).mean()

        frequency = _infer_frequency(prepared.index)
        future_index = pd.date_range(
            start=prepared.index[-1] + pd.tseries.frequencies.to_offset(frequency),
            periods=horizon,
            freq=frequency,
        )
        future_x = np.arange(len(values), len(values) + horizon, dtype=float)
        future_trend = intercept + slope * future_x
        future_seasonal = np.array(
            [seasonal.get(month, 0.0) for month in future_index.month]
        )
        mean_values = future_trend + future_seasonal

        dof = max(1, len(values) - 2)
        sigma = float(np.sqrt(np.sum(residual**2) / dof))
        z_score = float(stats.norm.ppf(0.5 + confidence_level / 2.0))
        centered = x - x.mean()
        denominator = float(np.sum(centered**2)) or 1.0
        prediction_error = sigma * np.sqrt(
            1.0 + 1.0 / len(values) + (future_x - x.mean()) ** 2 / denominator
        )

        mean = pd.Series(mean_values, index=future_index, name="forecast")
        lower = pd.Series(mean_values - z_score * prediction_error, index=future_index)
        upper = pd.Series(mean_values + z_score * prediction_error, index=future_index)

        return ForecastResult(
            mean=mean,
            lower=lower,
            upper=upper,
            horizon=horizon,
            model="linear",
            confidence_level=confidence_level,
            diagnostics={
                "slope_per_period": float(slope),
                "r_squared": float(r_value**2),
                "residual_std": sigma,
                "slope_pvalue": float(p_value),
                "slope_stderr": float(std_err),
            },
        )

    def _forecast_arima(
        self,
        prepared: pd.Series,
        horizon: int,
        confidence_level: float,
    ) -> ForecastResult:
        assert _SARIMAX is not None  # guarded by caller
        seasonal_period = min(self.seasonal_period, max(2, len(prepared) // 3))
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            model = _SARIMAX(
                prepared,
                order=(1, 1, 1),
                seasonal_order=(0, 1, 1, seasonal_period),
                trend="c",
                enforce_stationarity=False,
                enforce_invertibility=False,
            )
            fitted = model.fit(disp=False)
            alpha = 1.0 - confidence_level
            forecast = fitted.get_forecast(steps=horizon)
            mean = forecast.predicted_mean
            interval = forecast.conf_int(alpha=alpha)

        lower = interval.iloc[:, 0]
        upper = interval.iloc[:, 1]
        lower.name = "lower"
        upper.name = "upper"
        mean.name = "forecast"

        return ForecastResult(
            mean=mean,
            lower=lower,
            upper=upper,
            horizon=horizon,
            model="arima",
            confidence_level=confidence_level,
            diagnostics={
                "aic": float(fitted.aic),
                "bic": float(fitted.bic),
                "seasonal_period": float(seasonal_period),
            },
        )

    def stationarity_test(self, series: pd.Series) -> StationarityResult:
        """Run Augmented Dickey-Fuller and KPSS stationarity tests.

        Args:
            series: Datetime-indexed observations.

        Returns:
            A :class:`StationarityResult`. When statsmodels is unavailable the
            result reports ``NaN`` statistics and ``stationary=False``.
        """
        prepared = _as_series(series)
        if not _STATSMODELS_AVAILABLE:
            logger.warning("statsmodels unavailable; stationarity tests skipped")
            return StationarityResult(
                adf_statistic=float("nan"),
                adf_pvalue=float("nan"),
                kpss_statistic=float("nan"),
                kpss_pvalue=float("nan"),
                stationary=False,
                interpretation="statsmodels not installed",
            )

        assert _adfuller is not None and _kpss is not None
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            try:
                adf_stat, adf_pvalue = _adfuller(prepared, autolag="AIC")[:2]
            except Exception as error:  # pragma: no cover - numerical edge cases
                logger.warning("ADF test failed: {}", error)
                adf_stat, adf_pvalue = float("nan"), float("nan")
            try:
                kpss_stat, kpss_pvalue = _kpss(prepared, regression="c", nlags="auto")[:2]
            except Exception as error:  # pragma: no cover
                logger.warning("KPSS test failed: {}", error)
                kpss_stat, kpss_pvalue = float("nan"), float("nan")

        adf_stationary = bool(adf_pvalue < 0.05) if not np.isnan(adf_pvalue) else False
        kpss_stationary = bool(kpss_pvalue > 0.05) if not np.isnan(kpss_pvalue) else False
        stationary = adf_stationary and kpss_stationary
        if stationary:
            interpretation = "Both tests support stationarity"
        elif adf_stationary:
            interpretation = "ADF rejects a unit root but KPSS rejects stationarity"
        elif kpss_stationary:
            interpretation = "KPSS does not reject stationarity but ADF does not reject a unit root"
        else:
            interpretation = "Tests suggest a non-stationary series"

        return StationarityResult(
            adf_statistic=float(adf_stat),
            adf_pvalue=float(adf_pvalue),
            kpss_statistic=float(kpss_stat),
            kpss_pvalue=float(kpss_pvalue),
            stationary=stationary,
            interpretation=interpretation,
        )
