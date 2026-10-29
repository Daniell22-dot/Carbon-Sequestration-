"""Literature metadata acquisition from OpenAlex."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from src.constants import OPENALEX_WORKS_URL, RAW_DATA_DIR
from src.data_acquisition.base import BaseDownloader, DataSourceUnavailableError
from src.utils.logging import get_logger

logger = get_logger(__name__)


def _reconstruct_abstract(inverted_index: dict[str, list[int]] | None) -> str:
    if not inverted_index:
        return ""
    positions: list[tuple[int, str]] = []
    for word, indexes in inverted_index.items():
        for index in indexes:
            positions.append((int(index), word))
    positions.sort(key=lambda item: item[0])
    return " ".join(word for _, word in positions)


def search_openalex(
    query: str,
    limit: int = 25,
    mailto: str = "",
    cache_dir: Path | str = RAW_DATA_DIR / "literature",
    cache_hours: int = 168,
    force: bool = False,
) -> pd.DataFrame:
    """Search OpenAlex for works matching a query.

    Args:
        query: Free-text search query.
        limit: Maximum number of works to return (1-200).
        mailto: Contact email for the OpenAlex polite pool.
        cache_dir: Cache directory for the raw payload.
        cache_hours: Cache freshness window in hours.
        force: Refetch even when a fresh cache entry exists.

    Returns:
        DataFrame with ``id``, ``title``, ``publication_year``, ``doi``,
        ``cited_by_count``, ``type``, and ``abstract`` columns.

    Raises:
        ValueError: If ``limit`` is outside 1-200.
        DataSourceUnavailableError: If the API cannot be reached or parsed.
    """
    if not 1 <= limit <= 200:
        raise ValueError("limit must be between 1 and 200")

    params: dict[str, Any] = {
        "search": query,
        "per-page": limit,
        "select": "id,title,publication_year,doi,cited_by_count,type,abstract_inverted_index",
    }
    if mailto:
        params["mailto"] = mailto

    downloader = BaseDownloader(
        cache_dir=cache_dir,
        cache_hours=cache_hours,
        source_name="OpenAlex",
    )
    payload = downloader.fetch_json(
        OPENALEX_WORKS_URL,
        params=params,
        cache_key=f"openalex_{query}_{limit}",
        force=force,
    )

    results = payload.get("results") if isinstance(payload, dict) else None
    if not isinstance(results, list):
        raise DataSourceUnavailableError("OpenAlex", "unexpected response structure")

    records = [
        {
            "id": work.get("id", ""),
            "title": work.get("title") or "",
            "publication_year": work.get("publication_year"),
            "doi": work.get("doi") or "",
            "cited_by_count": work.get("cited_by_count", 0),
            "type": work.get("type") or "",
            "abstract": _reconstruct_abstract(work.get("abstract_inverted_index")),
        }
        for work in results
        if isinstance(work, dict)
    ]

    frame = pd.DataFrame(records)
    if not frame.empty:
        frame["publication_year"] = pd.to_numeric(
            frame["publication_year"], errors="coerce"
        ).astype("Int64")
        frame = frame.sort_values("cited_by_count", ascending=False)
    logger.info("OpenAlex: {} works for query '{}'", len(frame), query)
    return frame.reset_index(drop=True)
