"""Carbon removal project data acquisition.

The CDR Database does not expose a stable public API. This client therefore
supports either a configured JSON endpoint or a user-supplied CSV export. When
neither is available it fails loudly rather than fabricating project records.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import pandas as pd

from src.constants import RAW_DATA_DIR
from src.data_acquisition.base import BaseDownloader, DataSourceUnavailableError
from src.data_processing.cleaners import clean_projects
from src.data_processing.validators import assert_valid, validate_projects
from src.utils.logging import get_logger

logger = get_logger(__name__)

PROJECT_COLUMNS = (
    "project_id",
    "project_name",
    "method",
    "capacity_tco2_year",
    "status",
    "latitude",
    "longitude",
    "country",
    "start_year",
    "cost_per_ton",
    "funding_source",
)


def _records_from_payload(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [record for record in payload if isinstance(record, dict)]
    if isinstance(payload, dict):
        for key in ("projects", "data", "results", "records", "items"):
            value = payload.get(key)
            if isinstance(value, list):
                return [record for record in value if isinstance(record, dict)]
    raise DataSourceUnavailableError(
        "CDR Database", "payload does not contain a project list"
    )


def projects_from_records(records: Iterable[dict[str, Any]]) -> pd.DataFrame:
    """Build a project DataFrame from raw records.

    Args:
        records: Iterable of mappings using the documented project schema.

    Returns:
        A cleaned project DataFrame with canonical columns.

    Raises:
        DataValidationError: If the resulting table fails validation.
    """
    frame = pd.DataFrame(list(records))
    for column in PROJECT_COLUMNS:
        if column not in frame.columns:
            frame[column] = pd.NA
    frame = frame[list(PROJECT_COLUMNS)]
    cleaned = clean_projects(frame, drop_invalid_coordinates=False)
    assert_valid(validate_projects(cleaned))
    return cleaned


def load_cdr_projects_csv(path: Path | str) -> pd.DataFrame:
    """Load a user-supplied CDR project CSV export.

    Args:
        path: Path to a CSV using the documented project schema.

    Returns:
        A validated, cleaned project DataFrame.

    Raises:
        FileNotFoundError: If the file does not exist.
        DataValidationError: If the table fails schema validation.
    """
    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(f"Project CSV not found: {source}")
    frame = pd.read_csv(source)
    return projects_from_records(frame.to_dict(orient="records"))


def download_cdr_projects(
    endpoint: str | None = None,
    api_key: str | None = None,
    cache_dir: Path | str = RAW_DATA_DIR / "cdr_projects",
    cache_hours: int = 168,
    force: bool = False,
) -> pd.DataFrame:
    """Download carbon removal projects from a configured JSON endpoint.

    Args:
        endpoint: JSON endpoint returning a project list or an object with a
            ``projects``/``data``/``results`` array. Required.
        api_key: Optional bearer token.
        cache_dir: Cache directory for the raw payload.
        cache_hours: Cache freshness window in hours.
        force: Refetch even when a fresh cache entry exists.

    Returns:
        A validated, cleaned project DataFrame.

    Raises:
        DataSourceUnavailableError: If no endpoint is configured or the payload
            cannot be retrieved or interpreted.
    """
    if not endpoint:
        raise DataSourceUnavailableError(
            "CDR Database",
            "no endpoint configured",
            fallback=(
                "set data_sources.cdr.api_endpoint in config.yaml or use "
                "load_cdr_projects_csv() with an exported dataset"
            ),
        )

    headers = {"Authorization": f"Bearer {api_key}"} if api_key else None
    downloader = BaseDownloader(
        cache_dir=cache_dir,
        cache_hours=cache_hours,
        source_name="CDR Database",
    )
    payload = downloader.fetch(
        endpoint,
        headers=headers,
        suffix=".json",
        cache_key="cdr_projects",
        force=force,
    )
    try:
        decoded = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise DataSourceUnavailableError(
            "CDR Database", f"invalid JSON payload: {error}"
        ) from error

    records = _records_from_payload(decoded)
    if not records:
        raise DataSourceUnavailableError("CDR Database", "no project records returned")
    frame = projects_from_records(records)
    logger.info("Loaded {} CDR project records", len(frame))
    return frame
