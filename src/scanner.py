"""Scans a GitHub repository for open issues."""

import logging
from dataclasses import dataclass, field

import requests

from src.config import Config

logger = logging.getLogger(__name__)


@dataclass
class Issue:
    """Lightweight representation of a GitHub issue."""

    number: int
    title: str
    body: str
    labels: list[str] = field(default_factory=list)
    html_url: str = ""


def fetch_open_issues() -> list[Issue]:
    """Return all open issues (not pull requests) from the target repo."""

    url = f"{Config.GITHUB_API_URL}/repos/{Config.TARGET_REPO}/issues"
    headers = {
        "Authorization": f"token {Config.GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }
    params: dict[str, str | int] = {"state": "open", "per_page": 100}

    if Config.ISSUE_LABELS:
        params["labels"] = Config.ISSUE_LABELS

    all_issues: list[Issue] = []
    page = 1

    while True:
        params["page"] = page
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        items = resp.json()

        if not items:
            break

        for item in items:
            # GitHub's issues endpoint also returns PRs; skip them.
            if "pull_request" in item:
                continue
            all_issues.append(
                Issue(
                    number=item["number"],
                    title=item["title"],
                    body=item.get("body") or "",
                    labels=[lbl["name"] for lbl in item.get("labels", [])],
                    html_url=item.get("html_url", ""),
                )
            )

        page += 1

    logger.info("Fetched %d open issue(s) from %s", len(all_issues), Config.TARGET_REPO)
    return all_issues
