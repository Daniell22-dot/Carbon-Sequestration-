"""Run time series analysis and method comparison, writing machine-readable outputs."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.analysis.comparison import (
    build_comparison_table,
    cost_effectiveness,
    pareto_frontier,
    score_methods,
)
from src.analysis.forecasting import compare_forecast_methods, forecast_series
from src.analysis.risk_analysis import assess_portfolio_risk, simulate_portfolio
from src.analysis.time_series import CarbonTimeSeriesAnalyzer
from src.analysis.trends import summarize_trend
from src.config import load_config
from src.utils.io import write_dataframe, write_json
from src.utils.logging import setup_logging
from src.visualization.static_plots import (
    plot_co2_series,
    plot_decomposition,
    plot_forecast,
    plot_method_comparison,
    plot_pareto,
)


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=None, help="Processed NOAA CSV")
    parser.add_argument("--station", default=None)
    parser.add_argument("--horizon", type=int, default=None)
    parser.add_argument("--config", type=Path, default=None)
    return parser


def _load_series(path: Path) -> pd.Series:
    frame = pd.read_csv(path, parse_dates=["date"])
    frame = frame.dropna(subset=["co2_ppm"]).sort_values("date")
    series = frame.set_index("date")["co2_ppm"]
    series.name = "co2_ppm"
    return series


def main(argv: list[str] | None = None) -> int:
    """Run the analysis workflow.

    Args:
        argv: Optional argument list.

    Returns:
        Process exit code.
    """
    args = build_parser().parse_args(argv)
    setup_logging()
    config = load_config(args.config)

    station = args.station or config.data_sources.noaa.station
    input_path = args.input or config.paths.processed_dir / f"noaa_co2_{station}.csv"
    if not input_path.exists():
        raise SystemExit(
            f"Processed input not found: {input_path}. Run scripts/download_data.py first."
        )

    series = _load_series(input_path)
    horizon = args.horizon or config.analysis.forecast_horizon
    analyzer = CarbonTimeSeriesAnalyzer(
        seasonal_period=config.analysis.seasonal_period,
        confidence_level=config.analysis.confidence_level,
        changepoint_threshold=config.analysis.changepoint_threshold,
    )

    decomposition = analyzer.decompose(series)
    changepoints = analyzer.detect_changepoints(series)
    growth = analyzer.calculate_growth_rates(series)
    stationarity = analyzer.stationarity_test(series)
    trend = summarize_trend(series, periods_per_year=12)
    forecast = forecast_series(
        series,
        horizon=horizon,
        confidence_level=config.analysis.confidence_level,
        seasonal_period=config.analysis.seasonal_period,
    )
    backtest = compare_forecast_methods(series, seasonal_period=config.analysis.seasonal_period)

    comparison = build_comparison_table(list(config.analysis.methods))
    scored = score_methods(comparison)
    pareto = pareto_frontier(scored)
    effectiveness = cost_effectiveness(scored)
    risk = assess_portfolio_risk(scored)

    capacity_frame = scored.copy()
    capacity_frame["capacity_tco2_year"] = (
        capacity_frame["scalability_gt_year"] * 1_000_000.0
    )
    simulation = simulate_portfolio(capacity_frame, years=horizon)

    summary: dict[str, Any] = {
        "station": station,
        "observations": int(len(series)),
        "start": str(series.index.min().date()),
        "end": str(series.index.max().date()),
        "growth": {
            "cagr_percent": growth.cagr_percent,
            "acceleration_percent": growth.acceleration_percent,
            "start_value": growth.start_value,
            "end_value": growth.end_value,
            "years": growth.years,
        },
        "trend": trend,
        "stationarity": {
            "adf_statistic": stationarity.adf_statistic,
            "adf_pvalue": stationarity.adf_pvalue,
            "kpss_statistic": stationarity.kpss_statistic,
            "kpss_pvalue": stationarity.kpss_pvalue,
            "stationary": stationarity.stationary,
            "interpretation": stationarity.interpretation,
        },
        "changepoints": [
            {
                "date": str(point.date.date()) if point.date is not None else None,
                "direction": point.direction,
                "magnitude": point.magnitude,
                "statistic": point.statistic,
            }
            for point in changepoints
        ],
        "forecast": {
            "model": forecast.model,
            "horizon": forecast.horizon,
            "confidence_level": forecast.confidence_level,
            "diagnostics": forecast.diagnostics,
            "final_mean": float(forecast.mean.iloc[-1]),
            "final_lower": float(forecast.lower.iloc[-1]),
            "final_upper": float(forecast.upper.iloc[-1]),
        },
        "risk": {
            "weighted_risk_score": risk["weighted_risk_score"],
            "risk_level": risk["risk_level"],
            "portfolio_reversal_probability": risk["portfolio_reversal_probability"],
        },
    }

    exports = config.paths.exports_dir
    figures = config.paths.figures_dir
    exports.mkdir(parents=True, exist_ok=True)
    figures.mkdir(parents=True, exist_ok=True)

    write_json(exports / "analysis_summary.json", summary)
    write_dataframe(decomposition.to_frame().reset_index(), exports / "decomposition.csv")
    write_dataframe(forecast.to_frame().reset_index(), exports / "forecast.csv")
    write_dataframe(backtest, exports / "forecast_backtest.csv")
    write_dataframe(scored, exports / "method_comparison.csv")
    write_dataframe(pareto, exports / "pareto_frontier.csv")
    write_dataframe(effectiveness, exports / "cost_effectiveness.csv")
    write_dataframe(simulation, exports / "portfolio_simulation.csv")

    plot_co2_series(
        pd.DataFrame({"date": series.index, "co2_ppm": series.to_numpy()}),
        figures / "co2_series.png",
        changepoints=changepoints,
    )
    plot_decomposition(decomposition, figures / "decomposition.png")
    plot_forecast(series, forecast, figures / "forecast.png")
    plot_method_comparison(scored, figures / "method_comparison.png")
    plot_pareto(pareto, figures / "pareto_frontier.png")

    print(f"Analysis outputs written to {exports} and {figures}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
