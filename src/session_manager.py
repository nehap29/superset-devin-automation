"""Creates and monitors Devin sessions via the REST API."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from src.config import Config
from src.http_client import devin_headers, get, post
from src.models import Issue, SessionRecord

logger = logging.getLogger(__name__)


# ── Response model ───────────────────────────────────────────────────


@dataclass
class SessionStatus:
    """Parsed response from the Devin session-status endpoint."""

    status: str
    pr_url: str = ""

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> SessionStatus:
        pr_url = ""
        structured = data.get("structured_outputs")
        if isinstance(structured, dict):
            pr_url = structured.get("pr_url", "")
        return cls(
            status=data.get("status_enum", "unknown"),
            pr_url=pr_url,
        )


# ── Prompt builder ───────────────────────────────────────────────────


def _build_prompt(issue: Issue) -> str:
    """Construct the Devin session prompt from an issue."""
    return "\n".join([
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
    ])


# ── Public API ───────────────────────────────────────────────────────


def create_session(issue: Issue) -> SessionRecord:
    """Create a Devin session for the given issue."""
    url = f"{Config.DEVIN_API_URL}/sessions"
    payload = {
        "prompt": _build_prompt(issue),
        "title": f"[Auto] Issue #{issue.number}: {issue.title}",
        "tags": ["superset-automation", f"issue-{issue.number}"],
        "max_acu_limit": Config.MAX_ACU_LIMIT,
        "idempotent": True,
    }

    resp = post(url, headers=devin_headers(), json_body=payload, timeout=60)
    data: dict[str, Any] = resp.json()

    session_id: str = data["session_id"]
    session_url: str = data["url"]

    logger.info(
        "Created session %s for issue #%d — %s",
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


def get_session_status(session_id: str) -> SessionStatus:
    """Poll the current status of a Devin session."""
    url = f"{Config.DEVIN_API_URL}/session/{session_id}"
    resp = get(url, headers=devin_headers())
    return SessionStatus.from_api(resp.json())
