"""Cleaning routines that normalize raw acquired data."""

from __future__ import annotations

import pandas as pd

from src.utils.logging import get_logger

logger = get_logger(__name__)

_METHOD_ALIASES = {
    "dac": "dac",
    "direct air capture": "dac",
    "direct air capture (dac)": "dac",
    "beccs": "beccs",
    "bioenergy with carbon capture and storage": "beccs",
    "biochar": "biochar",
    "forestry": "forestry",
    "afforestation": "forestry",
    "reforestation": "forestry",
    "afforestation and reforestation": "forestry",
    "erw": "erw",
    "enhanced rock weathering": "erw",
    "enhanced weathering": "erw",
}


def normalize_method_name(value: str) -> str:
    """Map free-text method labels onto canonical method identifiers.

    Args:
        value: Raw method label.

    Returns:
        Canonical lowercase method identifier, or a slug of the input when
        unrecognized.
    """
    key = str(value).strip().lower()
    if key in _METHOD_ALIASES:
        return _METHOD_ALIASES[key]
    slug = "".join(character if character.isalnum() else "_" for character in key)
    return slug.strip("_")


def clean_noaa(frame: pd.DataFrame, interpolate: bool = False) -> pd.DataFrame:
    """Normalize a NOAA CO2 DataFrame.

    Args:
        frame: Raw or parsed NOAA data.
        interpolate: When ``True``, linearly interpolate gaps in ``co2_ppm``
            and ``co2_deseasonalized`` and record which rows were filled.

    Returns:
        A cleaned copy sorted by date with canonical dtypes.

    Raises:
        ValueError: If required columns are absent.
    """
    required = {"date", "year", "month", "co2_ppm"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"clean_noaa missing columns: {', '.join(sorted(missing))}")

    cleaned = frame.copy()
    cleaned["date"] = pd.to_datetime(cleaned["date"], errors="coerce")
    for column in ("year", "month", "co2_ppm", "co2_deseasonalized"):
        if column in cleaned.columns:
            cleaned[column] = pd.to_numeric(cleaned[column], errors="coerce")

    cleaned = cleaned.dropna(subset=["date"]).sort_values("date")
    cleaned = cleaned.drop_duplicates(subset=["date"], keep="last").reset_index(drop=True)
    cleaned["year"] = cleaned["date"].dt.year
    cleaned["month"] = cleaned["date"].dt.month

    cleaned["is_interpolated"] = False
    if interpolate:
        for column in ("co2_ppm", "co2_deseasonalized"):
            if column in cleaned.columns:
                missing_mask = cleaned[column].isna()
                if missing_mask.any():
                    cleaned[column] = cleaned[column].interpolate(
                        method="linear", limit_direction="both"
                    )
                    cleaned.loc[missing_mask, "is_interpolated"] = True

    logger.debug("clean_noaa: {} rows retained", len(cleaned))
    return cleaned


def clean_projects(
    frame: pd.DataFrame,
    drop_invalid_coordinates: bool = True,
) -> pd.DataFrame:
    """Normalize a carbon removal project table.

    Args:
        frame: Raw project data.
        drop_invalid_coordinates: Drop rows whose coordinates fall outside
            valid latitude/longitude bounds.

    Returns:
        A cleaned copy with canonical method names and numeric fields.

    Raises:
        ValueError: If required columns are absent.
    """
    required = {
        "project_id",
        "project_name",
        "method",
        "capacity_tco2_year",
        "status",
        "latitude",
        "longitude",
        "country",
        "start_year",
    }
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"clean_projects missing columns: {', '.join(sorted(missing))}")

    cleaned = frame.copy()
    cleaned["project_id"] = cleaned["project_id"].astype(str).str.strip()
    cleaned["project_name"] = cleaned["project_name"].astype(str).str.strip()
    cleaned["method"] = cleaned["method"].map(normalize_method_name)
    cleaned["status"] = cleaned["status"].astype(str).str.strip().str.title()
    cleaned["country"] = (
        cleaned["country"].astype(str).str.strip().str.upper().str.slice(0, 3)
    )

    for column in ("capacity_tco2_year", "latitude", "longitude", "cost_per_ton"):
        if column in cleaned.columns:
            cleaned[column] = pd.to_numeric(cleaned[column], errors="coerce")
    for column in ("start_year",):
        cleaned[column] = pd.to_numeric(cleaned[column], errors="coerce").astype("Int64")

    if drop_invalid_coordinates:
        valid = (
            cleaned["latitude"].between(-90, 90)
            & cleaned["longitude"].between(-180, 180)
        )
        dropped = int((~valid).sum())
        if dropped:
            logger.warning("clean_projects: dropping {} rows with invalid coordinates", dropped)
        cleaned = cleaned[valid]

    cleaned = cleaned.drop_duplicates(subset=["project_id"], keep="last")
    return cleaned.reset_index(drop=True)


def coerce_numeric(
    frame: pd.DataFrame,
    columns: list[str] | None = None,
) -> pd.DataFrame:
    """Coerce selected columns to numeric, replacing failures with NaN.

    Args:
        frame: Input table.
        columns: Columns to coerce; defaults to all object columns.

    Returns:
        A copy with coerced columns.
    """
    cleaned = frame.copy()
    targets = columns or list(cleaned.select_dtypes(include="object").columns)
    for column in targets:
        if column in cleaned.columns:
            cleaned[column] = pd.to_numeric(cleaned[column], errors="coerce")
    return cleaned
