# API Reference

## Configuration

- `src.config.load_config(path=None) -> Config`
- `src.config.config_from_dict(raw) -> Config`
- `Config.ensure_directories()`

Dataclasses: `Config`, `DataSourcesConfig`, `NOAAConfig`, `CDRConfig`,
`WorldBankConfig`, `OpenAlexConfig`, `AnalysisConfig`, `ReportingConfig`,
`PathsConfig`.

## Data acquisition

All clients inherit `src.data_acquisition.base.BaseDownloader`, which provides:

- TTL cache with `<name>.meta.json` provenance sidecars
- Exponential backoff retries
- Stale-cache fallback when the network fails
- Optional payload validation before caching

Exceptions:

- `DataAcquisitionError`
- `DataSourceUnavailableError(source, reason, fallback=None)`
- `DataValidationError`

### NOAA

```python
from src.data_acquisition.noaa_co2 import download_noaa_co2, parse_noaa_monthly

df = download_noaa_co2(station="mlo", start_year=1990)
```

Returns columns: `date`, `year`, `month`, `co2_ppm`, `co2_deseasonalized`,
`station`, `latitude`, `longitude`, `elevation_m`.

### CDR projects

```python
from src.data_acquisition.cdr_database import (
    download_cdr_projects,
    load_cdr_projects_csv,
    projects_from_records,
)
```

`download_cdr_projects` requires `data_sources.cdr.api_endpoint`. Without an
endpoint it raises `DataSourceUnavailableError`; use `load_cdr_projects_csv` for
licensed exports.

### World Bank

```python
from src.data_acquisition.world_bank import download_world_bank_indicator

df = download_world_bank_indicator("EN.GHG.CO2.MT.CE.AR5", start_year=2000)
```

### IEA

```python
from src.data_acquisition.iea_data import load_iea_csv

df = load_iea_csv("data/external/iea_export.csv")
```

### Literature

```python
from src.data_acquisition.literature import search_openalex

works = search_openalex("enhanced rock weathering", limit=25, mailto="you@example.org")
```

## Data processing

- `validate_noaa_data(df) -> ValidationResult`
- `validate_projects(df) -> ValidationResult`
- `validate_comparison(df) -> ValidationResult`
- `assert_valid(result) -> ValidationResult`
- `clean_noaa(df, interpolate=False) -> DataFrame`
- `clean_projects(df) -> DataFrame`
- `to_monthly(df, date_column="date", aggregation="mean") -> DataFrame`
- `resample_series(series, frequency="YS") -> Series`
- `add_rolling_statistics(df, column, windows=(12, 60)) -> DataFrame`

`ValidationResult` exposes `passed`, `errors`, and `summary()`.

## Analysis

### Time series

```python
from src.analysis.time_series import CarbonTimeSeriesAnalyzer

analyzer = CarbonTimeSeriesAnalyzer(seasonal_period=12, confidence_level=0.95)
decomposition = analyzer.decompose(series)
points = analyzer.detect_changepoints(series)
growth = analyzer.calculate_growth_rates(series)
forecast = analyzer.forecast(series, horizon=20, model="auto")
stationarity = analyzer.stationarity_test(series)
```

Dataclasses: `DecompositionResult`, `ChangePoint`, `GrowthResult`,
`ForecastResult`, `StationarityResult`.

### Trends

- `mann_kendall(series, periods_per_year=12) -> MannKendallResult`
- `sen_slope(series, periods_per_year=12) -> float`
- `linear_trend(series, periods_per_year=12) -> LinearTrendResult`
- `rolling_trend(series, window=60) -> Series`
- `summarize_trend(series) -> dict`

### Forecasting

- `forecast_series(series, horizon, model, confidence_level, seasonal_period)`
- `backtest(series, model, test_size) -> dict`
- `compare_forecast_methods(series, test_size, models) -> DataFrame`
- `scenario_forecast(base, adjustments, annual_growth_percent=None) -> DataFrame`

### Comparison

- `build_comparison_table(methods=None) -> DataFrame`
- `score_methods(frame, weights=None) -> DataFrame`
- `pareto_frontier(scored) -> DataFrame`
- `cost_effectiveness(scored) -> DataFrame`

Criterion directions: cost lower-is-better; permanence, scalability, and TRL
higher-is-better; energy and risk lower-is-better.

### Risk

- `assess_method_risk(row) -> RiskAssessment`
- `assess_portfolio_risk(frame, weights=None) -> dict`
- `simulate_portfolio(frame, weights=None, years=10, n_simulations=1000, seed=42)`

## Visualization

- `src.visualization.static_plots`: `plot_co2_series`, `plot_decomposition`,
  `plot_forecast`, `plot_method_comparison`, `plot_pareto`
- `src.visualization.interactive`: `co2_figure`, `forecast_figure`,
  `save_interactive` (requires plotly)
- `src.visualization.maps`: `stations_geodataframe`, `projects_geodataframe`,
  `save_geopackage`, `save_shapefile`, `create_folium_map`

## Reporting

- `create_report(title, sections, figures=None, tables=None, output_path=...)`
- `create_pdf_report(...)` (requires reportlab)
- `render_html_report(...)` (requires jinja2)
- `export_workbook(sheets, output_path=..., metadata=None)`

`sections` maps a heading to body text; body paragraphs are separated by blank
lines. `figures` and `tables` are keyed by the same heading.
