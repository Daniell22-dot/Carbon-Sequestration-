"""Shared pytest fixtures. All fixtures are deterministic and offline."""

from __future__ import annotations

from collections.abc import Iterator

import numpy as np
import pandas as pd
import pytest


def _monthly_index(start: str = "1990-01-01", periods: int = 192) -> pd.DatetimeIndex:
    return pd.date_range(start=start, periods=periods, freq="MS")


@pytest.fixture
def sample_noaa_text() -> str:
    """Return a NOAA-style monthly CSV payload with comment headers."""
    lines = [
        "# NOAA GML monthly CO2 (synthetic fixture for tests only)",
        "# year,month,decimal,average,deseasonalized,ndays,sdev",
        "year,month,decimal,average,deseasonalized,ndays,sdev",
    ]
    for year in range(1990, 2006):
        for month in range(1, 13):
            decimal = year + (month - 0.5) / 12
            seasonal = 3.0 * np.sin(2 * np.pi * (month - 1) / 12)
            co2 = 350.0 + 1.5 * (year - 1990) + seasonal
            lines.append(
                f"{year},{month},{decimal:.3f},{co2:.2f},{co2 - seasonal:.2f},"
                f"28,0.10"
            )
    return "\n".join(lines)


@pytest.fixture
def sample_noaa_frame(sample_noaa_text: str) -> pd.DataFrame:
    """Parsed NOAA fixture DataFrame."""
    from src.data_acquisition.noaa_co2 import parse_noaa_monthly

    return parse_noaa_monthly(sample_noaa_text, station="mlo")


@pytest.fixture
def sample_series() -> pd.Series:
    """Deterministic monthly CO2-like series with trend and seasonality."""
    index = _monthly_index()
    steps = np.arange(len(index), dtype=float)
    seasonal = 3.0 * np.sin(2 * np.pi * index.month.to_numpy() / 12.0)
    values = 350.0 + 0.15 * steps + seasonal
    return pd.Series(values, index=index, name="co2_ppm")


@pytest.fixture
def sample_projects() -> pd.DataFrame:
    """Small valid carbon removal project table."""
    return pd.DataFrame(
        {
            "project_id": ["p1", "p2", "p3"],
            "project_name": ["Alpha DAC", "Beta Biochar", "Gamma Forest"],
            "method": ["Direct Air Capture", "biochar", "Afforestation"],
            "capacity_tco2_year": [1000.0, 5000.0, 20000.0],
            "status": ["operational", "pilot", "development"],
            "latitude": [64.1, 40.0, -3.0],
            "longitude": [-21.9, -100.0, 30.0],
            "country": ["ISL", "USA", "TZA"],
            "start_year": [2020, 2022, 2019],
            "cost_per_ton": [400.0, 120.0, 25.0],
            "funding_source": ["private", "public", "mixed"],
        }
    )


@pytest.fixture
def sample_comparison() -> pd.DataFrame:
    """Scored comparison table built from the project catalog."""
    from src.analysis.comparison import build_comparison_table, score_methods

    return score_methods(build_comparison_table())


@pytest.fixture
def figure_path(tmp_path) -> Iterator[object]:
    """Create a tiny PNG figure for report tests."""

    def _create(name: str = "figure.png"):
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        path = tmp_path / name
        figure, axis = plt.subplots(figsize=(2, 2))
        axis.plot([0, 1, 2], [0, 1, 4])
        figure.savefig(path)
        plt.close(figure)
        return path

    yield _create
