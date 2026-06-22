"""Configuration loaded from environment variables."""

import os


class Config:
    """All settings are read from environment variables at import time."""

    GITHUB_TOKEN: str = os.environ.get("GITHUB_TOKEN", "")
    DEVIN_API_KEY: str = os.environ.get("DEVIN_API_KEY", "")

    # Repository to scan for issues (owner/repo format)
    TARGET_REPO: str = os.environ.get("TARGET_REPO", "nehap29/superset")

    # How often the scanner runs (cron expression, used by docker-compose/scheduler)
    SCAN_INTERVAL_SECONDS: int = int(os.environ.get("SCAN_INTERVAL_SECONDS", "3600"))

    # Path to the JSON file tracking which issues already have sessions
    STATE_FILE: str = os.environ.get("STATE_FILE", "/data/state.json")

    # Devin API base URL
    DEVIN_API_URL: str = os.environ.get("DEVIN_API_URL", "https://api.devin.ai/v1")

    # GitHub API base URL
    GITHUB_API_URL: str = os.environ.get("GITHUB_API_URL", "https://api.github.com")

    # Maximum ACU limit per Devin session (controls cost)
    MAX_ACU_LIMIT: int = int(os.environ.get("MAX_ACU_LIMIT", "10"))

    # Whether to post status comments back on the GitHub issue
    POST_STATUS_COMMENTS: bool = os.environ.get("POST_STATUS_COMMENTS", "true").lower() == "true"

    # Labels to filter issues (comma-separated). Empty means all open issues.
    ISSUE_LABELS: str = os.environ.get("ISSUE_LABELS", "")

    # Log level
    LOG_LEVEL: str = os.environ.get("LOG_LEVEL", "INFO")

    @classmethod
    def validate(cls) -> list[str]:
        """Return a list of missing required config keys."""
        missing = []
        if not cls.GITHUB_TOKEN:
            missing.append("GITHUB_TOKEN")
        if not cls.DEVIN_API_KEY:
            missing.append("DEVIN_API_KEY")
        return missing
