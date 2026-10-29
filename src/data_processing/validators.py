"""Schema and integrity validation for acquired and derived datasets."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field

import pandas as pd

from src.data_acquisition.base import DataValidationError


@dataclass(frozen=True)
class ValidationIssue:
    """A single validation finding."""

    field: str
    message: str
    severity: str = "error"


@dataclass(frozen=True)
class ValidationResult:
    """Outcome of a dataset validation pass."""

    dataset: str
    row_count: int
    issues: tuple[ValidationIssue, ...] = field(default_factory=tuple)

    @property
    def passed(self) -> bool:
        """Return ``True`` when no error-severity issues were found."""
        return not any(issue.severity == "error" for issue in self.issues)

    @property
    def errors(self) -> tuple[ValidationIssue, ...]:
        """Return only error-severity issues."""
        return tuple(issue for issue in self.issues if issue.severity == "error")

    def summary(self) -> str:
        """Render a compact human-readable summary."""
        if self.passed:
            return f"{self.dataset}: OK ({self.row_count} rows)"
        details = "; ".join(f"{issue.field}: {issue.message}" for issue in self.errors)
        return f"{self.dataset}: FAILED ({self.row_count} rows) - {details}"


def assert_valid(result: ValidationResult) -> ValidationResult:
    """Raise :class:`DataValidationError` when a validation result failed."""
    if not result.passed:
        raise DataValidationError(result.summary())
    return result


def _missing_columns(
    frame: pd.DataFrame, required: Iterable[str]
) -> list[ValidationIssue]:
    return [
        ValidationIssue(column, "required column is missing")
        for column in required
        if column not in frame.columns
    ]


def validate_noaa_data(frame: pd.DataFrame) -> ValidationResult:
    """Validate a NOAA CO2 DataFrame against the documented schema.

    Args:
        frame: Candidate DataFrame.

    Returns:
        A :class:`ValidationResult` describing any problems found.
    """
    issues: list[ValidationIssue] = []
    issues.extend(
        _missing_columns(
            frame,
            (
                "date",
                "year",
                "month",
                "co2_ppm",
                "station",
                "latitude",
                "longitude",
            ),
        )
    )
    if frame.empty:
        issues.append(ValidationIssue("rows", "dataset is empty"))
        return ValidationResult("NOAA CO2", 0, tuple(issues))

    if not issues:
        if not pd.api.types.is_datetime64_any_dtype(frame["date"]):
            issues.append(ValidationIssue("date", "must be datetime64"))
        if frame["co2_ppm"].isna().all():
            issues.append(ValidationIssue("co2_ppm", "all values are missing"))
        else:
            valid = frame["co2_ppm"].dropna()
            if ((valid < 100) | (valid > 1000)).any():
                issues.append(
                    ValidationIssue("co2_ppm", "values outside plausible range 100-1000 ppm")
                )
        if frame["month"].dropna().between(1, 12).all() is False:
            issues.append(ValidationIssue("month", "values must be between 1 and 12"))
        if frame["date"].duplicated().any():
            issues.append(ValidationIssue("date", "duplicate observation dates"))
        if frame["latitude"].dropna().between(-90, 90).all() is False:
            issues.append(ValidationIssue("latitude", "values must be between -90 and 90"))
        if frame["longitude"].dropna().between(-180, 180).all() is False:
            issues.append(ValidationIssue("longitude", "values must be between -180 and 180"))

    return ValidationResult("NOAA CO2", len(frame), tuple(issues))


def validate_projects(frame: pd.DataFrame) -> ValidationResult:
    """Validate a carbon removal project DataFrame.

    Args:
        frame: Candidate project table.

    Returns:
        A :class:`ValidationResult` describing any problems found.
    """
    required = (
        "project_id",
        "project_name",
        "method",
        "capacity_tco2_year",
        "status",
        "latitude",
        "longitude",
        "country",
        "start_year",
    )
    issues = _missing_columns(frame, required)
    if frame.empty:
        issues.append(ValidationIssue("rows", "dataset is empty"))
        return ValidationResult("CDR projects", 0, tuple(issues))

    if not issues:
        if frame["project_id"].duplicated().any():
            issues.append(ValidationIssue("project_id", "duplicate identifiers"))
        if frame["latitude"].dropna().between(-90, 90).all() is False:
            issues.append(ValidationIssue("latitude", "values must be between -90 and 90"))
        if frame["longitude"].dropna().between(-180, 180).all() is False:
            issues.append(ValidationIssue("longitude", "values must be between -180 and 180"))
        capacity = pd.to_numeric(frame["capacity_tco2_year"], errors="coerce")
        if capacity.dropna().lt(0).any():
            issues.append(
                ValidationIssue("capacity_tco2_year", "capacity must be non-negative")
            )
        years = pd.to_numeric(frame["start_year"], errors="coerce")
        if years.dropna().lt(1900).any() or years.dropna().gt(2100).any():
            issues.append(ValidationIssue("start_year", "must be between 1900 and 2100"))

    return ValidationResult("CDR projects", len(frame), tuple(issues))


def validate_comparison(frame: pd.DataFrame) -> ValidationResult:
    """Validate a method comparison matrix.

    Args:
        frame: Candidate comparison table.

    Returns:
        A :class:`ValidationResult` describing any problems found.
    """
    required = (
        "method",
        "cost_mean",
        "permanence_min",
        "permanence_max",
        "energy_gj_per_tco2",
        "trl",
        "scalability_gt_year",
        "risk_score",
    )
    issues = _missing_columns(frame, required)
    if frame.empty:
        issues.append(ValidationIssue("rows", "dataset is empty"))
        return ValidationResult("Method comparison", 0, tuple(issues))

    if not issues:
        if frame["method"].duplicated().any():
            issues.append(ValidationIssue("method", "duplicate method rows"))
        if frame["risk_score"].dropna().between(0, 1).all() is False:
            issues.append(ValidationIssue("risk_score", "must be between 0 and 1"))
        if frame["trl"].dropna().between(1, 9).all() is False:
            issues.append(ValidationIssue("trl", "must be between 1 and 9"))
        if frame["permanence_min"].dropna().gt(frame["permanence_max"]).any():
            issues.append(
                ValidationIssue("permanence_min", "must not exceed permanence_max")
            )

    return ValidationResult("Method comparison", len(frame), tuple(issues))


def validate_required_columns(
    frame: pd.DataFrame,
    required: Iterable[str],
    dataset: str,
) -> ValidationResult:
    """Validate that a DataFrame contains required columns and rows.

    Args:
        frame: Candidate table.
        required: Required column names.
        dataset: Label used in the result.

    Returns:
        A :class:`ValidationResult`.
    """
    issues = _missing_columns(frame, required)
    if frame.empty:
        issues.append(ValidationIssue("rows", "dataset is empty"))
    return ValidationResult(dataset, len(frame), tuple(issues))


def validate_schema_types(
    frame: pd.DataFrame,
    expected: Mapping[str, str],
) -> ValidationResult:
    """Check pandas dtype families against an expected mapping.

    Args:
        frame: Candidate table.
        expected: Mapping of column name to one of ``datetime``, ``numeric``,
            or ``string``.

    Returns:
        A :class:`ValidationResult`.
    """
    issues: list[ValidationIssue] = []
    for column, family in expected.items():
        if column not in frame.columns:
            issues.append(ValidationIssue(column, "required column is missing"))
            continue
        series = frame[column]
        if family == "datetime" and not pd.api.types.is_datetime64_any_dtype(series):
            issues.append(ValidationIssue(column, "expected datetime dtype"))
        elif family == "numeric" and not pd.api.types.is_numeric_dtype(series):
            issues.append(ValidationIssue(column, "expected numeric dtype"))
        elif family == "string" and pd.api.types.is_numeric_dtype(series):
            issues.append(ValidationIssue(column, "expected string dtype"))
    return ValidationResult("schema", len(frame), tuple(issues))
