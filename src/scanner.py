"""Scans a GitHub repository for open issues."""

from __future__ import annotations

import logging
from typing import Any

from src.config import Config
from src.http_client import get, github_headers
from src.models import Issue

logger = logging.getLogger(__name__)


def fetch_open_issues() -> list[Issue]:
    """Return all open issues (excluding pull requests) from the target repo.

    Paginates through the GitHub REST API and filters out entries that are
    actually pull requests (GitHub's ``/issues`` endpoint returns both).
    """
    url = f"{Config.GITHUB_API_URL}/repos/{Config.TARGET_REPO}/issues"
    headers = github_headers()
    params: dict[str, Any] = {"state": "open", "per_page": 100}

    if Config.ISSUE_LABELS:
        params["labels"] = Config.ISSUE_LABELS

    issues: list[Issue] = []
    page = 1

    while True:
        params["page"] = page
        resp = get(url, headers=headers, params=params)
        items: list[dict[str, Any]] = resp.json()

        if not items:
            break

        for item in items:
            if "pull_request" in item:
                continue
            issues.append(
                Issue(
                    number=item["number"],
                    title=item["title"],
                    body=item.get("body") or "",
                    labels=[lbl["name"] for lbl in item.get("labels", [])],
                    html_url=item.get("html_url", ""),
                )
            )

        page += 1

    logger.info(
        "Fetched %d open issue(s) from %s (page count: %d)",
        len(issues),
        Config.TARGET_REPO,
        page - 1,
    )
    return issues
