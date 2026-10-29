"""Tests for data acquisition, caching, and validation."""

from __future__ import annotations

import time
from pathlib import Path

import pandas as pd
import pytest
import requests
from src.data_acquisition.base import (
    BaseDownloader,
    DataSourceUnavailableError,
    DataValidationError,
)
from src.data_acquisition.cdr_database import projects_from_records
from src.data_acquisition.literature import search_openalex
from src.data_acquisition.noaa_co2 import download_noaa_co2, parse_noaa_monthly
from src.data_acquisition.world_bank import download_world_bank_indicator
from src.data_processing.validators import validate_noaa_data
from src.utils.io import write_json


class TestNOAAParsing:
    """Tests for NOAA payload parsing."""

    def test_parse_monthly_schema(self, sample_noaa_frame: pd.DataFrame) -> None:
        assert len(sample_noaa_frame) == 192
        assert list(sample_noaa_frame.columns) == [
            "date",
            "year",
            "month",
            "co2_ppm",
            "co2_deseasonalized",
            "station",
            "latitude",
            "longitude",
            "elevation_m",
        ]
        assert sample_noaa_frame["co2_ppm"].iloc[0] == pytest.approx(350.0, abs=1.0)
        assert sample_noaa_frame["station"].unique().tolist() == ["mlo"]

    def test_parse_rejects_unknown_station(self, sample_noaa_text: str) -> None:
        with pytest.raises(ValueError, match="Unknown station"):
            parse_noaa_monthly(sample_noaa_text, station="zzz")

    def test_validation_detects_implausible_values(
        self, sample_noaa_frame: pd.DataFrame
    ) -> None:
        broken = sample_noaa_frame.copy()
        broken.loc[0, "co2_ppm"] = 5000.0
        result = validate_noaa_data(broken)
        assert not result.passed
        assert "co2_ppm" in result.summary()


class TestNOAADownload:
    """Tests for the NOAA download wrapper."""

    def test_download_parses_cached_payload(
        self,
        monkeypatch: pytest.MonkeyPatch,
        sample_noaa_text: str,
        tmp_path: Path,
    ) -> None:
        monkeypatch.setattr(
            BaseDownloader,
            "fetch",
            lambda self, *args, **kwargs: sample_noaa_text.encode("utf-8"),
        )
        frame = download_noaa_co2(cache_dir=tmp_path, start_year=2000)
        assert frame["year"].min() == 2000
        assert len(frame) == 72

    def test_download_rejects_invalid_year_range(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="start_year"):
            download_noaa_co2(
                cache_dir=tmp_path,
                start_year=2010,
                end_year=2000,
            )


class TestCacheFallback:
    """Tests for cache freshness and stale fallback behavior."""

    def test_stale_cache_used_when_network_fails(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        downloader = BaseDownloader(cache_dir=tmp_path, cache_hours=1, source_name="Test")
        data_path, meta_path = downloader.cache_paths("example", ".csv")
        data_path.write_bytes(b"cached-payload")
        write_json(
            meta_path,
            {
                "fetched_at_epoch": time.time() - 7200,
                "sha256": "deadbeef",
            },
        )

        def _fail(*args, **kwargs):
            raise requests.ConnectionError("network down")

        monkeypatch.setattr(downloader.session, "get", _fail)
        payload = downloader.fetch("https://example.invalid/data.csv", suffix=".csv")
        assert payload == b"cached-payload"

    def test_missing_source_raises(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        downloader = BaseDownloader(cache_dir=tmp_path, max_retries=0, source_name="Test")

        def _fail(*args, **kwargs):
            raise requests.ConnectionError("network down")

        monkeypatch.setattr(downloader.session, "get", _fail)
        with pytest.raises(DataSourceUnavailableError):
            downloader.fetch("https://example.invalid/data.csv", suffix=".csv")


class TestProjectData:
    """Tests for carbon removal project ingestion."""

    def test_projects_from_records_normalizes_methods(
        self, sample_projects: pd.DataFrame
    ) -> None:
        frame = projects_from_records(sample_projects.to_dict(orient="records"))
        assert set(frame["method"]) == {"dac", "biochar", "forestry"}
        assert frame["country"].tolist() == ["ISL", "USA", "TZA"]

    def test_invalid_projects_rejected(self, sample_projects: pd.DataFrame) -> None:
        broken = sample_projects.copy()
        broken.loc[0, "latitude"] = 200.0
        with pytest.raises(DataValidationError):
            projects_from_records(broken.to_dict(orient="records"))


class TestWorldBank:
    """Tests for World Bank response parsing."""

    def test_parse_world_bank_payload(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        payload = [
            {"pages": 1, "page": 1},
            [
                {
                    "indicator": {"id": "EN.GHG.CO2.MT.CE.AR5", "value": "CO2"},
                    "country": {"id": "USA", "value": "United States"},
                    "countryiso3code": "USA",
                    "date": "2020",
                    "value": 4.5,
                }
            ],
        ]
        monkeypatch.setattr(
            BaseDownloader, "fetch_json", lambda self, *args, **kwargs: payload
        )
        frame = download_world_bank_indicator(
            "EN.GHG.CO2.MT.CE.AR5", cache_dir=tmp_path
        )
        assert len(frame) == 1
        assert frame.loc[0, "country_code"] == "USA"
        assert frame.loc[0, "value"] == pytest.approx(4.5)


class TestOpenAlex:
    """Tests for literature search parsing."""

    def test_abstract_reconstruction(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        payload = {
            "results": [
                {
                    "id": "https://openalex.org/W1",
                    "title": "Carbon removal",
                    "publication_year": 2024,
                    "doi": "https://doi.org/10.1/example",
                    "cited_by_count": 5,
                    "type": "article",
                    "abstract_inverted_index": {
                        "Carbon": [0],
                        "removal": [1],
                        "works": [2],
                    },
                }
            ]
        }
        monkeypatch.setattr(
            BaseDownloader, "fetch_json", lambda self, *args, **kwargs: payload
        )
        frame = search_openalex("carbon removal", cache_dir=tmp_path)
        assert len(frame) == 1
        assert frame.loc[0, "abstract"] == "Carbon removal works"
        assert frame.loc[0, "publication_year"] == 2024
