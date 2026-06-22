"""Configuration loaded from environment variables.

All settings are read once at import time.  Call ``Config.validate()`` early
to fail fast on missing credentials.
"""

from __future__ import annotations

import os


class Config:
    """Centralised, environment-driven configuration."""

    # ── Required credentials ─────────────────────────────────────────
    GITHUB_TOKEN: str = os.environ.get("GITHUB_TOKEN", "")
    DEVIN_API_KEY: str = os.environ.get("DEVIN_API_KEY", "")

    # ── Target repository ────────────────────────────────────────────
    TARGET_REPO: str = os.environ.get("TARGET_REPO", "nehap29/superset")
    ISSUE_LABELS: str = os.environ.get("ISSUE_LABELS", "")

    # ── Scheduling ───────────────────────────────────────────────────
    SCAN_INTERVAL_SECONDS: int = int(
        os.environ.get("SCAN_INTERVAL_SECONDS", "3600")
    )

    # ── Persistence paths ────────────────────────────────────────────
    STATE_FILE: str = os.environ.get("STATE_FILE", "/data/state.json")
    METRICS_FILE: str = os.environ.get("METRICS_FILE", "/data/metrics.json")
    REPORT_FILE: str = os.environ.get("REPORT_FILE", "/data/report.md")

    # ── API base URLs ────────────────────────────────────────────────
    DEVIN_API_URL: str = os.environ.get(
        "DEVIN_API_URL", "https://api.devin.ai/v1"
    )
    GITHUB_API_URL: str = os.environ.get(
        "GITHUB_API_URL", "https://api.github.com"
    )

    # ── Devin session limits ─────────────────────────────────────────
    MAX_ACU_LIMIT: int = int(os.environ.get("MAX_ACU_LIMIT", "10"))

    # ── Behaviour flags ──────────────────────────────────────────────
    POST_STATUS_COMMENTS: bool = (
        os.environ.get("POST_STATUS_COMMENTS", "true").lower() == "true"
    )

    # ── Logging ──────────────────────────────────────────────────────
    LOG_LEVEL: str = os.environ.get("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = os.environ.get("LOG_FORMAT", "text")  # "text" or "json"

    @classmethod
    def validate(cls) -> list[str]:
        """Return a list of missing required config keys (empty = OK)."""
        missing: list[str] = []
        if not cls.GITHUB_TOKEN:
            missing.append("GITHUB_TOKEN")
        if not cls.DEVIN_API_KEY:
            missing.append("DEVIN_API_KEY")
        return missing
