# AGENTS.md - Carbon Sequestration Analysis Project

## Project Overview

This document serves as the master guide for AI agents and human collaborators working on the Carbon Sequestration Time Series Analysis project. The goal is to build a comprehensive, data-driven analysis system in Python that models atmospheric CO₂ trends, evaluates carbon sequestration methods, and provides actionable insights for climate strategy.

---

## Core Mission

Build a production-quality Python application that:
1. **Downloads and validates** real-world carbon and climate data from authoritative sources.
2. **Analyzes** time series data to identify trends, patterns, and projections.
3. **Compares** carbon sequestration methods across multiple criteria (cost, permanence, scalability, risk).
4. **Generates** comprehensive reports with visualizations in multiple formats.
5. **Exports** data in formats suitable for GIS, statistical, and business analysis.

---

## Autonomous Agent Instructions & Operating Directives

When operating on this codebase as an autonomous agent, follow these rules strictly:

1. **Environment Integrity & Isolation**:
   - Always operate within a virtual environment (`venv` or `conda`).
   - Run dependency checks using `pip check` or `pytest` prior to generating output.
2. **Deterministic Code Generation**:
   - Write standard PEP 8 compliant Python code with strict type annotations (`typing`).
   - Do not use non-standard third-party modules unless explicitly listed in `requirements.txt`.
3. **No Synthetic Data in Production**:
   - Mock data is permitted **only** inside unit testing suites (`tests/fixtures`).
   - Never fall back to generated synthetic data for generated reports, analytical outputs, or exports.
4. **Data Safety**:
   - Always write network requests using cached response patterns. Do not refetch identical payloads repeatedly.
5. **Modification Protocol**:
   - Prior to modifying existing functions, review associated unit test specs in `tests/`.
   - Update `AGENTS.md` or implementation documentation whenever interfaces or data schemas change.

---

## Technical Stack

### Core Languages & Libraries

```
Python 3.10+
├── Data Acquisition
│   ├── requests / httpx - HTTP requests
│   ├── beautifulsoup4 - Web scraping
│   ├── noaa-co2-api / custom API clients
│   └── yfinance - Financial data (for carbon markets)
├── Data Processing
│   ├── pandas - Data manipulation
│   ├── numpy - Numerical operations
│   ├── polars - Fast dataframes (alternative)
│   └── scipy - Statistical functions
├── Time Series Analysis
│   ├── statsmodels - ARIMA, decomposition, forecasting
│   ├── prophet - Facebook's time series forecasting
│   ├── sktime - Time series toolkit
│   └── pmdarima - Auto ARIMA
├── Visualization
│   ├── matplotlib - Base plotting
│   ├── seaborn - Statistical visualization
│   ├── plotly - Interactive plots
│   ├── bokeh - Interactive web plots
│   └── folium - Maps
├── Geospatial
│   ├── geopandas - Spatial data
│   ├── shapely - Geometry operations
│   ├── pyproj - Projections
│   └── rasterio - Raster data
├── Reporting
│   ├── python-docx - Word documents
│   ├── reportlab - PDF generation
│   ├── openpyxl - Excel files
│   └── jinja2 - HTML templates
└── Utilities
    ├── loguru - Logging
    ├── pydantic - Data validation
    ├── tqdm - Progress bars
    └── pytest - Testing
```

### Project Structure

```
carbon_sequestration/
├── AGENTS.md                    # This file
├── README.md                    # User documentation
├── requirements.txt             # Dependencies
├── setup.py                     # Package setup
├── pyproject.toml               # Modern Python packaging
├── .env.example                 # Environment variables template
├── .gitignore                   # Git ignore rules
│
├── data/
│   ├── raw/                    # Downloaded raw data
│   │   ├── noaa_co2/
│   │   ├── cdr_projects/
│   │   └── literature/
│   ├── processed/               # Cleaned and processed data
│   ├── external/                # Third-party data
│   └── outputs/                 # Analysis outputs
│
├── src/
│   ├── __init__.py
│   ├── config.py                # Configuration management
│   ├── constants.py             # Project constants
│   │
│   ├── data_acquisition/
│   │   ├── __init__.py
│   │   ├── base.py              # Base downloader class
│   │   ├── noaa_co2.py          # NOAA CO2 data
│   │   ├── cdr_database.py      # Carbon removal projects
│   │   ├── world_bank.py        # World Bank climate data
│   │   ├── iea_data.py          # IEA energy data
│   │   └── literature.py        # OpenAlex, Semantic Scholar
│   │
│   ├── data_processing/
│   │   ├── __init__.py
│   │   ├── cleaners.py          # Data cleaning functions
│   │   ├── validators.py        # Data validation
│   │   └── transformers.py      # Data transformation
│   │
│   ├── analysis/
│   │   ├── __init__.py
│   │   ├── time_series.py       # Time series analysis
│   │   ├── trends.py            # Trend detection
│   │   ├── forecasting.py       # Forecasting models
│   │   ├── comparison.py        # Method comparison
│   │   └── risk_analysis.py     # Risk quantification
│   │
│   ├── visualization/
│   │   ├── __init__.py
│   │   ├── static_plots.py      # Matplotlib/Seaborn plots
│   │   ├── interactive.py       # Plotly/Bokeh plots
│   │   ├── maps.py              # Folium/GeoPandas maps
│   │   └── themes.py            # Plot styling
│   │
│   ├── reporting/
│   │   ├── __init__.py
│   │   ├── word_report.py       # Word document generation
│   │   ├── pdf_report.py        # PDF generation
│   │   ├── excel_export.py      # Excel exports
│   │   └── html_report.py       # HTML dashboards
│   │
│   └── utils/
│       ├── __init__.py
│       ├── logging.py           # Logging setup
│       ├── io.py                # File I/O utilities
│       └── helpers.py           # General utilities
│
├── notebooks/                   # Jupyter notebooks for exploration
│   ├── 01_data_exploration.ipynb
│   ├── 02_time_series_analysis.ipynb
│   └── 03_report_generation.ipynb
│
├── scripts/                     # Standalone scripts
│   ├── download_data.py
│   ├── run_analysis.py
│   └── generate_report.py
│
├── tests/                       # Unit tests
│   ├── test_data_acquisition.py
│   ├── test_analysis.py
│   └── test_reporting.py
│
├── docs/                        # Documentation
│   ├── api.md
│   ├── data_sources.md
│   └── methodology.md
│
└── output/                      # Generated reports and figures
    ├── reports/
    ├── figures/
    └── data_exports/
```

---

## Data Sources (Priority Order)

### Tier 1: Authoritative Primary Sources

| Source | Data Type | URL | Access Method |
| :--- | :--- | :--- | :--- |
| NOAA GML | CO₂ concentrations | `https://gml.noaa.gov/ccgg/trends/` | Direct file download |
| CDR Database | Carbon removal projects | `https://cdrdatabase.com` | API (if available) |
| World Bank | Climate indicators | `https://data.worldbank.org` | `wbgapi` package |
| IEA | Energy/CCUS data | `https://www.iea.org/data-and-statistics` | Manual/API |
| IPCC AR6 | Method assessments | `https://www.ipcc.ch/report/ar6/wg3/` | PDF extraction |

### Tier 2: Secondary Sources

| Source | Data Type | Access Method |
| :--- | :--- | :--- |
| OpenAlex | Literature metadata | `pyalex` package |
| Semantic Scholar | Paper abstracts | API |
| Global Carbon Project | Emissions data | CSV downloads |
| FAO | Forestry data | `faostat` package |

### Tier 3: Supplementary Sources
- Carbon market data (Xpansiv, CBL Markets)
- Company reports (Climeworks, Carbon Engineering)
- News articles for project announcements

### Data Source Requirements
1. **Always cache downloaded data** with timestamps.
2. **Document data provenance** in metadata files.
3. **Handle API rate limits** with exponential backoff.
4. **Provide fallback data** if primary sources fail.
5. **Validate data integrity** after download.

---

## Development Standards

### Code Quality Rules
- **Style**: Standard PEP 8, formatted via `black`, linted via `ruff`.
- **Types**: Use type hints for all functions (`from typing import ...`).
- **Docstrings**: Google-style docstrings for all public functions and classes.
- **Testing**: Minimum 80% test coverage using `pytest`.
- **Logging**: Use `loguru` for structured logging.

### Example Function Template

```python
from typing import Optional
from pathlib import Path
from loguru import logger
import pandas as pd

def download_noaa_co2(
    station: str = "mlo",
    start_year: Optional[int] = None,
    end_year: Optional[int] = None,
    cache_dir: Path = Path("data/raw/noaa_co2"),
) -> pd.DataFrame:
    """Download CO2 data from NOAA Global Monitoring Laboratory.

    Args:
        station: Station code (e.g., 'mlo' for Mauna Loa).
        start_year: Filter data from this year (inclusive).
        end_year: Filter data up to this year (inclusive).
        cache_dir: Directory to cache downloaded data.

    Returns:
        DataFrame with columns: date, co2_ppm, station, latitude, longitude.

    Raises:
        DataDownloadError: If data cannot be retrieved after retries.

    Example:
        >>> df = download_noaa_co2(station="mlo", start_year=2000)
        >>> df.head()
    """
    ...
```

### Testing Requirements

```python
# tests/test_data_acquisition.py
import pytest
from pathlib import Path
from unittest.mock import patch, Mock

from src.data_acquisition.noaa_co2 import download_noaa_co2

class TestNOAADownload:
    """Tests for NOAA CO2 data download."""
    
    def test_successful_download(self, tmp_path):
        """Test successful data download and parsing."""
        ...
    
    @patch("src.data_acquisition.noaa_co2.requests.get")
    def test_network_failure_fallback(self, mock_get, tmp_path):
        """Test fallback behavior on network failure."""
        ...
    
    def test_data_validation(self, sample_co2_data):
        """Test that downloaded data passes validation."""
        ...
```

---

## Analysis Methodology

### 1. Time Series Analysis Pipeline

```python
from typing import List
import pandas as pd

class CarbonTimeSeriesAnalyzer:
    """Analyze CO2 and sequestration time series data."""
    
    def decompose(self, series: pd.Series):
        """Decompose into trend, seasonal, residual components."""
        ...
        
    def detect_changepoints(self, series: pd.Series):
        """Identify structural breaks in trends."""
        ...
        
    def calculate_growth_rates(self, series: pd.Series):
        """Calculate YoY, CAGR, and acceleration metrics."""
        ...
        
    def forecast(self, series: pd.Series, horizon: int):
        """Generate forecasts with confidence intervals."""
        ...
        
    def stationarity_test(self, series: pd.Series):
        """ADF and KPSS stationarity tests."""
        ...
```

### 2. Method Comparison Framework

Each sequestration method must be evaluated on:

| Criterion | Metric | Data Source |
| :--- | :--- | :--- |
| Cost | $/tCO₂ (range, mean, median) | Literature, industry reports |
| Sequestration Rate | tCO₂/ha/yr or tCO₂/facility/yr | Scientific papers |
| Permanence | Storage duration (years, distribution) | Literature |
| Energy Requirement | GJ/tCO₂, energy multiplier | Technical assessments |
| Scalability | GtCO₂/yr potential, constraints | IPCC, IEA |
| Technology Readiness | TRL (1-9) | Assessments |
| Risk Factors | Reversal probability, hazard types | Literature |

### 3. Required Analysis Outputs

For each analysis run, generate:

1. **Statistical Summary** (JSON/CSV)
   - Descriptive statistics per method
   - Confidence intervals
   - Hypothesis test results
2. **Time Series Decomposition** (PNG/SVG)
   - Trend, seasonal, residual plots
   - Change point annotations
3. **Forecast Visualizations** (PNG/interactive HTML)
   - Historical data + forecast
   - Confidence bands
   - Scenario comparison
4. **Method Comparison Matrix** (CSV/Excel)
   - Multi-criteria scoring
   - Normalized rankings
   - Pareto frontier analysis
5. **Comprehensive Report** (DOCX/PDF)
   - Executive summary
   - Methodology description
   - Results and discussion
   - Recommendations
6. **GIS-Ready Data** (GeoPackage/Shapefile)
   - Station locations with attributes
   - Project locations with metadata
   - Analysis results as spatial layers

---

## Report Structure

```markdown
1. Executive Summary
   - Key findings (bullet points)
   - Quantitative claims with confidence levels
   - Strategic recommendations

2. Introduction
   - Project scope and objectives
   - Data sources and methodology overview

3. Data Analysis
   - Data provenance and validation
   - Descriptive statistics
   - Time series decomposition
   - Trend analysis and forecasting

4. Method Comparison
   - Multi-criteria evaluation
   - Cost-benefit analysis
   - Risk assessment
   - Portfolio optimization

5. Results and Discussion
   - Statistical findings
   - Sensitivity analysis
   - Limitations and uncertainties

6. Recommendations
   - Immediate actions
   - Strategic investments
   - Policy implications

7. Appendices
   - Data tables
   - Methodology details
   - Code documentation
   - References
```

---

## Quality Checklist

### Before Committing Code
- [ ] Code passes `black` formatting
- [ ] Code passes `ruff` linting
- [ ] All functions have type hints
- [ ] All public functions have docstrings
- [ ] New code has tests (≥80% coverage)
- [ ] Data downloads are cached
- [ ] Logging is implemented
- [ ] Errors are handled gracefully

### Before Generating Report
- [ ] All data sources are documented
- [ ] Statistical claims are reproducible
- [ ] Visualizations have proper labels and titles
- [ ] Numbers are consistent throughout
- [ ] Confidence levels are stated
- [ ] Limitations are acknowledged
- [ ] Recommendations are actionable

### Before Publishing
- [ ] README is up to date
- [ ] AGENTS.md reflects current state
- [ ] All tests pass
- [ ] Documentation is complete
- [ ] Data provenance is traceable
- [ ] Licensing is clear
- [ ] Citation information is provided

---

## Error Handling Guidelines

### Data Acquisition Errors

```python
from typing import Optional

class DataAcquisitionError(Exception):
    """Base exception for data acquisition failures."""
    pass

class DataSourceUnavailableError(DataAcquisitionError):
    """Primary data source is unavailable."""
    
    def __init__(self, source: str, reason: str, fallback: Optional[str] = None):
        self.source = source
        self.reason = reason
        self.fallback = fallback
        super().__init__(f"{source} unavailable: {reason}")
```

### Error Handling Strategy
1. **Retry with backoff** for transient errors (network issues).
2. **Fallback to cached data** if available.
3. **Fallback to secondary source** if primary fails.
4. **Use synthetic data** only for testing, never for final reports.
5. **Log all errors** with full context.
6. **Fail loudly** for critical errors (data integrity).

---

## Performance Guidelines

### Data Processing
- Use `polars` for large datasets (>1M rows).
- Chunk processing for memory-intensive operations.
- Parallel processing for independent operations (`concurrent.futures`).

### Visualization
- Cache figures to avoid regeneration.
- Use vector formats (SVG, PDF) for publications.
- Use raster (PNG) for quick previews.
- Limit interactive plots to essential data.

### Report Generation
- Generate reports incrementally.
- Save intermediate results.
- Allow restart from failure points.

---

## Collaboration Protocol

### For AI Agents

1. **Before starting any task**:
   - Read this `AGENTS.md` completely.
   - Check existing code for architectural patterns.
   - Verify data availability.
   - Understand the analysis context.
2. **During work**:
   - Follow established code standards.
   - Write tests alongside functionality.
   - Document assumptions clearly.
   - Use consistent naming conventions.
   - Log progress for execution tasks.
3. **After completing work**:
   - Update documentation files.
   - Run the full test suite (`pytest`).
   - Verify outputs.
   - Update `AGENTS.md` if repository architecture changes.

---

## Common Pitfalls to Avoid

### Data Handling
- ❌ Don't use synthetic data for final reports
- ❌ Don't ignore data quality issues
- ❌ Don't hardcode file paths
- ✅ Do validate all downloaded data
- ✅ Do cache data with provenance
- ✅ Do use configuration files

### Analysis
- ❌ Don't claim causality from correlation
- ❌ Don't extrapolate beyond data range without justification
- ❌ Don't ignore confidence intervals
- ✅ Do use appropriate statistical tests
- ✅ Do acknowledge uncertainties
- ✅ Do validate assumptions

### Reporting
- ❌ Don't make unsubstantiated claims
- ❌ Don't omit methodology details
- ❌ Don't hide limitations
- ✅ Do cite data sources
- ✅ Do explain methodology
- ✅ Do discuss limitations

### Code
- ❌ Don't use magic numbers
- ❌ Don't duplicate code
- ❌ Don't ignore warnings
- ✅ Do use named constants
- ✅ Do write reusable functions
- ✅ Do handle edge cases

---

## Version Control Guidelines

### Branching Strategy

```
main
├── develop
│   ├── feature/data-acquisition
│   ├── feature/time-series-analysis
│   ├── feature/report-generation
│   └── feature/gis-export
└── release/v1.0
```

### Commit Message Format

```
type(scope): description

[optional body]

[optional footer]
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

---

## Environment Configuration

### Required Environment Variables (`.env.example`)

```bash
NOAA_API_KEY=optional
CDR_DATABASE_API_KEY=optional
OPENALEX_EMAIL=your.email@example.com
LOG_LEVEL=INFO
CACHE_DIR=./data/raw
OUTPUT_DIR=./output
```

### Configuration File (`config.yaml`)

```yaml
data_sources:
  noaa:
    station: mlo
    cache_hours: 24
  cdr:
    api_endpoint: https://api.cdrdatabase.com/v1
    cache_hours: 168

analysis:
  forecast_horizon: 10
  confidence_level: 0.95
  methods:
    - dac
    - beccs
    - biochar
    - forestry
    - erw

reporting:
  format: [docx, pdf, html]
  include_interactive: true
  theme: professional
```

---

## Testing Data

### Mocking External Services Example

```python
import pytest
from unittest.mock import patch
from src.data_acquisition.noaa_co2 import download_noaa_co2

@pytest.fixture
def mock_noaa_response():
    """Mock NOAA API response."""
    return """# NOAA data header
# ...
1958 3 1958.21 315.71 314.44 1958 3 0.5 0.1
1958 4 1958.29 317.45 315.16 1958 4 0.5 0.1
"""

@patch("requests.get")
def test_noaa_download(mock_get, mock_noaa_response, tmp_path):
    mock_get.return_value.text = mock_noaa_response
    mock_get.return_value.status_code = 200
    
    df = download_noaa_co2(cache_dir=tmp_path)
    assert len(df) == 2
    assert df["co2_ppm"].iloc[0] == 315.71
```

---

## Appendix: Data Schema Reference

### NOAA CO2 Data Schema
```python
{
    "date": "datetime64[ns]",       # Observation date
    "year": "int64",                # Year
    "month": "int64",               # Month
    "co2_ppm": "float64",           # CO2 concentration in ppm
    "co2_deseasonalized": "float64",# Seasonally adjusted
    "station": "string",            # Station name
    "latitude": "float64",          # Station latitude
    "longitude": "float64",         # Station longitude
    "elevation_m": "float64",       # Station elevation
}
```

### Carbon Project Data Schema
```python
{
    "project_id": "string",         # Unique identifier
    "project_name": "string",       # Project name
    "method": "string",             # Sequestration method
    "capacity_tco2_year": "float64",# Annual capacity
    "status": "string",             # Operational/Pilot/Development
    "latitude": "float64",          # Project latitude
    "longitude": "float64",         # Project longitude
    "country": "string",            # Country code
    "start_year": "int64",          # Year operations started
    "cost_per_ton": "float64",      # Cost in USD
    "funding_source": "string",     # Funding type
}
```

---

**Last Updated**: October 2026  
**Status**: Active Development