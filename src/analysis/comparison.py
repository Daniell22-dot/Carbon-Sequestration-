"""Multi-criteria comparison and Pareto analysis of sequestration methods."""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import pandas as pd

from src.constants import DEFAULT_METHOD_WEIGHTS, METHOD_CATALOG, PER_HECTARE_RATES
from src.data_processing.validators import assert_valid, validate_comparison
from src.utils.logging import get_logger

logger = get_logger(__name__)

#: criterion -> (column, higher_is_better)
CRITERIA: dict[str, tuple[str, bool]] = {
    "cost": ("cost_mean", False),
    "permanence": ("permanence_min", True),
    "scalability": ("scalability_gt_year", True),
    "energy": ("energy_gj_per_tco2", False),
    "trl": ("trl", True),
    "risk": ("risk_score", False),
}


def build_comparison_table(
    methods: list[str] | None = None,
    catalog: Mapping[str, Mapping[str, object]] | None = None,
) -> pd.DataFrame:
    """Build a comparison table from the literature-derived method catalog.

    Args:
        methods: Method identifiers to include. Defaults to all catalog keys.
        catalog: Optional replacement catalog (useful for tests or updates).

    Returns:
        DataFrame with one row per method and all comparison schema fields.

    Raises:
        KeyError: If a requested method is absent from the catalog.
        DataValidationError: If the resulting table fails validation.
    """
    source = catalog or METHOD_CATALOG
    selected = methods or list(source.keys())
    records: list[dict[str, object]] = []
    for method in selected:
        if method not in source:
            raise KeyError(f"Unknown method: {method}")
        record = {"method": method, **source[method]}
        rate = PER_HECTARE_RATES.get(method)
        record["per_hectare_min"] = rate[0] if rate else np.nan
        record["per_hectare_max"] = rate[1] if rate else np.nan
        records.append(record)

    frame = pd.DataFrame(records)
    for column in (
        "sequestration_min",
        "sequestration_max",
        "sequestration_mean",
        "cost_min",
        "cost_max",
        "cost_mean",
        "permanence_min",
        "permanence_max",
        "energy_gj_per_tco2",
        "trl",
        "scalability_gt_year",
        "risk_score",
        "per_hectare_min",
        "per_hectare_max",
    ):
        if column in frame.columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")

    assert_valid(validate_comparison(frame))
    return frame


def score_methods(
    frame: pd.DataFrame,
    weights: Mapping[str, float] | None = None,
) -> pd.DataFrame:
    """Normalize criteria and compute a weighted composite score.

    Args:
        frame: Comparison table containing the columns in :data:`CRITERIA`.
        weights: Criterion weights. Defaults to
            :data:`src.constants.DEFAULT_METHOD_WEIGHTS`. Weights are rescaled
            to sum to one.

    Returns:
        A copy with ``score_*`` columns, ``composite_score``, and ``rank``.

    Raises:
        ValueError: If a criterion column is missing or weights are invalid.
    """
    resolved_weights = dict(weights or DEFAULT_METHOD_WEIGHTS)
    missing = set(resolved_weights).difference(CRITERIA)
    if missing:
        raise ValueError(f"Unknown criteria in weights: {', '.join(sorted(missing))}")
    for criterion, (column, _) in CRITERIA.items():
        if criterion in resolved_weights and column not in frame.columns:
            raise ValueError(f"Missing criterion column: {column}")

    total_weight = float(sum(resolved_weights.values()))
    if total_weight <= 0:
        raise ValueError("Weights must sum to a positive value")

    scored = frame.copy()
    composite = np.zeros(len(scored), dtype=float)
    for criterion, weight in resolved_weights.items():
        column, higher_is_better = CRITERIA[criterion]
        values = pd.to_numeric(scored[column], errors="coerce")
        if values.notna().sum() == 0:
            scores = pd.Series(0.5, index=scored.index)
        else:
            minimum = float(values.min())
            maximum = float(values.max())
            if maximum == minimum:
                scores = pd.Series(0.5, index=scored.index)
            else:
                scores = ((values - minimum) / (maximum - minimum)).clip(0.0, 1.0)
                if not higher_is_better:
                    scores = 1.0 - scores
            scores = scores.fillna(0.0)
        scored[f"score_{criterion}"] = scores.astype(float)
        composite += (scores.astype(float) * (weight / total_weight)).to_numpy()

    scored["composite_score"] = composite
    scored["rank"] = scored["composite_score"].rank(
        ascending=False, method="min"
    ).astype(int)
    return scored.sort_values("rank").reset_index(drop=True)


def pareto_frontier(
    scored: pd.DataFrame,
    cost_column: str = "cost_mean",
    benefit_column: str = "composite_score",
    lower_cost_is_better: bool = True,
) -> pd.DataFrame:
    """Mark Pareto-optimal methods on cost and benefit.

    A method is Pareto-optimal when no other method is at least as good on both
    axes and strictly better on one.

    Args:
        scored: Scored comparison table.
        cost_column: Cost axis column.
        benefit_column: Benefit axis column.
        lower_cost_is_better: Direction of the cost axis.

    Returns:
        A copy sorted by cost with a boolean ``pareto_optimal`` column.

    Raises:
        ValueError: If required columns are missing.
    """
    for column in (cost_column, benefit_column):
        if column not in scored.columns:
            raise ValueError(f"Missing column: {column}")

    ordered = scored.sort_values(cost_column, ascending=lower_cost_is_better).copy()
    costs = pd.to_numeric(ordered[cost_column], errors="coerce").to_numpy(dtype=float)
    benefits = pd.to_numeric(ordered[benefit_column], errors="coerce").to_numpy(dtype=float)

    optimal = np.zeros(len(ordered), dtype=bool)
    best_benefit = -np.inf
    for position, (cost, benefit) in enumerate(zip(costs, benefits, strict=True)):
        if np.isnan(cost) or np.isnan(benefit):
            continue
        if benefit > best_benefit:
            optimal[position] = True
            best_benefit = benefit
    ordered["pareto_optimal"] = optimal
    return ordered.reset_index(drop=True)


def cost_effectiveness(
    scored: pd.DataFrame,
    benefit_column: str = "composite_score",
    cost_column: str = "cost_mean",
) -> pd.DataFrame:
    """Add a benefit-per-dollar cost-effectiveness column.

    Args:
        scored: Scored comparison table.
        benefit_column: Benefit axis column.
        cost_column: Cost axis column.

    Returns:
        A copy with ``benefit_per_cost`` and descending ``cost_effectiveness_rank``.
    """
    result = scored.copy()
    benefit = pd.to_numeric(result[benefit_column], errors="coerce")
    cost = pd.to_numeric(result[cost_column], errors="coerce").replace(0, np.nan)
    result["benefit_per_cost"] = benefit / cost
    result["cost_effectiveness_rank"] = result["benefit_per_cost"].rank(
        ascending=False, method="min"
    )
    return result.sort_values("cost_effectiveness_rank").reset_index(drop=True)
