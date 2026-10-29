"""Tests for visualization and report generation."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from src.analysis.comparison import (
    build_comparison_table,
    pareto_frontier,
    score_methods,
)
from src.analysis.time_series import CarbonTimeSeriesAnalyzer
from src.reporting.excel_export import export_workbook
from src.reporting.html_report import render_html_report
from src.reporting.pdf_report import create_pdf_report
from src.reporting.word_report import create_report
from src.visualization.static_plots import (
    plot_co2_series,
    plot_decomposition,
    plot_forecast,
    plot_method_comparison,
    plot_pareto,
)

SECTIONS = {
    "Executive Summary": "Atmospheric CO2 continues to rise.\n\nMethod scores are relative.",
    "Method Comparison": "DAC scores highest on permanence; forestry on cost.",
}


class TestStaticPlots:
    """Tests for matplotlib figure generation."""

    def test_plot_co2_series(
        self, sample_noaa_frame: pd.DataFrame, tmp_path: Path
    ) -> None:
        path = tmp_path / "co2.png"
        plot_co2_series(sample_noaa_frame, output_path=path)
        assert path.exists() and path.stat().st_size > 0

    def test_plot_decomposition(self, sample_series: pd.Series, tmp_path: Path) -> None:
        analyzer = CarbonTimeSeriesAnalyzer()
        path = tmp_path / "decomposition.png"
        plot_decomposition(analyzer.decompose(sample_series), output_path=path)
        assert path.exists() and path.stat().st_size > 0

    def test_plot_forecast(self, sample_series: pd.Series, tmp_path: Path) -> None:
        analyzer = CarbonTimeSeriesAnalyzer()
        forecast = analyzer.forecast(sample_series, horizon=12, model="linear")
        path = tmp_path / "forecast.png"
        plot_forecast(sample_series, forecast, output_path=path)
        assert path.exists() and path.stat().st_size > 0

    def test_plot_comparison_and_pareto(self, tmp_path: Path) -> None:
        scored = score_methods(build_comparison_table())
        pareto = pareto_frontier(scored)
        comparison_path = tmp_path / "comparison.png"
        pareto_path = tmp_path / "pareto.png"
        plot_method_comparison(scored, output_path=comparison_path)
        plot_pareto(pareto, output_path=pareto_path)
        assert comparison_path.exists() and comparison_path.stat().st_size > 0
        assert pareto_path.exists() and pareto_path.stat().st_size > 0


class TestReports:
    """Tests for document generation."""

    def test_word_report(self, tmp_path: Path, figure_path) -> None:
        output = tmp_path / "report.docx"
        create_report(
            title="Test Report",
            subtitle="Unit test",
            sections=SECTIONS,
            figures={"Executive Summary": [figure_path()]},
            tables={"Method Comparison": build_comparison_table()},
            output_path=output,
            metadata={"Source": "NOAA GML"},
        )
        assert output.exists() and output.stat().st_size > 1000

    def test_html_report(self, tmp_path: Path, figure_path) -> None:
        output = tmp_path / "report.html"
        render_html_report(
            title="Test Report",
            sections=SECTIONS,
            figures={"Executive Summary": [figure_path()]},
            tables={"Method Comparison": build_comparison_table()},
            output_path=output,
        )
        content = output.read_text(encoding="utf-8")
        assert "<html" in content
        assert "Test Report" in content
        assert "data:image/png;base64," in content

    def test_excel_export(self, tmp_path: Path) -> None:
        output = tmp_path / "analysis.xlsx"
        export_workbook(
            {"Methods": build_comparison_table()},
            output_path=output,
            metadata={"source": "NOAA GML"},
        )
        assert output.exists() and output.stat().st_size > 1000

    def test_pdf_report(self, tmp_path: Path, figure_path) -> None:
        output = tmp_path / "report.pdf"
        create_pdf_report(
            title="Test Report",
            subtitle="Unit test",
            sections=SECTIONS,
            figures={"Executive Summary": [figure_path()]},
            tables={"Method Comparison": build_comparison_table()},
            output_path=output,
        )
        assert output.exists() and output.stat().st_size > 1000
