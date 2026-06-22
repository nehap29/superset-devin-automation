"""Posts status updates to GitHub issues and generates summary reports."""

import logging
from datetime import datetime, timezone

import requests

from src.config import Config
from src.state import SessionRecord, State

logger = logging.getLogger(__name__)


def post_issue_comment(issue_number: int, body: str) -> None:
    """Post a comment on a GitHub issue."""
    if not Config.POST_STATUS_COMMENTS:
        logger.debug("Status comments disabled — skipping comment on #%d", issue_number)
        return

    url = (
        f"{Config.GITHUB_API_URL}/repos/{Config.TARGET_REPO}"
        f"/issues/{issue_number}/comments"
    )
    headers = {
        "Authorization": f"token {Config.GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }
    resp = requests.post(url, headers=headers, json={"body": body}, timeout=30)
    resp.raise_for_status()
    logger.info("Posted comment on issue #%d", issue_number)


def notify_session_created(record: SessionRecord) -> None:
    """Comment on the GitHub issue that a Devin session was started."""
    body = (
        f"**Devin Automation** started a session for this issue.\n\n"
        f"- **Session ID:** `{record.session_id}`\n"
        f"- **Session URL:** {record.session_url}\n"
        f"- **Created at:** {record.created_at}\n\n"
        f"Devin will analyze this issue, implement a fix, and open a PR. "
        f"Status updates will follow."
    )
    post_issue_comment(record.issue_number, body)


def notify_session_update(record: SessionRecord) -> None:
    """Comment on the GitHub issue with a session status update."""
    lines = [
        f"**Devin Automation** — session status update.",
        "",
        f"- **Status:** `{record.status}`",
        f"- **Session URL:** {record.session_url}",
    ]
    if record.pr_url:
        lines.append(f"- **Pull Request:** {record.pr_url}")
    post_issue_comment(record.issue_number, "\n".join(lines))


def generate_summary_report(state: State) -> str:
    """Return a Markdown summary of all tracked sessions."""
    now = datetime.now(timezone.utc).isoformat()
    lines = [
        "# Superset Issue Automation — Summary Report",
        "",
        f"_Generated at {now}_",
        "",
        f"**Target repo:** `{Config.TARGET_REPO}`",
        f"**Tracked issues:** {len(state.records)}",
        "",
        "| Issue | Status | Session | PR |",
        "|-------|--------|---------|----|",
    ]

    for number, rec in sorted(state.records.items()):
        issue_link = f"[#{number}](https://github.com/{Config.TARGET_REPO}/issues/{number})"
        session_link = f"[link]({rec.session_url})" if rec.session_url else "—"
        pr_link = f"[PR]({rec.pr_url})" if rec.pr_url else "—"
        lines.append(f"| {issue_link} | `{rec.status}` | {session_link} | {pr_link} |")

    report = "\n".join(lines)
    logger.info("Generated summary report (%d records)", len(state.records))
    return report
