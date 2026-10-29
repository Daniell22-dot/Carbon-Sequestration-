"""Base downloader with on-disk caching, retries, and provenance metadata."""

from __future__ import annotations

import time
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

import requests

from src.constants import (
    DEFAULT_BACKOFF_FACTOR,
    DEFAULT_CACHE_HOURS,
    DEFAULT_MAX_RETRIES,
    DEFAULT_TIMEOUT_SECONDS,
    RAW_DATA_DIR,
    USER_AGENT,
)
from src.utils.helpers import slugify
from src.utils.io import (
    ensure_dir,
    read_json,
    sha256_bytes,
    utc_now_iso,
    write_metadata,
)
from src.utils.logging import get_logger

logger = get_logger(__name__)


class DataAcquisitionError(Exception):
    """Base exception for data acquisition failures."""


class DataSourceUnavailableError(DataAcquisitionError):
    """Raised when a primary data source cannot be reached or parsed."""

    def __init__(
        self,
        source: str,
        reason: str,
        fallback: str | None = None,
    ) -> None:
        self.source = source
        self.reason = reason
        self.fallback = fallback
        message = f"{source} unavailable: {reason}"
        if fallback:
            message += f" (fallback: {fallback})"
        super().__init__(message)


class DataValidationError(DataAcquisitionError):
    """Raised when downloaded data fails schema or integrity validation."""


class BaseDownloader:
    """Shared caching and HTTP behavior for data source clients.

    Downloaded payloads are stored on disk together with a ``.meta.json``
    sidecar recording the URL, fetch time, SHA-256 digest, and byte size.
    Fresh cache entries are reused; stale entries act as a fallback when the
    network is unavailable.

    Attributes:
        source_name: Human-readable source identifier used in metadata.
    """

    source_name: str = "unknown"

    def __init__(
        self,
        cache_dir: Path | str = RAW_DATA_DIR,
        cache_hours: int = DEFAULT_CACHE_HOURS,
        timeout: int = DEFAULT_TIMEOUT_SECONDS,
        max_retries: int = DEFAULT_MAX_RETRIES,
        backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
        session: requests.Session | None = None,
        source_name: str | None = None,
    ) -> None:
        if source_name is not None:
            self.source_name = source_name
        self.cache_dir = ensure_dir(cache_dir)
        self.cache_hours = cache_hours
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.session = session or requests.Session()
        self.session.headers.setdefault("User-Agent", USER_AGENT)

    def cache_paths(self, key: str, suffix: str) -> tuple[Path, Path]:
        """Return the data and metadata cache paths for a key."""
        safe_key = slugify(key)
        data_path = self.cache_dir / f"{safe_key}{suffix}"
        meta_path = self.cache_dir / f"{safe_key}{suffix}.meta.json"
        return data_path, meta_path

    def cache_is_fresh(self, meta_path: Path) -> bool:
        """Return ``True`` when cached metadata is within the TTL window."""
        if not meta_path.exists():
            return False
        try:
            metadata = read_json(meta_path)
            fetched_at = metadata.get("fetched_at_epoch")
            if fetched_at is None:
                return False
            age_hours = (time.time() - float(fetched_at)) / 3600.0
            return age_hours <= self.cache_hours
        except (OSError, ValueError, TypeError):
            return False

    def fetch(
        self,
        url: str,
        *,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
        suffix: str = ".json",
        cache_key: str | None = None,
        force: bool = False,
        validate: Callable[[bytes], None] | None = None,
    ) -> bytes:
        """Fetch a URL with caching, retries, and stale-cache fallback.

        Args:
            url: Resource URL.
            params: Optional query parameters.
            headers: Optional per-request headers.
            suffix: File suffix for the cached payload.
            cache_key: Stable cache key; defaults to the URL and sorted params.
            force: Bypass a fresh cache entry and refetch.
            validate: Optional callable invoked with the payload before caching.

        Returns:
            The raw response body.

        Raises:
            DataSourceUnavailableError: If the resource cannot be fetched and no
                cached copy exists.
            DataValidationError: If ``validate`` raises an exception.
        """
        key = cache_key or self._default_cache_key(url, params)
        data_path, meta_path = self.cache_paths(key, suffix)

        if not force and data_path.exists() and self.cache_is_fresh(meta_path):
            logger.info("Cache hit for {} ({})", key, data_path.name)
            return data_path.read_bytes()

        request_headers = {"User-Agent": USER_AGENT}
        if headers:
            request_headers.update(headers)

        last_error: BaseException | None = None
        delay = 1.0
        for attempt in range(self.max_retries + 1):
            try:
                response = self.session.get(
                    url,
                    params=dict(params) if params else None,
                    headers=request_headers,
                    timeout=self.timeout,
                )
                response.raise_for_status()
                payload = response.content
                if not payload:
                    raise DataSourceUnavailableError(
                        self.source_name, f"empty response from {url}"
                    )
                if validate is not None:
                    try:
                        validate(payload)
                    except Exception as error:
                        raise DataValidationError(
                            f"{self.source_name} payload failed validation: {error}"
                        ) from error

                ensure_dir(data_path.parent)
                data_path.write_bytes(payload)
                metadata = {
                    "source": self.source_name,
                    "url": url,
                    "params": dict(params) if params else {},
                    "fetched_at": utc_now_iso(),
                    "fetched_at_epoch": time.time(),
                    "sha256": sha256_bytes(payload),
                    "bytes": len(payload),
                    "content_type": response.headers.get("Content-Type", ""),
                }
                write_metadata(data_path, metadata)
                logger.info(
                    "Downloaded {} ({} bytes) from {}",
                    key,
                    len(payload),
                    url,
                )
                return payload
            except DataValidationError:
                raise
            except (requests.RequestException, DataSourceUnavailableError) as error:
                last_error = error
                if attempt >= self.max_retries:
                    break
                logger.warning(
                    "Attempt {}/{} failed for {}: {}",
                    attempt + 1,
                    self.max_retries + 1,
                    key,
                    error,
                )
                time.sleep(delay)
                delay *= self.backoff_factor

        if data_path.exists():
            logger.warning(
                "Network failed for {}; using stale cache at {}",
                key,
                data_path,
            )
            return data_path.read_bytes()

        raise DataSourceUnavailableError(
            self.source_name,
            str(last_error) if last_error else "unknown error",
            fallback="no cached copy available",
        )

    def fetch_json(
        self,
        url: str,
        *,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
        cache_key: str | None = None,
        force: bool = False,
    ) -> Any:
        """Fetch and decode a JSON resource."""
        import json

        payload = self.fetch(
            url,
            params=params,
            headers=headers,
            suffix=".json",
            cache_key=cache_key,
            force=force,
        )
        try:
            return json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise DataSourceUnavailableError(
                self.source_name, f"invalid JSON payload: {error}"
            ) from error

    @staticmethod
    def _default_cache_key(url: str, params: Mapping[str, Any] | None) -> str:
        if not params:
            return url
        rendered = "&".join(f"{key}={params[key]}" for key in sorted(params))
        return f"{url}?{rendered}"
