"""Geospatial exports for stations, projects, and analysis results."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from src.constants import STATIONS
from src.utils.io import ensure_dir
from src.utils.logging import get_logger

logger = get_logger(__name__)


def _require_geopandas() -> Any:
    try:
        import geopandas as gpd
    except ImportError as error:  # pragma: no cover - depends on environment
        raise ImportError(
            "geopandas is required for GIS exports; install the 'geo' extra"
        ) from error
    return gpd


def stations_geodataframe() -> Any:
    """Build a GeoDataFrame of NOAA station locations.

    Returns:
        GeoDataFrame with station metadata and point geometry (EPSG:4326).

    Raises:
        ImportError: If geopandas is not installed.
    """
    gpd = _require_geopandas()
    records = [
        {
            "station": code,
            "name": metadata["name"],
            "latitude": metadata["latitude"],
            "longitude": metadata["longitude"],
            "elevation_m": metadata["elevation_m"],
            "country": metadata["country"],
        }
        for code, metadata in STATIONS.items()
    ]
    frame = pd.DataFrame(records)
    geometry = gpd.points_from_xy(frame["longitude"], frame["latitude"])
    return gpd.GeoDataFrame(frame, geometry=geometry, crs="EPSG:4326")


def projects_geodataframe(frame: pd.DataFrame) -> Any:
    """Build a GeoDataFrame from a project table.

    Args:
        frame: Project table with ``latitude`` and ``longitude`` columns.

    Returns:
        GeoDataFrame with point geometry (EPSG:4326).

    Raises:
        ValueError: If coordinate columns are missing.
        ImportError: If geopandas is not installed.
    """
    if not {"latitude", "longitude"}.issubset(frame.columns):
        raise ValueError("Project table requires latitude and longitude columns")
    gpd = _require_geopandas()
    data = frame.dropna(subset=["latitude", "longitude"]).copy()
    geometry = gpd.points_from_xy(data["longitude"], data["latitude"])
    return gpd.GeoDataFrame(data, geometry=geometry, crs="EPSG:4326")


def save_geopackage(
    frame: Any,
    path: Path | str,
    layer: str = "features",
) -> Path:
    """Write a GeoDataFrame to a GeoPackage.

    Args:
        frame: GeoDataFrame.
        path: Destination ``.gpkg`` path.
        layer: Layer name.

    Returns:
        The destination path.
    """
    destination = Path(path)
    ensure_dir(destination.parent)
    frame.to_file(destination, layer=layer, driver="GPKG")
    logger.info("Wrote GeoPackage layer '{}' to {}", layer, destination)
    return destination


def save_shapefile(
    frame: Any,
    directory: Path | str,
    layer: str = "features",
) -> Path:
    """Write a GeoDataFrame to an ESRI Shapefile.

    Args:
        frame: GeoDataFrame.
        directory: Destination directory.
        layer: Base filename for the shapefile.

    Returns:
        Path to the generated ``.shp`` file.
    """
    destination = ensure_dir(directory)
    path = destination / f"{layer}.shp"
    frame.to_file(path, driver="ESRI Shapefile")
    return path


def create_folium_map(
    frame: Any,
    location: tuple[float, float] | None = None,
    zoom_start: int = 2,
) -> Any:
    """Create an interactive Folium map from point features.

    Args:
        frame: GeoDataFrame with point geometry and a ``name`` or ``method``
            label column.
        location: Optional initial map centre as ``(latitude, longitude)``.
        zoom_start: Initial zoom level.

    Returns:
        A Folium map.

    Raises:
        ImportError: If folium is not installed.
    """
    try:
        import folium
    except ImportError as error:  # pragma: no cover
        raise ImportError("folium is required for interactive maps") from error

    centre = location or (
        float(frame.geometry.y.mean()),
        float(frame.geometry.x.mean()),
    )
    map_object = folium.Map(location=list(centre), zoom_start=zoom_start)
    for _, row in frame.iterrows():
        label = row.get("name") or row.get("project_name") or row.get("method") or "Feature"
        folium.Marker(
            location=[row.geometry.y, row.geometry.x],
            popup=str(label),
        ).add_to(map_object)
    return map_object


def save_folium_map(map_object: Any, path: Path | str) -> Path:
    """Save a Folium map to HTML."""
    destination = Path(path)
    ensure_dir(destination.parent)
    map_object.save(str(destination))
    return destination
