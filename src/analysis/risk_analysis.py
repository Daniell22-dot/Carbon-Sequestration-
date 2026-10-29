"""Risk quantification for sequestration methods and portfolios."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.utils.helpers import clamp
from src.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class RiskAssessment:
    """Risk profile for a single sequestration method."""

    method: str
    reversal_probability: float
    permanence_years: float
    trl: float
    energy_gj_per_tco2: float
    score: float
    level: str

    def to_dict(self) -> dict[str, object]:
        """Return the assessment as a plain dictionary."""
        return {
            "method": self.method,
            "reversal_probability": self.reversal_probability,
            "permanence_years": self.permanence_years,
            "trl": self.trl,
            "energy_gj_per_tco2": self.energy_gj_per_tco2,
            "risk_score": self.score,
            "risk_level": self.level,
        }


def _risk_level(score: float) -> str:
    if score < 0.25:
        return "low"
    if score < 0.5:
        return "moderate"
    if score < 0.75:
        return "high"
    return "very high"


def assess_method_risk(row: Mapping[str, object]) -> RiskAssessment:
    """Compute a composite risk score for one method.

    The score blends reversal probability, permanence, technology readiness,
    and energy intensity. Each component is normalized to ``[0, 1]`` where
    higher means riskier.

    Args:
        row: Mapping containing ``method``, ``reversal_probability``,
            ``permanence_min``, ``trl``, and ``energy_gj_per_tco2``.

    Returns:
        A :class:`RiskAssessment`.

    Raises:
        ValueError: If required fields are missing.
    """
    required = ("method", "reversal_probability", "permanence_min", "trl", "energy_gj_per_tco2")
    missing = [field for field in required if field not in row]
    if missing:
        raise ValueError(f"Missing risk fields: {', '.join(missing)}")

    reversal = clamp(float(row["reversal_probability"]))
    permanence = max(1.0, float(row["permanence_min"]))
    permanence_risk = clamp(1.0 - np.log10(permanence) / 4.0)
    trl = clamp(float(row["trl"]), 1.0, 9.0)
    trl_risk = clamp((9.0 - trl) / 8.0)
    energy = max(0.0, float(row["energy_gj_per_tco2"]))
    energy_risk = clamp(energy / 10.0)

    score = (
        0.40 * reversal
        + 0.30 * permanence_risk
        + 0.20 * trl_risk
        + 0.10 * energy_risk
    )
    return RiskAssessment(
        method=str(row["method"]),
        reversal_probability=reversal,
        permanence_years=permanence,
        trl=trl,
        energy_gj_per_tco2=energy,
        score=float(score),
        level=_risk_level(float(score)),
    )


def assess_portfolio_risk(
    frame: pd.DataFrame,
    weights: Mapping[str, float] | None = None,
) -> dict[str, object]:
    """Aggregate method-level risk into a portfolio risk summary.

    Args:
        frame: Comparison table with the fields required by
            :func:`assess_method_risk`.
        weights: Optional mapping of method to portfolio weight. Defaults to
            equal weights.

    Returns:
        Dictionary containing individual assessments, weighted risk score,
        level, and the probability that at least one method reverses.

    Raises:
        ValueError: If ``frame`` is empty.
    """
    if frame.empty:
        raise ValueError("Cannot assess risk for an empty table")

    methods = [str(value) for value in frame["method"].tolist()]
    resolved_weights = {
        method: float(weights.get(method, 1.0 / len(methods))) if weights else 1.0 / len(methods)
        for method in methods
    }
    total = sum(resolved_weights.values())
    if total <= 0:
        raise ValueError("Portfolio weights must sum to a positive value")
    resolved_weights = {key: value / total for key, value in resolved_weights.items()}

    assessments = [assess_method_risk(row) for row in frame.to_dict(orient="records")]
    weighted_score = sum(
        assessment.score * resolved_weights[assessment.method]
        for assessment in assessments
    )

    no_reversal = 1.0
    for assessment in assessments:
        no_reversal *= 1.0 - assessment.reversal_probability
    portfolio_reversal = 1.0 - no_reversal

    return {
        "assessments": [assessment.to_dict() for assessment in assessments],
        "weights": resolved_weights,
        "weighted_risk_score": float(weighted_score),
        "risk_level": _risk_level(float(weighted_score)),
        "portfolio_reversal_probability": float(portfolio_reversal),
    }


def simulate_portfolio(
    frame: pd.DataFrame,
    weights: Mapping[str, float] | None = None,
    years: int = 10,
    n_simulations: int = 1000,
    seed: int | None = 42,
) -> pd.DataFrame:
    """Simulate cumulative sequestration under delivery uncertainty.

    Annual delivery for each method is drawn from a normal distribution whose
    mean is the method capacity and whose standard deviation scales with the
    method risk score. Reversal events are modelled as Bernoulli draws that
    remove a fraction of cumulative storage.

    Args:
        frame: Table with ``method`` and ``capacity_tco2_year`` columns, plus
            the fields required by :func:`assess_method_risk`.
        weights: Optional method allocation weights.
        years: Simulation horizon in years.
        n_simulations: Number of Monte Carlo paths.
        seed: Random seed for reproducibility.

    Returns:
        DataFrame summarizing per-year cumulative storage percentiles.

    Raises:
        ValueError: If inputs are invalid.
    """
    if years <= 0 or n_simulations <= 0:
        raise ValueError("years and n_simulations must be positive")
    if "capacity_tco2_year" not in frame.columns:
        raise ValueError("frame must contain capacity_tco2_year")

    rng = np.random.default_rng(seed)
    methods = [str(value) for value in frame["method"].tolist()]
    if weights:
        total = sum(weights.get(method, 0.0) for method in methods)
        if total <= 0:
            raise ValueError("weights must include at least one positive value")
        allocations = np.array([weights.get(method, 0.0) / total for method in methods])
    else:
        allocations = np.full(len(methods), 1.0 / len(methods))

    capacities = pd.to_numeric(frame["capacity_tco2_year"], errors="coerce").fillna(0.0).to_numpy()
    assessments = [assess_method_risk(row) for row in frame.to_dict(orient="records")]
    risks = np.array([assessment.score for assessment in assessments])
    reversals = np.array([assessment.reversal_probability for assessment in assessments])

    allocated = capacities * allocations
    paths = np.zeros((n_simulations, years), dtype=float)
    cumulative = np.zeros(n_simulations, dtype=float)

    for year in range(years):
        mean_delivery = allocated * (1.0 + 0.02 * year)
        sigma = mean_delivery * (0.10 + 0.30 * risks)
        delivery = rng.normal(mean_delivery, sigma, size=(n_simulations, len(methods)))
        delivery = np.clip(delivery, 0.0, None)
        annual = delivery.sum(axis=1)
        cumulative += annual
        reversal_draws = rng.random((n_simulations, len(methods))) < (reversals / 10.0)
        reversed_fraction = (reversal_draws * 0.25).sum(axis=1)
        cumulative = cumulative * (1.0 - np.clip(reversed_fraction, 0.0, 1.0))
        paths[:, year] = cumulative

    summary = pd.DataFrame(
        {
            "year": np.arange(1, years + 1),
            "p10": np.percentile(paths, 10, axis=0),
            "p50": np.percentile(paths, 50, axis=0),
            "p90": np.percentile(paths, 90, axis=0),
            "mean": paths.mean(axis=0),
            "std": paths.std(axis=0),
        }
    )
    logger.info(
        "Simulated {} paths over {} years (median cumulative {:.1f} tCO2)",
        n_simulations,
        years,
        float(summary["p50"].iloc[-1]),
    )
    return summary
