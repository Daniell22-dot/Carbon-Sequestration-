"""Project-wide constants: paths, station metadata, and method reference data.

All numeric method ranges are literature-derived reference values used for
comparison only. They are deliberately expressed as ranges so that downstream
analysis can propagate uncertainty instead of presenting false precision.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parent.parent

DATA_DIR: Final[Path] = PROJECT_ROOT / "data"
RAW_DATA_DIR: Final[Path] = DATA_DIR / "raw"
PROCESSED_DATA_DIR: Final[Path] = DATA_DIR / "processed"
EXTERNAL_DATA_DIR: Final[Path] = DATA_DIR / "external"
OUTPUT_DIR: Final[Path] = PROJECT_ROOT / "output"
REPORTS_DIR: Final[Path] = OUTPUT_DIR / "reports"
FIGURES_DIR: Final[Path] = OUTPUT_DIR / "figures"
EXPORTS_DIR: Final[Path] = OUTPUT_DIR / "data_exports"

DEFAULT_CONFIG_PATH: Final[Path] = PROJECT_ROOT / "config.yaml"

DEFAULT_CACHE_HOURS: Final[int] = 24
DEFAULT_TIMEOUT_SECONDS: Final[int] = 30
DEFAULT_MAX_RETRIES: Final[int] = 3
DEFAULT_BACKOFF_FACTOR: Final[float] = 2.0

USER_AGENT: Final[str] = (
    "carbon-sequestration-analysis/0.1 (+https://github.com/anomalyco/opencode)"
)

#: NOAA Global Monitoring Laboratory monthly CO2 file template.
NOAA_MONTHLY_URL_TEMPLATE: Final[str] = (
    "https://gml.noaa.gov/webdata/ccgg/trends/co2/co2_mm_{station}.csv"
)

#: World Bank API v2 indicator endpoint template.
WORLD_BANK_URL_TEMPLATE: Final[str] = (
    "https://api.worldbank.org/v2/country/{countries}/indicator/{indicator}"
)

#: OpenAlex works endpoint.
OPENALEX_WORKS_URL: Final[str] = "https://api.openalex.org/works"

#: Station metadata keyed by lowercase NOAA station code.
#: Latitude/longitude in decimal degrees, elevation in metres above sea level.
STATIONS: Final[dict[str, dict[str, object]]] = {
    "mlo": {
        "name": "Mauna Loa, Hawaii",
        "latitude": 19.536,
        "longitude": -155.576,
        "elevation_m": 3397.0,
        "country": "USA",
    },
    "brw": {
        "name": "Barrow, Alaska",
        "latitude": 71.323,
        "longitude": -156.611,
        "elevation_m": 11.0,
        "country": "USA",
    },
    "smo": {
        "name": "Tutuila, American Samoa",
        "latitude": -14.247,
        "longitude": -170.564,
        "elevation_m": 42.0,
        "country": "ASM",
    },
    "spo": {
        "name": "South Pole, Antarctica",
        "latitude": -90.0,
        "longitude": 0.0,
        "elevation_m": 2810.0,
        "country": "ATA",
    },
    "mlh": {
        "name": "Mauna Loa (in situ), Hawaii",
        "latitude": 19.536,
        "longitude": -155.576,
        "elevation_m": 3397.0,
        "country": "USA",
    },
    "nwr": {
        "name": "Niwood, Colorado",
        "latitude": 40.053,
        "longitude": -105.586,
        "elevation_m": 3523.0,
        "country": "USA",
    },
    "thd": {
        "name": "Trinidad Head, California",
        "latitude": 41.054,
        "longitude": -124.151,
        "elevation_m": 107.0,
        "country": "USA",
    },
    "cgo": {
        "name": "Cape Grim, Tasmania",
        "latitude": -40.683,
        "longitude": 144.690,
        "elevation_m": 94.0,
        "country": "AUS",
    },
    "zep": {
        "name": "Zeppelin, Svalbard",
        "latitude": 78.907,
        "longitude": 11.888,
        "elevation_m": 475.0,
        "country": "NOR",
    },
}

SUPPORTED_STATIONS: Final[tuple[str, ...]] = tuple(sorted(STATIONS))

#: Literature-derived reference ranges per sequestration method.
#: Keys map to the comparison schema in AGENTS.md.
#: Values are central estimates plus plausible ranges; they are NOT measurements
#: produced by this project and must be cited when reported.
METHOD_CATALOG: Final[dict[str, dict[str, object]]] = {
    "dac": {
        "display_name": "Direct Air Capture (DAC)",
        "sequestration_min": 0.0,
        "sequestration_max": 0.0,
        "sequestration_mean": 0.0,
        "cost_min": 100.0,
        "cost_max": 600.0,
        "cost_mean": 350.0,
        "permanence_min": 1000,
        "permanence_max": 10000,
        "energy_gj_per_tco2": 6.0,
        "trl": 7,
        "scalability_gt_year": 0.01,
        "risk_score": 0.25,
        "reversal_probability": 0.02,
    },
    "beccs": {
        "display_name": "Bioenergy with Carbon Capture and Storage (BECCS)",
        "sequestration_min": 0.0,
        "sequestration_max": 0.0,
        "sequestration_mean": 0.0,
        "cost_min": 100.0,
        "cost_max": 250.0,
        "cost_mean": 175.0,
        "permanence_min": 100,
        "permanence_max": 1000,
        "energy_gj_per_tco2": 3.0,
        "trl": 6,
        "scalability_gt_year": 0.5,
        "risk_score": 0.45,
        "reversal_probability": 0.10,
    },
    "biochar": {
        "display_name": "Biochar",
        "sequestration_min": 0.0,
        "sequestration_max": 0.0,
        "sequestration_mean": 0.0,
        "cost_min": 50.0,
        "cost_max": 200.0,
        "cost_mean": 120.0,
        "permanence_min": 100,
        "permanence_max": 1000,
        "energy_gj_per_tco2": 1.0,
        "trl": 8,
        "scalability_gt_year": 0.5,
        "risk_score": 0.30,
        "reversal_probability": 0.08,
    },
    "forestry": {
        "display_name": "Afforestation and Reforestation",
        "sequestration_min": 0.0,
        "sequestration_max": 0.0,
        "sequestration_mean": 0.0,
        "cost_min": 5.0,
        "cost_max": 50.0,
        "cost_mean": 25.0,
        "permanence_min": 20,
        "permanence_max": 200,
        "energy_gj_per_tco2": 0.0,
        "trl": 9,
        "scalability_gt_year": 3.0,
        "risk_score": 0.55,
        "reversal_probability": 0.25,
    },
    "erw": {
        "display_name": "Enhanced Rock Weathering (ERW)",
        "sequestration_min": 0.0,
        "sequestration_max": 0.0,
        "sequestration_mean": 0.0,
        "cost_min": 50.0,
        "cost_max": 200.0,
        "cost_mean": 110.0,
        "permanence_min": 1000,
        "permanence_max": 10000,
        "energy_gj_per_tco2": 1.5,
        "trl": 5,
        "scalability_gt_year": 2.0,
        "risk_score": 0.35,
        "reversal_probability": 0.05,
    },
}

#: Per-hectare sequestration rates (tCO2/ha/yr) for land-based methods.
#: DAC/BECCS are facility-based, so they have no per-hectare rate.
PER_HECTARE_RATES: Final[dict[str, tuple[float, float]]] = {
    "forestry": (2.0, 15.0),
    "biochar": (1.0, 5.0),
    "erw": (0.5, 4.0),
}

DEFAULT_METHOD_WEIGHTS: Final[dict[str, float]] = {
    "cost": 0.30,
    "permanence": 0.20,
    "scalability": 0.20,
    "energy": 0.10,
    "trl": 0.10,
    "risk": 0.10,
}

SCHEMA_VERSION: Final[str] = "1.0.0"
