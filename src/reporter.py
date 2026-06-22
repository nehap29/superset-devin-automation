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
        "=" * 60,
        "  SUPERSET ISSUE AUTOMATION — STATUS REPORT",
        f"  Generated {now}",
        "=" * 60,
        "",
        "SYSTEM HEALTH",
        "-" * 40,
        _health_table(metrics, state),
        "",
        "SESSION OUTCOMES",
        "-" * 40,
        _outcomes_table(status_counts),
        "",
        "ISSUE DETAILS",
        "-" * 40,
        _issue_table(state),
        "",
    ]

    if metrics.recent_cycles:
        lines += [
            "RECENT CYCLE HISTORY",
            "-" * 40,
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
    blocked_display = f"{blocked} (NEEDS ATTENTION)" if blocked else "0"
    rows = [
        ("Total scan cycles", str(metrics.total_cycles)),
        ("Issues tracked", str(len(state.records))),
        ("Sessions created", str(metrics.total_sessions_created)),
        ("Success rate", f"{metrics.success_rate()}%"),
        ("Blocked sessions", blocked_display),
        ("Total errors", str(metrics.total_errors)),
        ("Avg cycle duration", f"{metrics.avg_cycle_duration_seconds}s"),
        ("Last scan", metrics.last_cycle_at or "n/a"),
    ]
    width = max(len(r[0]) for r in rows)
    return "\n".join(f"  {label:<{width}}  {value}" for label, value in rows)


def _outcomes_table(counts: dict[str, int]) -> str:
    if not counts:
        return "_No sessions tracked yet._"
    lines = []
    for status, count in sorted(counts.items()):
        lines.append(f"  {status:<12} {count}")
    return "\n".join(lines)


def _issue_table(state: State) -> str:
    if not state.records:
        return "  (no issues processed yet)"
    header = f"  {'Issue':<8} {'Status':<12} {'PR':<50} Session"
    sep = "  " + "-" * (len(header) - 2)
    lines = [header, sep]
    for number, rec in sorted(state.records.items()):
        pr = rec.pr_url if rec.pr_url else "—"
        session = rec.session_url if rec.session_url else "—"
        lines.append(f"  #{number:<7} {rec.status:<12} {pr:<50} {session}")
    return "\n".join(lines)


def _cycle_history_table(metrics: MetricsSummary) -> str:
    # Fixed-width columns for clean console output
    header = (
        f"{'Cycle':>5}  {'Time':<20}  {'Duration':>8}  "
        f"{'Scanned':>7}  {'Created':>7}  {'Done':>4}  "
        f"{'Failed':>6}  {'Errors':>6}"
    )
    sep = "-" * len(header)
    lines = [header, sep]
    for c in metrics.recent_cycles[-10:]:
        lines.append(
            f"{c['cycle']:>5}  {c['at'][:19]:<20}  "
            f"{str(c['duration_s']) + 's':>8}  "
            f"{c['scanned']:>7}  {c['created']:>7}  "
            f"{c.get('done', 0):>4}  "
            f"{c['failed']:>6}  {c['errors']:>6}"
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
