"""File I/O helpers with atomic writes and provenance metadata."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from collections.abc import Iterable, Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


def ensure_dir(path: Path | str) -> Path:
    """Create a directory (and parents) if it does not exist.

    Args:
        path: Directory to create.

    Returns:
        The resolved :class:`Path`.
    """
    resolved = Path(path)
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def utc_now() -> datetime:
    """Return the current UTC timestamp as a timezone-aware datetime."""
    return datetime.now(timezone.utc)


def utc_now_iso() -> str:
    """Return the current UTC timestamp in ISO 8601 format."""
    return utc_now().isoformat()


def sha256_bytes(payload: bytes) -> str:
    """Return the hexadecimal SHA-256 digest of a byte payload."""
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path | str) -> str:
    """Return the hexadecimal SHA-256 digest of a file."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_write_bytes(path: Path | str, payload: bytes) -> Path:
    """Write bytes atomically by writing to a temporary file then replacing.

    Args:
        path: Destination path.
        payload: Bytes to write.

    Returns:
        The destination path.
    """
    destination = Path(path)
    ensure_dir(destination.parent)
    descriptor, temp_name = tempfile.mkstemp(dir=destination.parent, prefix=".tmp-")
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, destination)
    except BaseException:
        if os.path.exists(temp_name):
            os.unlink(temp_name)
        raise
    return destination


def write_json(path: Path | str, payload: Any, indent: int = 2) -> Path:
    """Serialize ``payload`` to JSON atomically.

    Args:
        path: Destination path.
        payload: JSON-serializable object.
        indent: Indentation level.

    Returns:
        The destination path.
    """
    text = json.dumps(payload, indent=indent, ensure_ascii=False, default=str)
    return atomic_write_bytes(path, text.encode("utf-8"))


def read_json(path: Path | str) -> Any:
    """Read and decode a JSON document."""
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_dataframe(
    df: pd.DataFrame,
    path: Path | str,
    index: bool = False,
    **kwargs: Any,
) -> Path:
    """Write a DataFrame to CSV, Parquet, JSON, or Excel based on suffix.

    Args:
        df: DataFrame to persist.
        path: Destination path; the suffix selects the writer.
        index: Whether to include the index.
        **kwargs: Extra keyword arguments forwarded to the pandas writer.

    Returns:
        The destination path.

    Raises:
        ValueError: If the suffix is unsupported.
    """
    destination = Path(path)
    ensure_dir(destination.parent)
    suffix = destination.suffix.lower()

    if suffix in {".csv", ".txt"}:
        df.to_csv(destination, index=index, **kwargs)
    elif suffix in {".parquet", ".pq"}:
        df.to_parquet(destination, index=index, **kwargs)
    elif suffix == ".json":
        df.to_json(destination, orient="records", indent=2, **kwargs)
    elif suffix in {".xlsx", ".xls"}:
        df.to_excel(destination, index=index, **kwargs)
    else:
        raise ValueError(f"Unsupported dataframe format: {suffix}")

    return destination


def write_metadata(path: Path | str, metadata: Mapping[str, Any]) -> Path:
    """Write provenance metadata next to a data file.

    Args:
        path: Path of the associated data file.
        metadata: Provenance fields (source, url, fetched_at, sha256, ...).

    Returns:
        Path of the written ``.meta.json`` file.
    """
    data_path = Path(path)
    meta_path = data_path.with_suffix(data_path.suffix + ".meta.json")
    return write_json(meta_path, dict(metadata))


def list_files(directory: Path | str, pattern: str = "*") -> Iterable[Path]:
    """Yield files matching ``pattern`` in ``directory``, sorted by name."""
    return sorted(Path(directory).glob(pattern))
