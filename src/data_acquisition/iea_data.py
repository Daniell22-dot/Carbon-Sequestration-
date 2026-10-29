"""IEA energy and CCUS data loading.

IEA data is distributed under licence and is not available through an open API.
This module validates and normalizes CSV exports obtained manually or through a
licensed feed; it never fabricates records.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.data_processing.validators import (
    assert_valid,
    validate_required_columns,
)
from src.utils.logging import get_logger

logger = get_logger(__name__)

IEA_REQUIRED_COLUMNS = ("country", "year", "indicator", "value")


def load_iea_csv(
    path: Path | str,
    required_columns: list[str] | None = None,
) -> pd.DataFrame:
    """Load and validate an IEA CSV export.

    Args:
        path: Path to a licensed IEA CSV export.
        required_columns: Columns that must be present. Defaults to
            ``country``, ``year``, ``indicator``, and ``value``.

    Returns:
        A normalized DataFrame sorted by country, indicator, and year.

    Raises:
        FileNotFoundError: If the file does not exist.
        DataValidationError: If required columns are missing or the file is empty.
    """
    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(f"IEA export not found: {source}")

    frame = pd.read_csv(source)
    required = required_columns or list(IEA_REQUIRED_COLUMNS)
    assert_valid(validate_required_columns(frame, required, "IEA export"))

    frame["year"] = pd.to_numeric(frame["year"], errors="coerce").astype("Int64")
    frame["value"] = pd.to_numeric(frame["value"], errors="coerce")
    frame = frame.dropna(subset=["year"]).sort_values(
        ["country", "indicator", "year"]
    )
    logger.info("Loaded {} IEA observations from {}", len(frame), source)
    return frame.reset_index(drop=True)
