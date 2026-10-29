"""NOAA Global Monitoring Laboratory monthly CO2 data acquisition.

Data source:
    https://gml.noaa.gov/ccgg/trends/data.html

The monthly files are CSV documents with comment lines beginning with ``#``.
This module parses them into the schema documented in ``AGENTS.md`` and caches
the raw payload with provenance metadata.
"""

from __future__ import annotations

import io
from pathlib import Path

import pandas as pd

from src.constants import NOAA_MONTHLY_URL_TEMPLATE, RAW_DATA_DIR, STATIONS
from src.data_acquisition.base import BaseDownloader, DataSourceUnavailableError
from src.data_processing.validators import assert_valid, validate_noaa_data
from src.utils.logging import get_logger

logger = get_logger(__name__)

_REQUIRED_COLUMNS = ("year", "month", "co2_ppm")
_COLUMN_ALIASES = {
    "year": "year",
    "month": "month",
    "decimal": "decimal_date",
    "decimal date": "decimal_date",
    "decimal_date": "decimal_date",
    "average": "co2_ppm",
    "average (ppm)": "co2_ppm",
    "co2": "co2_ppm",
    "deseasonalized": "co2_deseasonalized",
    "ndays": "n_days",
    "sdev": "std_dev",
}


def _normalize_columns(columns: list[str]) -> list[str]:
    normalized: list[str] = []
    for column in columns:
        key = column.strip().lower()
        normalized.append(_COLUMN_ALIASES.get(key, key.replace(" ", "_")))
    return normalized


def parse_noaa_monthly(text: str, station: str = "mlo") -> pd.DataFrame:
    """Parse a NOAA monthly CO2 CSV payload.

    Args:
        text: Raw file contents, including ``#`` comment lines.
        station: Lowercase station code used to attach metadata.

    Returns:
        DataFrame with columns ``date``, ``year``, ``month``, ``co2_ppm``,
        ``co2_deseasonalized``, ``station``, ``latitude``, ``longitude``, and
        ``elevation_m``.

    Raises:
        DataSourceUnavailableError: If the payload cannot be parsed.
        ValueError: If the station code is unknown.
    """
    station_code = station.lower()
    if station_code not in STATIONS:
        raise ValueError(
            f"Unknown station '{station}'. Supported: {', '.join(sorted(STATIONS))}"
        )

    try:
        frame = pd.read_csv(
            io.StringIO(text),
            comment="#",
            skip_blank_lines=True,
            na_values=["", "-9.99", "-999.99", "-999"],
        )
    except Exception as error:  # pragma: no cover - pandas parser errors vary
        raise DataSourceUnavailableError(
            "NOAA GML", f"could not parse monthly CSV: {error}"
        ) from error

    frame.columns = _normalize_columns([str(column) for column in frame.columns])
    missing = [column for column in _REQUIRED_COLUMNS if column not in frame.columns]
    if missing:
        raise DataSourceUnavailableError(
            "NOAA GML", f"missing required columns: {', '.join(missing)}"
        )

    frame["year"] = pd.to_numeric(frame["year"], errors="coerce")
    frame["month"] = pd.to_numeric(frame["month"], errors="coerce")
    frame["co2_ppm"] = pd.to_numeric(frame["co2_ppm"], errors="coerce")

    if "co2_deseasonalized" in frame.columns:
        frame["co2_deseasonalized"] = pd.to_numeric(
            frame["co2_deseasonalized"], errors="coerce"
        )
    else:
        frame["co2_deseasonalized"] = float("nan")

    frame = frame.dropna(subset=["year", "month"])
    frame = frame[(frame["month"] >= 1) & (frame["month"] <= 12)]
    frame["year"] = frame["year"].astype(int)
    frame["month"] = frame["month"].astype(int)

    frame["date"] = pd.to_datetime(
        {
            "year": frame["year"],
            "month": frame["month"],
            "day": 1,
        },
        errors="coerce",
    )
    frame = frame.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)

    metadata = STATIONS[station_code]
    frame["station"] = station_code
    frame["latitude"] = float(metadata["latitude"])  # type: ignore[arg-type]
    frame["longitude"] = float(metadata["longitude"])  # type: ignore[arg-type]
    frame["elevation_m"] = float(metadata["elevation_m"])  # type: ignore[arg-type]

    columns = [
        "date",
        "year",
        "month",
        "co2_ppm",
        "co2_deseasonalized",
        "station",
        "latitude",
        "longitude",
        "elevation_m",
    ]
    return frame[columns]


def download_noaa_co2(
    station: str = "mlo",
    start_year: int | None = None,
    end_year: int | None = None,
    cache_dir: Path | str = RAW_DATA_DIR / "noaa_co2",
    cache_hours: int = 24,
    force: bool = False,
) -> pd.DataFrame:
    """Download monthly CO2 concentrations from NOAA GML.

    Args:
        station: Station code such as ``"mlo"`` (Mauna Loa) or ``"brw"``.
        start_year: Inclusive lower year bound.
        end_year: Inclusive upper year bound.
        cache_dir: Directory for cached raw payloads.
        cache_hours: Cache freshness window in hours.
        force: Refetch even when a fresh cache entry exists.

    Returns:
        Validated DataFrame using the NOAA schema from ``AGENTS.md``.

    Raises:
        ValueError: If the station is unsupported or the year range is invalid.
        DataSourceUnavailableError: If the download and cache both fail.
        DataValidationError: If the parsed data fails validation.

    Example:
        >>> df = download_noaa_co2(station="mlo", start_year=2000)  # doctest: +SKIP
        >>> df["co2_ppm"].iloc[-1] > 300  # doctest: +SKIP
        True
    """
    station_code = station.lower()
    if station_code not in STATIONS:
        raise ValueError(
            f"Unknown station '{station}'. Supported: {', '.join(sorted(STATIONS))}"
        )
    if start_year and end_year and start_year > end_year:
        raise ValueError("start_year must be less than or equal to end_year")

    url = NOAA_MONTHLY_URL_TEMPLATE.format(station=station_code)
    downloader = BaseDownloader(
        cache_dir=cache_dir,
        cache_hours=cache_hours,
        source_name="NOAA GML",
    )
    payload = downloader.fetch(
        url,
        suffix=".csv",
        cache_key=f"noaa_co2_monthly_{station_code}",
        force=force,
    )

    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError:
        text = payload.decode("latin-1")

    frame = parse_noaa_monthly(text, station=station_code)

    if start_year is not None:
        frame = frame[frame["year"] >= start_year]
    if end_year is not None:
        frame = frame[frame["year"] <= end_year]
    frame = frame.reset_index(drop=True)

    result = validate_noaa_data(frame)
    assert_valid(result)
    logger.info(
        "NOAA {}: {} monthly observations ({} to {})",
        station_code,
        len(frame),
        frame["year"].min() if not frame.empty else "n/a",
        frame["year"].max() if not frame.empty else "n/a",
    )
    return frame
