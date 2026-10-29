"""Structured logging configuration.

Uses :mod:`loguru` when available and falls back to the standard library so
that lightweight tooling (for example, import checks) never fails on a missing
optional dependency.
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Any

try:  # pragma: no cover - exercised only when loguru is absent
    from loguru import logger as _loguru_logger
except ImportError:  # pragma: no cover
    _loguru_logger = None

_CONFIGURED = False


class _StdlibAdapter:
    """Minimal loguru-compatible facade backed by :mod:`logging`."""

    def __init__(self, name: str = "carbon") -> None:
        self._logger = logging.getLogger(name)

    def bind(self, **_kwargs: Any) -> _StdlibAdapter:
        return self

    def debug(self, message: str, *args: Any, **kwargs: Any) -> None:
        self._logger.debug(message.format(*args) if args else message, **kwargs)

    def info(self, message: str, *args: Any, **kwargs: Any) -> None:
        self._logger.info(message.format(*args) if args else message, **kwargs)

    def warning(self, message: str, *args: Any, **kwargs: Any) -> None:
        self._logger.warning(message.format(*args) if args else message, **kwargs)

    def error(self, message: str, *args: Any, **kwargs: Any) -> None:
        self._logger.error(message.format(*args) if args else message, **kwargs)

    def exception(self, message: str, *args: Any, **kwargs: Any) -> None:
        self._logger.exception(message.format(*args) if args else message, **kwargs)


def setup_logging(level: str | None = None) -> Any:
    """Configure and return the process-wide logger.

    Args:
        level: Log level name. Defaults to the ``LOG_LEVEL`` environment
            variable or ``INFO``.

    Returns:
        A loguru logger, or a stdlib-backed adapter when loguru is missing.
    """
    global _CONFIGURED

    resolved = (level or os.environ.get("LOG_LEVEL") or "INFO").upper()

    if _loguru_logger is None:  # pragma: no cover
        logging.basicConfig(
            level=getattr(logging, resolved, logging.INFO),
            format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            stream=sys.stderr,
        )
        return _StdlibAdapter()

    if not _CONFIGURED:
        _loguru_logger.remove()
        _loguru_logger.add(
            sys.stderr,
            level=resolved,
            format=(
                "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>"
            ),
            colorize=True,
        )
        _CONFIGURED = True
    else:
        _loguru_logger.remove()
        _loguru_logger.add(sys.stderr, level=resolved)

    return _loguru_logger


def get_logger(name: str | None = None) -> Any:
    """Return a logger, optionally bound to a module name."""
    logger = setup_logging()
    return logger.bind(module=name) if name else logger
