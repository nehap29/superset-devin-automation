"""Logging configuration — plain text or JSON output.

Call ``setup()`` once at application startup (in ``main.py``).
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any

from src.config import Config


class _JsonFormatter(logging.Formatter):
    """Emits one JSON object per log line — easy to parse in log aggregators."""

    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info and record.exc_info[1]:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry, default=str)


_TEXT_FORMAT = "%(asctime)s [%(levelname)s] %(name)s — %(message)s"


def setup() -> None:
    """Configure the root logger based on ``Config.LOG_FORMAT``."""
    root = logging.getLogger()
    root.setLevel(getattr(logging, Config.LOG_LEVEL, logging.INFO))

    handler = logging.StreamHandler(sys.stdout)

    if Config.LOG_FORMAT == "json":
        handler.setFormatter(_JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter(_TEXT_FORMAT))

    root.handlers.clear()
    root.addHandler(handler)
