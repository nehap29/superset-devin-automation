"""Creates and monitors Devin sessions via the REST API."""

import logging
from datetime import datetime, timezone

import requests

from src.config import Config
from src.scanner import Issue
from src.state import SessionRecord

logger = logging.getLogger(__name__)


def _build_prompt(issue: Issue) -> str:
    """Build a Devin session prompt from a GitHub issue."""
    prompt_parts = [
        f"## GitHub Issue #{issue.number}: {issue.title}",
        "",
        f"Repository: {Config.TARGET_REPO}",
        f"Issue URL: {issue.html_url}",
        "",
        "### Issue Description",
        issue.body or "(no description provided)",
        "",
        "### Instructions",
        "1. Read and understand the issue above.",
        "2. Explore the repository to find the relevant code.",
        "3. Implement the fix or feature described in the issue.",
        "4. Create a pull request with your changes.",
        "5. Ensure lint and tests pass.",
    ]
    return "\n".join(prompt_parts)


def create_session(issue: Issue) -> SessionRecord:
    """Create a Devin session for the given issue. Returns a SessionRecord."""
    url = f"{Config.DEVIN_API_URL}/sessions"
    headers = {
        "Authorization": f"Bearer {Config.DEVIN_API_KEY}",
        "Content-Type": "application/json",
    }
    prompt = _build_prompt(issue)
    payload = {
        "prompt": prompt,
        "title": f"[Auto] Issue #{issue.number}: {issue.title}",
        "tags": [
            "superset-automation",
            f"issue-{issue.number}",
        ],
        "max_acu_limit": Config.MAX_ACU_LIMIT,
        "idempotent": True,
    }

    resp = requests.post(url, headers=headers, json=payload, timeout=60)
    resp.raise_for_status()
    data = resp.json()

    session_id = data["session_id"]
    session_url = data["url"]
    logger.info(
        "Created Devin session %s for issue #%d — %s",
        session_id,
        issue.number,
        session_url,
    )

    return SessionRecord(
        issue_number=issue.number,
        session_id=session_id,
        session_url=session_url,
        created_at=datetime.now(timezone.utc).isoformat(),
        status="created",
    )


def get_session_status(session_id: str) -> dict:
    """Poll the status of an existing Devin session."""
    url = f"{Config.DEVIN_API_URL}/session/{session_id}"
    headers = {"Authorization": f"Bearer {Config.DEVIN_API_KEY}"}

    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json()
