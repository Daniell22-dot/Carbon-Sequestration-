# Carbon Sequestration Analysis

A production-oriented Python pipeline for analyzing atmospheric CO2 time series and
comparing carbon sequestration methods.

## What it does

1. Downloads and caches authoritative data (NOAA GML CO2, World Bank indicators,
   OpenAlex literature, user-supplied CDR project exports).
2. Validates every dataset against documented schemas and records SHA-256
   provenance metadata beside each cached payload.
3. Decomposes CO2 series, detects change points, tests stationarity, measures
   trends, and forecasts with prediction intervals.
4. Scores sequestration methods on cost, permanence, scalability, energy, TRL,
   and risk; ranks them and computes a Pareto frontier.
5. Exports CSV/JSON, GeoPackage, Excel, DOCX, PDF, and standalone HTML reports.

No synthetic data is used in production outputs. Test fixtures are synthetic and
live only under `tests/`.

## Requirements

- Python 3.10+ (tested on 3.13)
- A virtual environment is required

## Quick start

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
pytest
```

Run the pipeline:

```powershell
python scripts/download_data.py --station mlo --start-year 1990
python scripts/run_analysis.py --station mlo --horizon 20
python scripts/generate_report.py
```

Outputs are written to `output/reports`, `output/figures`, and
`output/data_exports`.

## Configuration

Edit `config.yaml` or set environment variables (see `.env.example`). Precedence:

1. Explicit CLI arguments
2. Environment variables (`CACHE_DIR`, `OUTPUT_DIR`, `OPENALEX_EMAIL`, `LOG_LEVEL`)
3. `config.yaml`
4. Built-in defaults in `src/config.py`

## Project layout

```
src/
  data_acquisition/   NOAA, CDR, World Bank, IEA, OpenAlex clients
  data_processing/    cleaners, validators, transformers
  analysis/           time series, trends, forecasting, comparison, risk
  visualization/      static plots, interactive plots, maps, themes
  reporting/          DOCX, PDF, Excel, HTML
  utils/              logging, I/O, helpers
scripts/              download, analyze, report CLIs
tests/                offline pytest suite with fixtures
docs/                 API, data source, and methodology notes
```

## Data sources and licensing

NOAA GML CO2 data are public domain. World Bank data are available under the
World Bank Open Data terms. OpenAlex metadata are CC0. IEA and CDR Database data
are licence-restricted; this project only loads exports you are entitled to use.
See `docs/data_sources.md`.

## Limitations

- Method cost/permanence ranges are literature-derived reference values, not
  measurements produced here.
- Forecasts assume the estimated model structure persists; intervals widen with
  horizon.
- Correlation between CO2 and deployment does not establish causality.
- Portfolio simulations are illustrative, not investment advice.

## License

MIT.
