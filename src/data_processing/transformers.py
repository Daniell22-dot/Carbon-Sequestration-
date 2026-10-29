"""Reusable dataframe transformations."""

from __future__ import annotations

from typing import Literal

import pandas as pd


def to_monthly(
    frame: pd.DataFrame,
    date_column: str = "date",
    value_columns: list[str] | None = None,
    aggregation: Literal["mean", "sum", "last", "first"] = "mean",
) -> pd.DataFrame:
    """Resample a table to month-start frequency.

    Args:
        frame: Input table containing ``date_column``.
        date_column: Name of the datetime column.
        value_columns: Columns to aggregate. Defaults to all numeric columns.
        aggregation: Aggregation function name.

    Returns:
        A month-indexed DataFrame with a ``date`` column.

    Raises:
        ValueError: If ``date_column`` is missing.
    """
    if date_column not in frame.columns:
        raise ValueError(f"Missing date column: {date_column}")

    working = frame.copy()
    working[date_column] = pd.to_datetime(working[date_column], errors="coerce")
    working = working.dropna(subset=[date_column]).set_index(date_column)

    columns = value_columns or list(working.select_dtypes(include="number").columns)
    if not columns:
        raise ValueError("No numeric columns available for monthly aggregation")

    resampled = working[columns].resample("MS").agg(aggregation)
    resampled.index.name = "date"
    return resampled.reset_index()


def resample_series(
    series: pd.Series,
    frequency: str = "YS",
    aggregation: str = "mean",
) -> pd.Series:
    """Resample a datetime-indexed series.

    Args:
        series: Series with a DatetimeIndex.
        frequency: pandas offset alias, e.g. ``"YS"`` or ``"MS"``.
        aggregation: Aggregation function name.

    Returns:
        The resampled series.

    Raises:
        ValueError: If the series index is not a DatetimeIndex.
    """
    if not isinstance(series.index, pd.DatetimeIndex):
        raise ValueError("resample_series requires a DatetimeIndex")
    return series.resample(frequency).agg(aggregation)


def add_rolling_statistics(
    frame: pd.DataFrame,
    column: str,
    windows: tuple[int, ...] = (12, 60),
    statistics: tuple[str, ...] = ("mean",),
) -> pd.DataFrame:
    """Add centered rolling statistics for a numeric column.

    Args:
        frame: Input table.
        column: Column to smooth.
        windows: Rolling window lengths in observations.
        statistics: Statistics to compute, e.g. ``"mean"`` or ``"std"``.

    Returns:
        A copy with ``{column}_roll{window}_{statistic}`` columns.

    Raises:
        ValueError: If ``column`` is absent.
    """
    if column not in frame.columns:
        raise ValueError(f"Missing column: {column}")

    enriched = frame.copy()
    for window in windows:
        for statistic in statistics:
            name = f"{column}_roll{window}_{statistic}"
            enriched[name] = (
                enriched[column]
                .rolling(window=window, min_periods=max(1, window // 2), center=True)
                .agg(statistic)
            )
    return enriched


def pivot_series(
    frame: pd.DataFrame,
    index: str,
    columns: str,
    values: str,
) -> pd.DataFrame:
    """Pivot long-form observations into a wide matrix.

    Args:
        frame: Long-form table.
        index: Column to use as the index.
        columns: Column whose values become output columns.
        values: Column of values to fill the matrix.

    Returns:
        The pivoted DataFrame.
    """
    return frame.pivot_table(index=index, columns=columns, values=values, aggfunc="mean")
