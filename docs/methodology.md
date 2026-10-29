# Methodology

## Scope

This project models atmospheric CO2 concentrations, detects structural changes
in the record, generates conditional forecasts, and compares carbon dioxide
removal (CDR) methods on multiple criteria. It is an analytical aid, not a
policy prescription.

## Data validation

Every acquired dataset is validated before analysis:

- NOAA: required columns, datetime dtype, plausible CO2 range (100-1000 ppm),
  month bounds, duplicate dates, and coordinate bounds.
- Projects: unique identifiers, coordinate bounds, non-negative capacity, and
  plausible start years.
- Comparison: unique methods, risk in `[0, 1]`, TRL in `[1, 9]`, and
  `permanence_min <= permanence_max`.

Validation failures raise `DataValidationError` rather than silently dropping
records, except where cleaning explicitly documents a filter.

## Decomposition

`seasonal_decompose` from statsmodels is used when available, with
`extrapolate_trend="freq"` so that endpoints are populated. The fallback uses a
centered moving average for the trend and month-of-year mean residuals for the
seasonal component. Multiplicative decomposition requires statsmodels.

Assumptions:

- The seasonal pattern is stable over the sample.
- Additive decomposition is appropriate when seasonal amplitude is roughly
  constant in absolute terms; multiplicative when it scales with the level.

## Change points

Change points are located by binary segmentation. For each candidate split, a
Welch-style t-statistic compares segment means. A split is accepted when the
statistic exceeds `changepoint_threshold` (default 3.0) and both segments contain
at least `min_segment` observations. The procedure recurses up to
`max_changepoints`.

Limitations: binary segmentation can miss closely spaced changes and is sensitive
to the threshold. Detected dates are approximate to the sampling interval.

## Trend detection

- **Mann-Kendall**: non-parametric monotonic trend test with tie correction.
  Significance is assessed at `alpha = 0.05` (two-sided).
- **Sen's slope**: median of pairwise slopes, reported per year.
- **OLS**: ordinary least squares on observation order, reported per year with
  R-squared and a slope p-value.

Mann-Kendall detects monotonic association, not magnitude or causality. OLS
assumes independent errors; autocorrelated series can overstate significance, so
both tests are reported together.

## Forecasting

- **Auto**: SARIMA `(1,1,1)(0,1,1,12)` when statsmodels is available and the
  series has at least 24 observations; otherwise a seasonal linear model.
- **Linear**: OLS trend plus month-of-year mean residuals, with prediction
  intervals that widen with distance from the sample mean.
- **SARIMA**: `SARIMAX` with `trend="c"`, `enforce_stationarity=False`, and
  `enforce_invertibility=False` for numerical stability.

Intervals are model-based prediction intervals at the configured confidence
level (default 95%). They do not include structural uncertainty, policy shocks,
or measurement error beyond the residual variance.

Backtesting holds out the final `test_size` observations, refits on the training
tail, and reports MAE, RMSE, and MAPE.

## Method comparison

Reference ranges in `src/constants.py` are drawn from published literature and
industry reporting. Each criterion is min-max normalized across the included
methods, oriented so that higher scores are better:

| Criterion | Column | Direction |
| --- | --- | --- |
| Cost | `cost_mean` | lower is better |
| Permanence | `permanence_min` | higher is better |
| Scalability | `scalability_gt_year` | higher is better |
| Energy | `energy_gj_per_tco2` | lower is better |
| Technology readiness | `trl` | higher is better |
| Risk | `risk_score` | lower is better |

Composite scores are weighted sums of normalized criteria. Default weights are
cost 0.30, permanence 0.20, scalability 0.20, energy 0.10, TRL 0.10, and risk
0.10. Scores are relative to the methods included in a run and must not be
compared across runs with different method sets.

Pareto analysis marks methods not dominated on both cost and composite benefit.
Cost-effectiveness is composite score per USD/tCO2.

## Risk

Method risk blends reversal probability (40%), permanence risk (30%, decreasing
in log10 permanence), TRL risk (20%, decreasing in TRL), and energy intensity
risk (10%). Portfolio reversal probability is `1 - product(1 - p_i)` under an
independence assumption, which is optimistic when methods share climate or
policy exposure.

The Monte Carlo portfolio simulation draws annual delivery from a normal
distribution scaled by method risk, clips negative delivery to zero, and applies
stochastic reversal events. Output percentiles are illustrative.

## Reproducibility

- All randomness uses explicit seeds (`simulate_portfolio(seed=42)`).
- Cached payloads are content-addressed with SHA-256.
- Analysis outputs are written as CSV/JSON with stable column names.
- Tests run fully offline against fixtures in `tests/`.

## References

- IPCC AR6 Working Group III: https://www.ipcc.ch/report/ar6/wg3/
- NOAA GML CO2 trends: https://gml.noaa.gov/ccgg/trends/
- Hyndman & Athanasopoulos, *Forecasting: Principles and Practice* (3rd ed.):
  https://otexts.com/fpp3/
- Mann, H. B. (1945). Nonparametric tests against trend. *Econometrica*.
- Sen, P. K. (1968). Estimates of the regression coefficient based on Kendall's
  tau. *JASA*.
