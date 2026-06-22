"""Status updates on GitHub issues and executive-ready summary reports.

Produces two kinds of output:

1. **Issue comments** — posted on individual GitHub issues when a session is
   created or its status changes.
2. **Summary report** — a Markdown document answering "is this system working?"
   with throughput, success rates, and per-issue status.  Written to
   ``Config.REPORT_FILE`` and logged every cycle.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

from src.config import Config
from src.http_client import github_headers, post
from src.metrics import MetricsSummary, load_metrics
from src.models import SessionRecord
from src.state import State

logger = logging.getLogger(__name__)


# ── GitHub issue comments ────────────────────────────────────────────


def post_issue_comment(issue_number: int, body: str) -> bool:
    """Post a comment on a GitHub issue.  Returns True on success."""
    if not Config.POST_STATUS_COMMENTS:
        logger.debug("Comments disabled — skipping #%d", issue_number)
        return False

    url = (
        f"{Config.GITHUB_API_URL}/repos/{Config.TARGET_REPO}"
        f"/issues/{issue_number}/comments"
    )
    try:
        post(url, headers=github_headers(), json_body={"body": body})
        logger.info("Commented on issue #%d", issue_number)
        return True
    except Exception:
        logger.exception("Failed to comment on issue #%d", issue_number)
        return False


def notify_session_created(record: SessionRecord) -> bool:
    body = (
        f"**Devin Automation** started a session for this issue.\n\n"
        f"| Field | Value |\n"
        f"|-------|-------|\n"
        f"| Session ID | `{record.session_id}` |\n"
        f"| Session URL | {record.session_url} |\n"
        f"| Created | {record.created_at} |\n\n"
        f"Devin will analyse this issue, implement a fix, and open a PR. "
        f"Status updates will follow."
    )
    return post_issue_comment(record.issue_number, body)


def notify_session_blocked(record: SessionRecord) -> bool:
    lines = [
        "**Devin Automation** — session is **blocked** and needs attention.",
        "",
        "This is a fully automated system with no human in the loop, so "
        "blocked sessions cannot be unblocked automatically.",
        "",
        f"| Field | Value |",
        f"|-------|-------|",
        f"| Status | `blocked` |",
        f"| Session | {record.session_url} |",
    ]
    if record.pr_url:
        lines.append(f"| Pull Request | {record.pr_url} |")
    lines += [
        "",
        "Please review the session and unblock it manually, or close this "
        "issue if no action is needed.",
    ]
    return post_issue_comment(record.issue_number, "\n".join(lines))


def notify_session_update(record: SessionRecord) -> bool:
    lines = [
        "**Devin Automation** — status update.",
        "",
        f"| Field | Value |",
        f"|-------|-------|",
        f"| Status | `{record.status}` |",
        f"| Session | {record.session_url} |",
    ]
    if record.pr_url:
        lines.append(f"| Pull Request | {record.pr_url} |")
    return post_issue_comment(record.issue_number, "\n".join(lines))


# ── Executive summary report ─────────────────────────────────────────


def generate_summary_report(state: State) -> str:
    """Build a Markdown report aimed at engineering leadership.

    Sections:
      - System health at a glance (success rate, throughput, uptime proxy)
      - Per-issue status table
      - Recent cycle history
    """
    metrics = load_metrics()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    status_counts = state.count_by_status()

    lines = [
        "# Superset Issue Automation — Status Report",
        "",
        f"_Generated {now}_",
        "",
        "---",
        "",
        "## System Health",
        "",
        _health_table(metrics, state),
        "",
        "## Session Outcomes",
        "",
        _outcomes_table(status_counts),
        "",
        "## Issue Details",
        "",
        _issue_table(state),
        "",
    ]

    if metrics.recent_cycles:
        lines += [
            "## Recent Cycle History",
            "",
            _cycle_history_table(metrics),
            "",
        ]

    report = "\n".join(lines)

    _persist_report(report)
    return report


# ── Report building blocks ───────────────────────────────────────────


def _health_table(metrics: MetricsSummary, state: State) -> str:
    counts = state.count_by_status()
    blocked = counts.get("blocked", 0)
    blocked_display = f"**{blocked}** (needs attention)" if blocked else "0"
    return "\n".join([
        "| Metric | Value |",
        "|--------|-------|",
        f"| Total scan cycles | {metrics.total_cycles} |",
        f"| Issues tracked | {len(state.records)} |",
        f"| Sessions created | {metrics.total_sessions_created} |",
        f"| Session creation success rate | {metrics.success_rate()}% |",
        f"| Blocked sessions | {blocked_display} |",
        f"| Total errors | {metrics.total_errors} |",
        f"| Avg cycle duration | {metrics.avg_cycle_duration_seconds}s |",
        f"| Last scan | {metrics.last_cycle_at or 'n/a'} |",
    ])


def _outcomes_table(counts: dict[str, int]) -> str:
    if not counts:
        return "_No sessions tracked yet._"
    lines = ["| Status | Count |", "|--------|-------|"]
    for status, count in sorted(counts.items()):
        lines.append(f"| `{status}` | {count} |")
    return "\n".join(lines)


def _issue_table(state: State) -> str:
    if not state.records:
        return "_No issues processed yet._"
    lines = [
        "| Issue | Status | Session | PR |",
        "|-------|--------|---------|----|",
    ]
    for number, rec in sorted(state.records.items()):
        issue = f"[#{number}](https://github.com/{Config.TARGET_REPO}/issues/{number})"
        session = f"[link]({rec.session_url})" if rec.session_url else "—"
        pr = f"[PR]({rec.pr_url})" if rec.pr_url else "—"
        lines.append(f"| {issue} | `{rec.status}` | {session} | {pr} |")
    return "\n".join(lines)


def _cycle_history_table(metrics: MetricsSummary) -> str:
    lines = [
        "| Cycle | Time | Duration | Scanned | Created | Failed | Errors |",
        "|-------|------|----------|---------|---------|--------|--------|",
    ]
    for c in metrics.recent_cycles[-10:]:
        lines.append(
            f"| {c['cycle']} | {c['at'][:19]} | {c['duration_s']}s "
            f"| {c['scanned']} | {c['created']} | {c['failed']} | {c['errors']} |"
        )
    return "\n".join(lines)


def _persist_report(report: str) -> None:
    """Write the report to disk so it can be served or inspected."""
    path = Config.REPORT_FILE
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(path, "w") as fh:
        fh.write(report)
    logger.debug("Report written to %s", path)
