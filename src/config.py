"""Configuration loading with YAML, environment overrides, and path setup."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from src.constants import (
    DEFAULT_CACHE_HOURS,
    DEFAULT_CONFIG_PATH,
    EXPORTS_DIR,
    FIGURES_DIR,
    PROCESSED_DATA_DIR,
    RAW_DATA_DIR,
    REPORTS_DIR,
)


@dataclass(frozen=True)
class NOAAConfig:
    """NOAA CO2 acquisition settings."""

    station: str = "mlo"
    start_year: int | None = None
    end_year: int | None = None
    cache_hours: int = DEFAULT_CACHE_HOURS


@dataclass(frozen=True)
class CDRConfig:
    """Carbon removal project data settings."""

    api_endpoint: str = ""
    cache_hours: int = 168


@dataclass(frozen=True)
class WorldBankConfig:
    """World Bank indicator settings."""

    cache_hours: int = 168


@dataclass(frozen=True)
class OpenAlexConfig:
    """OpenAlex literature settings."""

    mailto: str = ""


@dataclass(frozen=True)
class DataSourcesConfig:
    """Container for all data source settings."""

    noaa: NOAAConfig = field(default_factory=NOAAConfig)
    cdr: CDRConfig = field(default_factory=CDRConfig)
    world_bank: WorldBankConfig = field(default_factory=WorldBankConfig)
    openalex: OpenAlexConfig = field(default_factory=OpenAlexConfig)


@dataclass(frozen=True)
class AnalysisConfig:
    """Analysis defaults."""

    forecast_horizon: int = 10
    confidence_level: float = 0.95
    seasonal_period: int = 12
    changepoint_threshold: float = 3.0
    methods: tuple[str, ...] = ("dac", "beccs", "biochar", "forestry", "erw")


@dataclass(frozen=True)
class ReportingConfig:
    """Report generation defaults."""

    format: tuple[str, ...] = ("docx", "html", "xlsx")
    include_interactive: bool = True
    theme: str = "professional"
    title: str = "Carbon Sequestration and Atmospheric CO2 Analysis"


@dataclass(frozen=True)
class PathsConfig:
    """Filesystem locations used by the pipeline."""

    cache_dir: Path = RAW_DATA_DIR
    processed_dir: Path = PROCESSED_DATA_DIR
    output_dir: Path = EXPORTS_DIR.parent
    reports_dir: Path = REPORTS_DIR
    figures_dir: Path = FIGURES_DIR
    exports_dir: Path = EXPORTS_DIR


@dataclass(frozen=True)
class Config:
    """Top-level application configuration."""

    data_sources: DataSourcesConfig = field(default_factory=DataSourcesConfig)
    analysis: AnalysisConfig = field(default_factory=AnalysisConfig)
    reporting: ReportingConfig = field(default_factory=ReportingConfig)
    paths: PathsConfig = field(default_factory=PathsConfig)

    def ensure_directories(self) -> None:
        """Create all configured output and data directories if missing."""
        for directory in (
            self.paths.cache_dir,
            self.paths.processed_dir,
            self.paths.output_dir,
            self.paths.reports_dir,
            self.paths.figures_dir,
            self.paths.exports_dir,
        ):
            Path(directory).mkdir(parents=True, exist_ok=True)


def _section(raw: dict[str, Any], key: str) -> dict[str, Any]:
    value = raw.get(key, {})
    if not isinstance(value, dict):
        raise ValueError(f"Config section '{key}' must be a mapping")
    return value


def _tuple_of_str(value: Any, default: tuple[str, ...]) -> tuple[str, ...]:
    if value is None:
        return default
    if isinstance(value, str):
        return (value,)
    if isinstance(value, (list, tuple)):
        return tuple(str(item) for item in value)
    raise ValueError("Expected a string or list of strings")


def config_from_dict(raw: dict[str, Any]) -> Config:
    """Build a :class:`Config` from a parsed YAML mapping.

    Environment variables ``CACHE_DIR`` and ``OUTPUT_DIR`` override the
    corresponding configured paths when present.
    """
    sources = _section(raw, "data_sources")
    noaa = _section(sources, "noaa")
    cdr = _section(sources, "cdr")
    world_bank = _section(sources, "world_bank")
    openalex = _section(sources, "openalex")

    analysis = _section(raw, "analysis")
    reporting = _section(raw, "reporting")
    paths = _section(raw, "paths")

    cache_dir = Path(os.environ.get("CACHE_DIR") or paths.get("cache_dir") or RAW_DATA_DIR)
    output_dir = Path(os.environ.get("OUTPUT_DIR") or paths.get("output_dir") or "output")

    return Config(
        data_sources=DataSourcesConfig(
            noaa=NOAAConfig(
                station=str(noaa.get("station", "mlo")),
                start_year=noaa.get("start_year"),
                end_year=noaa.get("end_year"),
                cache_hours=int(noaa.get("cache_hours", DEFAULT_CACHE_HOURS)),
            ),
            cdr=CDRConfig(
                api_endpoint=str(cdr.get("api_endpoint") or ""),
                cache_hours=int(cdr.get("cache_hours", 168)),
            ),
            world_bank=WorldBankConfig(
                cache_hours=int(world_bank.get("cache_hours", 168)),
            ),
            openalex=OpenAlexConfig(
                mailto=str(
                    os.environ.get("OPENALEX_EMAIL") or openalex.get("mailto") or ""
                ),
            ),
        ),
        analysis=AnalysisConfig(
            forecast_horizon=int(analysis.get("forecast_horizon", 10)),
            confidence_level=float(analysis.get("confidence_level", 0.95)),
            seasonal_period=int(analysis.get("seasonal_period", 12)),
            changepoint_threshold=float(analysis.get("changepoint_threshold", 3.0)),
            methods=_tuple_of_str(
                analysis.get("methods"),
                ("dac", "beccs", "biochar", "forestry", "erw"),
            ),
        ),
        reporting=ReportingConfig(
            format=_tuple_of_str(reporting.get("format"), ("docx", "html", "xlsx")),
            include_interactive=bool(reporting.get("include_interactive", True)),
            theme=str(reporting.get("theme", "professional")),
            title=str(
                reporting.get(
                    "title", "Carbon Sequestration and Atmospheric CO2 Analysis"
                )
            ),
        ),
        paths=PathsConfig(
            cache_dir=cache_dir,
            processed_dir=Path(paths.get("processed_dir") or PROCESSED_DATA_DIR),
            output_dir=output_dir,
            reports_dir=Path(paths.get("reports_dir") or output_dir / "reports"),
            figures_dir=Path(paths.get("figures_dir") or output_dir / "figures"),
            exports_dir=Path(paths.get("exports_dir") or output_dir / "data_exports"),
        ),
    )


def load_config(path: Path | str | None = None) -> Config:
    """Load configuration from YAML, falling back to defaults.

    Args:
        path: Optional path to a YAML configuration file. Defaults to
            ``CONFIG_PATH`` environment variable or ``config.yaml`` at the
            project root.

    Returns:
        A validated :class:`Config` instance.

    Raises:
        FileNotFoundError: If an explicitly provided path does not exist.
        ValueError: If the YAML document is not a mapping.
    """
    resolved = Path(path or os.environ.get("CONFIG_PATH") or DEFAULT_CONFIG_PATH)
    if not resolved.exists():
        if path is not None or os.environ.get("CONFIG_PATH"):
            raise FileNotFoundError(f"Configuration file not found: {resolved}")
        return Config()

    with resolved.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}

    if not isinstance(raw, dict):
        raise ValueError(f"Configuration root must be a mapping: {resolved}")

    return config_from_dict(raw)
