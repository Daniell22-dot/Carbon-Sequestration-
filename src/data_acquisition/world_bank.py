"""World Bank climate indicator acquisition via the public API v2."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from src.constants import RAW_DATA_DIR, WORLD_BANK_URL_TEMPLATE
from src.data_acquisition.base import BaseDownloader, DataSourceUnavailableError
from src.utils.logging import get_logger

logger = get_logger(__name__)

PAGE_SIZE = 1000


def _parse_page(payload: Any, indicator: str) -> tuple[list[dict[str, Any]], int]:
    if not isinstance(payload, list) or len(payload) < 2:
        raise DataSourceUnavailableError(
            "World Bank", "unexpected API response structure"
        )
    metadata, rows = payload[0], payload[1]
    if not isinstance(metadata, dict) or not isinstance(rows, list):
        raise DataSourceUnavailableError(
            "World Bank", "unexpected API response structure"
        )
    pages = int(metadata.get("pages", 1))
    records: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        records.append(
            {
                "indicator": row.get("indicator", {}).get("id", indicator),
                "indicator_name": row.get("indicator", {}).get("value", ""),
                "country": row.get("country", {}).get("value", ""),
                "country_code": row.get("countryiso3code") or row.get("country", {}).get("id", ""),
                "year": pd.to_numeric(row.get("date"), errors="coerce"),
                "value": pd.to_numeric(row.get("value"), errors="coerce"),
            }
        )
    return records, pages


def download_world_bank_indicator(
    indicator: str,
    countries: str = "all",
    start_year: int | None = None,
    end_year: int | None = None,
    cache_dir: Path | str = RAW_DATA_DIR / "world_bank",
    cache_hours: int = 168,
    force: bool = False,
) -> pd.DataFrame:
    """Download a World Bank indicator series.

    Args:
        indicator: Indicator code, e.g. ``"EN.GHG.CO2.MT.CE.AR5"``.
        countries: Semicolon-separated ISO codes or ``"all"``.
        start_year: Inclusive start year.
        end_year: Inclusive end year.
        cache_dir: Cache directory for raw pages.
        cache_hours: Cache freshness window in hours.
        force: Refetch even when fresh cache entries exist.

    Returns:
        DataFrame with columns ``indicator``, ``indicator_name``, ``country``,
        ``country_code``, ``year``, and ``value``.

    Raises:
        DataSourceUnavailableError: If the API cannot be reached or parsed.
    """
    downloader = BaseDownloader(
        cache_dir=cache_dir,
        cache_hours=cache_hours,
        source_name="World Bank",
    )
    url = WORLD_BANK_URL_TEMPLATE.format(countries=countries, indicator=indicator)
    date_range = "1960:2100"
    if start_year or end_year:
        date_range = f"{start_year or 1960}:{end_year or 2100}"

    all_records: list[dict[str, Any]] = []
    page = 1
    total_pages = 1
    while page <= total_pages:
        params = {
            "format": "json",
            "per_page": PAGE_SIZE,
            "page": page,
            "date": date_range,
        }
        payload = downloader.fetch_json(
            url,
            params=params,
            cache_key=f"world_bank_{indicator}_{countries}_{date_range}_p{page}",
            force=force,
        )
        records, total_pages = _parse_page(payload, indicator)
        all_records.extend(records)
        page += 1

    frame = pd.DataFrame(all_records)
    if frame.empty:
        raise DataSourceUnavailableError("World Bank", "no observations returned")

    frame["year"] = frame["year"].astype("Int64")
    if start_year is not None:
        frame = frame[frame["year"] >= start_year]
    if end_year is not None:
        frame = frame[frame["year"] <= end_year]
    frame = frame.dropna(subset=["value"]).sort_values(["country_code", "year"])
    logger.info("World Bank {}: {} observations", indicator, len(frame))
    return frame.reset_index(drop=True)
