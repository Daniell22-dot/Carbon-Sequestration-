"""Generate DOCX, PDF, HTML, and Excel reports from analysis outputs."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import load_config
from src.reporting.excel_export import export_workbook
from src.reporting.html_report import render_html_report
from src.reporting.pdf_report import create_pdf_report
from src.reporting.word_report import create_report
from src.utils.io import read_json
from src.utils.logging import setup_logging


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument(
        "--formats",
        nargs="+",
        default=None,
        choices=["docx", "pdf", "html", "xlsx"],
        help="Report formats to generate",
    )
    return parser


def _format_number(value: Any, digits: int = 2) -> str:
    if value is None:
        return "n/a"
    try:
        return f"{float(value):,.{digits}f}"
    except (TypeError, ValueError):
        return str(value)


def _build_sections(summary: dict[str, Any], comparison: pd.DataFrame) -> dict[str, str]:
    growth = summary.get("growth", {})
    forecast = summary.get("forecast", {})
    risk = summary.get("risk", {})
    trend = summary.get("trend", {})

    ranked = comparison.sort_values("rank")
    top_methods = ", ".join(
        f"{row.get('display_name', row['method'])} (score {row['composite_score']:.2f})"
        for _, row in ranked.head(3).iterrows()
    )

    executive = (
        f"This report analyzes {summary.get('observations', 0):,} monthly NOAA CO2 "
        f"observations from {summary.get('start', 'n/a')} to {summary.get('end', 'n/a')}.\n\n"
        f"The estimated compound annual growth rate over the record is "
        f"{_format_number(growth.get('cagr_percent'))}% and the Mann-Kendall test "
        f"reports a {trend.get('mann_kendall_trend', 'n/a')} trend "
        f"(p = {_format_number(trend.get('mann_kendall_pvalue'), 4)}).\n\n"
        f"The {forecast.get('model', 'n/a')} forecast projects "
        f"{_format_number(forecast.get('final_mean'))} ppm by the end of the horizon, "
        f"with a {int(float(forecast.get('confidence_level', 0.95)) * 100)}% interval of "
        f"{_format_number(forecast.get('final_lower'))} to "
        f"{_format_number(forecast.get('final_upper'))} ppm.\n\n"
        f"Leading sequestration options by weighted score: {top_methods}. "
        f"Portfolio risk is classified as {risk.get('risk_level', 'n/a')}."
    )

    methodology = (
        "CO2 concentrations are sourced from the NOAA Global Monitoring Laboratory "
        "monthly station files. Data are cached with SHA-256 provenance metadata and "
        "validated before analysis.\n\n"
        "Trend detection combines the non-parametric Mann-Kendall test with OLS and "
        "Theil-Sen slope estimates. Forecasts use SARIMA when statsmodels is available "
        "and fall back to a seasonal linear model otherwise. Change points are located "
        "by binary segmentation using Welch-style mean-shift statistics.\n\n"
        "Method comparison normalizes literature-derived cost, permanence, scalability, "
        "energy, technology readiness, and risk ranges onto a 0-1 scale, then applies "
        "user-configurable weights. These ranges are reference values, not measurements "
        "produced by this project."
    )

    comparison_text = (
        "Scores are relative to the methods included in this run, so they are not "
        "comparable across runs with different method sets.\n\n"
        "Pareto analysis identifies methods that are not dominated on both cost and "
        "composite benefit. Cost-effectiveness is reported as composite score per "
        "USD/tCO2 and should be read alongside permanence and reversal risk."
    )

    limitations = (
        "Correlation between atmospheric CO2 and sequestration deployment does not "
        "establish causality. Forecast intervals widen with horizon and assume the "
        "estimated model structure remains valid.\n\n"
        "Method cost and permanence ranges are drawn from published literature and "
        "industry reporting; they vary by location, scale, and accounting boundary. "
        "Portfolio simulations are illustrative and do not constitute investment advice."
    )

    return {
        "Executive Summary": executive,
        "Introduction and Data Provenance": methodology,
        "Method Comparison": comparison_text,
        "Limitations and Uncertainties": limitations,
    }


def main(argv: list[str] | None = None) -> int:
    """Generate configured report formats.

    Args:
        argv: Optional argument list.

    Returns:
        Process exit code.
    """
    args = build_parser().parse_args(argv)
    setup_logging()
    config = load_config(args.config)
    formats = args.formats or list(config.reporting.format)

    exports = config.paths.exports_dir
    figures = config.paths.figures_dir
    reports = config.paths.reports_dir

    summary_path = exports / "analysis_summary.json"
    comparison_path = exports / "method_comparison.csv"
    if not summary_path.exists() or not comparison_path.exists():
        raise SystemExit(
            "Analysis outputs missing. Run scripts/run_analysis.py first."
        )

    summary = read_json(summary_path)
    comparison = pd.read_csv(comparison_path)
    sections = _build_sections(summary, comparison)

    figure_map = {
        "Introduction and Data Provenance": [
            figures / "co2_series.png",
            figures / "decomposition.png",
        ],
        "Method Comparison": [
            figures / "method_comparison.png",
            figures / "pareto_frontier.png",
        ],
        "Executive Summary": [figures / "forecast.png"],
    }
    figure_map = {
        key: [path for path in paths if path.exists()] for key, paths in figure_map.items()
    }

    table_map = {
        "Method Comparison": comparison,
        "Executive Summary": pd.read_csv(exports / "forecast_backtest.csv")
        if (exports / "forecast_backtest.csv").exists()
        else pd.DataFrame(),
    }
    metadata = {
        "Source": "NOAA GML",
        "Station": summary.get("station", "n/a"),
        "Observations": summary.get("observations", "n/a"),
        "Period": f"{summary.get('start', 'n/a')} to {summary.get('end', 'n/a')}",
    }

    reports.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    if "docx" in formats:
        written.append(
            create_report(
                title=config.reporting.title,
                subtitle="Atmospheric CO2 trends and sequestration method assessment",
                sections=sections,
                figures=figure_map,
                tables=table_map,
                output_path=reports / "carbon_sequestration_report.docx",
                metadata=metadata,
            )
        )
    if "pdf" in formats:
        written.append(
            create_pdf_report(
                title=config.reporting.title,
                subtitle="Atmospheric CO2 trends and sequestration method assessment",
                sections=sections,
                figures=figure_map,
                tables=table_map,
                output_path=reports / "carbon_sequestration_report.pdf",
            )
        )
    if "html" in formats:
        written.append(
            render_html_report(
                title=config.reporting.title,
                subtitle="Atmospheric CO2 trends and sequestration method assessment",
                sections=sections,
                figures=figure_map,
                tables=table_map,
                output_path=reports / "carbon_sequestration_report.html",
            )
        )
    if "xlsx" in formats:
        sheets = {
            "Summary": pd.json_normalize(summary, sep="_"),
            "MethodComparison": comparison,
            "Forecast": pd.read_csv(exports / "forecast.csv")
            if (exports / "forecast.csv").exists()
            else pd.DataFrame(),
            "Backtest": pd.read_csv(exports / "forecast_backtest.csv")
            if (exports / "forecast_backtest.csv").exists()
            else pd.DataFrame(),
            "PortfolioSimulation": pd.read_csv(exports / "portfolio_simulation.csv")
            if (exports / "portfolio_simulation.csv").exists()
            else pd.DataFrame(),
        }
        written.append(
            export_workbook(
                sheets,
                output_path=reports / "carbon_sequestration_data.xlsx",
                metadata=metadata,
            )
        )

    for path in written:
        print(f"Wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
