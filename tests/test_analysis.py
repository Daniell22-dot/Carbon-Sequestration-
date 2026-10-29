"""Tests for time series analysis, comparison, and risk."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from src.analysis.comparison import (
    build_comparison_table,
    cost_effectiveness,
    pareto_frontier,
    score_methods,
)
from src.analysis.forecasting import (
    backtest,
    compare_forecast_methods,
    scenario_forecast,
)
from src.analysis.risk_analysis import (
    assess_method_risk,
    assess_portfolio_risk,
    simulate_portfolio,
)
from src.analysis.time_series import CarbonTimeSeriesAnalyzer
from src.analysis.trends import linear_trend, mann_kendall, sen_slope, summarize_trend


class TestDecomposition:
    """Tests for seasonal decomposition."""

    def test_additive_decomposition(self, sample_series: pd.Series) -> None:
        analyzer = CarbonTimeSeriesAnalyzer(seasonal_period=12)
        result = analyzer.decompose(sample_series)
        assert len(result.trend) == len(sample_series)
        assert result.seasonal.notna().sum() > 0
        assert result.residual.notna().sum() > 0
        assert result.period == 12

    def test_short_series_raises(self) -> None:
        analyzer = CarbonTimeSeriesAnalyzer(seasonal_period=12)
        short = pd.Series(
            np.arange(10, dtype=float),
            index=pd.date_range("2020-01-01", periods=10, freq="MS"),
        )
        with pytest.raises(ValueError, match="at least"):
            analyzer.decompose(short)


class TestChangePoints:
    """Tests for mean-shift detection."""

    def test_detects_clear_level_shift(self) -> None:
        index = pd.date_range("2000-01-01", periods=120, freq="MS")
        values = np.concatenate([np.full(60, 10.0), np.full(60, 20.0)])
        series = pd.Series(values, index=index)
        analyzer = CarbonTimeSeriesAnalyzer(changepoint_threshold=3.0)
        points = analyzer.detect_changepoints(series, min_segment=6)
        assert points
        assert any(abs(point.position - 60) <= 2 for point in points)
        assert points[0].direction == "increase"


class TestGrowthAndTrend:
    """Tests for growth and trend statistics."""

    def test_growth_metrics(self, sample_series: pd.Series) -> None:
        analyzer = CarbonTimeSeriesAnalyzer()
        growth = analyzer.calculate_growth_rates(sample_series)
        assert growth.cagr_percent > 0
        assert growth.years == pytest.approx(191 / 12, abs=0.2)
        assert not growth.yoy_percent.empty

    def test_mann_kendall_detects_increasing(self, sample_series: pd.Series) -> None:
        result = mann_kendall(sample_series)
        assert result.trend == "increasing"
        assert result.significant
        assert result.sen_slope_per_year > 0

    def test_linear_trend_and_summary(self, sample_series: pd.Series) -> None:
        trend = linear_trend(sample_series)
        assert trend.slope_per_year > 0
        assert 0 <= trend.r_squared <= 1
        summary = summarize_trend(sample_series)
        assert summary["mann_kendall_trend"] == "increasing"
        assert sen_slope(sample_series) > 0


class TestForecasting:
    """Tests for forecast generation and backtesting."""

    def test_linear_forecast_intervals(self, sample_series: pd.Series) -> None:
        analyzer = CarbonTimeSeriesAnalyzer()
        result = analyzer.forecast(sample_series, horizon=12, model="linear")
        assert len(result.mean) == 12
        assert (result.lower <= result.mean).all()
        assert (result.mean <= result.upper).all()
        assert result.mean.iloc[-1] > sample_series.iloc[-1]
        assert result.model == "linear"

    def test_invalid_horizon(self, sample_series: pd.Series) -> None:
        analyzer = CarbonTimeSeriesAnalyzer()
        with pytest.raises(ValueError, match="horizon"):
            analyzer.forecast(sample_series, horizon=0)

    def test_backtest_and_model_comparison(self, sample_series: pd.Series) -> None:
        metrics = backtest(sample_series, model="linear", test_size=12)
        assert metrics["rmse"] >= 0
        comparison = compare_forecast_methods(
            sample_series, test_size=12, models=("linear",)
        )
        assert list(comparison["model"]) == ["linear"]

    def test_scenario_forecast(self, sample_series: pd.Series) -> None:
        analyzer = CarbonTimeSeriesAnalyzer()
        base = analyzer.forecast(sample_series, horizon=6, model="linear")
        scenarios = scenario_forecast(
            base,
            {"low": 0.9, "high": 1.1},
            annual_growth_percent=1.0,
        )
        assert set(scenarios["scenario"]) == {"low", "high"}
        assert len(scenarios) == 12
        low = scenarios[scenarios["scenario"] == "low"]["forecast"].to_numpy()
        high = scenarios[scenarios["scenario"] == "high"]["forecast"].to_numpy()
        assert (low < high).all()


class TestStationarity:
    """Tests for stationarity testing."""

    def test_stationarity_fields(self, sample_series: pd.Series) -> None:
        analyzer = CarbonTimeSeriesAnalyzer()
        result = analyzer.stationarity_test(sample_series)
        assert isinstance(result.stationary, bool)
        assert result.interpretation


class TestComparison:
    """Tests for multi-criteria scoring and Pareto analysis."""

    def test_build_and_score(self) -> None:
        frame = build_comparison_table()
        scored = score_methods(frame)
        assert len(scored) == 5
        assert scored["composite_score"].between(0, 1).all()
        assert scored["rank"].min() == 1
        assert scored["rank"].is_unique

    def test_weights_change_ranking(self) -> None:
        frame = build_comparison_table()
        cost_heavy = score_methods(frame, weights={"cost": 1.0})
        permanence_heavy = score_methods(frame, weights={"permanence": 1.0})
        assert cost_heavy.iloc[0]["method"] != permanence_heavy.iloc[0]["method"]

    def test_pareto_and_effectiveness(self) -> None:
        scored = score_methods(build_comparison_table())
        pareto = pareto_frontier(scored)
        assert "pareto_optimal" in pareto.columns
        assert pareto["pareto_optimal"].any()
        effectiveness = cost_effectiveness(scored)
        assert "benefit_per_cost" in effectiveness.columns


class TestRisk:
    """Tests for method and portfolio risk."""

    def test_assess_method_risk(self) -> None:
        row = {
            "method": "dac",
            "reversal_probability": 0.02,
            "permanence_min": 1000,
            "trl": 7,
            "energy_gj_per_tco2": 6.0,
        }
        assessment = assess_method_risk(row)
        assert 0 <= assessment.score <= 1
        assert assessment.level in {"low", "moderate", "high", "very high"}

    def test_portfolio_risk_and_simulation(self) -> None:
        frame = build_comparison_table()
        frame["capacity_tco2_year"] = frame["scalability_gt_year"] * 1_000_000
        risk = assess_portfolio_risk(frame)
        assert 0 <= risk["weighted_risk_score"] <= 1
        assert 0 <= risk["portfolio_reversal_probability"] <= 1
        simulation = simulate_portfolio(frame, years=5, n_simulations=50)
        assert list(simulation.columns) == ["year", "p10", "p50", "p90", "mean", "std"]
        assert (simulation["p10"] <= simulation["p50"]).all()
        assert (simulation["p50"] <= simulation["p90"]).all()
