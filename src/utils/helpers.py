"""General-purpose helpers: retries, hashing, and numeric utilities."""

from __future__ import annotations

import functools
import re
import time
from collections.abc import Callable
from typing import Any, TypeVar

T = TypeVar("T")


def retry_with_backoff(
    max_retries: int = 3,
    backoff_factor: float = 2.0,
    initial_delay: float = 1.0,
    exceptions: tuple[type[BaseException], ...] = (Exception,),
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorate a callable with exponential backoff retries.

    Args:
        max_retries: Maximum number of attempts after the first failure.
        backoff_factor: Multiplier applied to the delay after each failure.
        initial_delay: Delay in seconds before the first retry.
        exceptions: Exception types that trigger a retry.

    Returns:
        A decorated callable that retries on the configured exceptions.
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            delay = initial_delay
            last_error: BaseException | None = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as error:  # noqa: PERF203 - retry loop
                    last_error = error
                    if attempt >= max_retries:
                        break
                    time.sleep(delay)
                    delay *= backoff_factor
            assert last_error is not None
            raise last_error

        return wrapper

    return decorator


def slugify(value: str) -> str:
    """Convert text to a filesystem-safe slug."""
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower())
    return cleaned.strip("-") or "item"


def safe_divide(numerator: float, denominator: float) -> float:
    """Return ``numerator / denominator`` or NaN when the denominator is zero."""
    if denominator == 0:
        return float("nan")
    return numerator / denominator


def clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    """Clamp ``value`` to the inclusive ``[lower, upper]`` interval."""
    return max(lower, min(upper, value))


def normalize_score(
    value: float,
    min_val: float,
    max_val: float,
    higher_is_better: bool = True,
) -> float:
    """Normalize a value onto a 0-1 scale.

    Args:
        value: Raw value to normalize.
        min_val: Minimum possible value.
        max_val: Maximum possible value.
        higher_is_better: When ``True``, larger raw values yield larger scores.

    Returns:
        A score between 0 and 1. Returns 0.5 when the range is degenerate.
    """
    if max_val == min_val:
        return 0.5
    normalized = (value - min_val) / (max_val - min_val)
    normalized = clamp(normalized)
    return normalized if higher_is_better else 1.0 - normalized


def calculate_cagr(start_value: float, end_value: float, years: float) -> float:
    """Calculate compound annual growth rate as a percentage.

    Args:
        start_value: Initial value; must be positive.
        end_value: Final value; must be non-negative.
        years: Elapsed time in years; must be positive.

    Returns:
        CAGR in percent, or NaN when inputs are invalid.
    """
    if start_value <= 0 or years <= 0 or end_value < 0:
        return float("nan")
    return ((end_value / start_value) ** (1.0 / years) - 1.0) * 100.0
