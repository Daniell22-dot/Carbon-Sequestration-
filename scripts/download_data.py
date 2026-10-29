"""Download and cache authoritative carbon and climate datasets."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import load_config
from src.data_acquisition.cdr_database import (
    download_cdr_projects,
    load_cdr_projects_csv,
)
from src.data_acquisition.noaa_co2 import download_noaa_co2
from src.data_processing.cleaners import clean_noaa
from src.utils.io import write_dataframe, write_metadata
from src.utils.logging import setup_logging


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--station", default=None, help="NOAA station code (default: mlo)")
    parser.add_argument("--start-year", type=int, default=None)
    parser.add_argument("--end-year", type=int, default=None)
    parser.add_argument("--cache-dir", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--projects-csv", type=Path, default=None)
    parser.add_argument("--force", action="store_true", help="Ignore fresh caches")
    parser.add_argument("--config", type=Path, default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the download workflow.

    Args:
        argv: Optional argument list (defaults to ``sys.argv``).

    Returns:
        Process exit code.
    """
    args = build_parser().parse_args(argv)
    setup_logging()
    config = load_config(args.config)

    station = args.station or config.data_sources.noaa.station
    start_year = args.start_year or config.data_sources.noaa.start_year
    end_year = args.end_year or config.data_sources.noaa.end_year
    cache_dir = args.cache_dir or config.paths.cache_dir / "noaa_co2"
    output_dir = args.output_dir or config.paths.processed_dir

    frame = download_noaa_co2(
        station=station,
        start_year=start_year,
        end_year=end_year,
        cache_dir=cache_dir,
        cache_hours=config.data_sources.noaa.cache_hours,
        force=args.force,
    )
    cleaned = clean_noaa(frame)
    destination = write_dataframe(cleaned, output_dir / f"noaa_co2_{station}.csv")
    write_metadata(
        destination,
        {
            "source": "NOAA GML",
            "station": station,
            "rows": len(cleaned),
            "start": str(cleaned["date"].min()),
            "end": str(cleaned["date"].max()),
        },
    )
    print(f"Wrote {len(cleaned)} NOAA rows to {destination}")

    if args.projects_csv:
        projects = load_cdr_projects_csv(args.projects_csv)
        projects_destination = write_dataframe(
            projects, output_dir / "cdr_projects.csv"
        )
        print(f"Wrote {len(projects)} project rows to {projects_destination}")
    elif config.data_sources.cdr.api_endpoint:
        projects = download_cdr_projects(
            endpoint=config.data_sources.cdr.api_endpoint,
            cache_dir=config.paths.cache_dir / "cdr_projects",
            cache_hours=config.data_sources.cdr.cache_hours,
            force=args.force,
        )
        projects_destination = write_dataframe(
            projects, output_dir / "cdr_projects.csv"
        )
        print(f"Wrote {len(projects)} project rows to {projects_destination}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
