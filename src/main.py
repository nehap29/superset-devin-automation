"""Entrypoint — scan issues, create sessions, update status, report.

Supports two modes:
  ``python -m src.main``        → continuous loop (default)
  ``python -m src.main once``   → single scan cycle
"""

from __future__ import annotations

import logging
import sys
import time

from src import logging_setup
from src.config import Config
from src.metrics import CycleTracker
from src.reporter import (
    generate_summary_report,
    notify_session_created,
    notify_session_update,
)
from src.scanner import fetch_open_issues
from src.session_manager import create_session, get_session_status
from src.state import load_state, save_state

logging_setup.setup()
logger = logging.getLogger(__name__)


def run_once() -> None:
    """Execute a single scan → create → poll → report cycle."""
    missing = Config.validate()
    if missing:
        logger.error("Missing required config: %s", ", ".join(missing))
        sys.exit(1)

    with CycleTracker() as cycle:
        # 1. Load persisted state
        state = load_state()
        logger.info(
            "State loaded — %d existing record(s)", len(state.records)
        )

        # 2. Fetch open issues
        issues = fetch_open_issues()
        cycle.issues_scanned = len(issues)

        new_issues = [i for i in issues if not state.has_session(i.number)]
        cycle.new_issues_found = len(new_issues)
        logger.info("%d new issue(s) to process", len(new_issues))

        # 3. Create Devin sessions for new issues
        for issue in new_issues:
            try:
                record = create_session(issue)
                state.add_record(record)
                save_state(state)
                if notify_session_created(record):
                    cycle.comments_posted += 1
                cycle.sessions_created += 1
            except Exception:
                logger.exception(
                    "Failed to create session for issue #%d", issue.number
                )
                cycle.sessions_failed += 1
                cycle.errors.append(f"create_session(#{issue.number})")

        # 4. Poll existing sessions for status changes
        for number, record in list(state.records.items()):
            if record.status in ("finished", "expired"):
                continue
            try:
                status = get_session_status(record.session_id)
                cycle.sessions_polled += 1

                changed = status.status != record.status
                has_new_pr = bool(status.pr_url and not record.pr_url)

                if changed or has_new_pr:
                    # If session is blocked but has a PR, mark as finished
                    effective_status = status.status
                    if status.is_effectively_done and status.status == "blocked":
                        effective_status = "finished"
                        logger.info(
                            "Issue #%d: session blocked with PR — marking finished",
                            number,
                        )

                    state.update_status(
                        number, effective_status, status.pr_url
                    )
                    save_state(state)
                    if notify_session_update(state.records[number]):
                        cycle.comments_posted += 1
                    cycle.status_changes_detected += 1
            except Exception:
                logger.exception(
                    "Failed to poll session for issue #%d", number
                )
                cycle.errors.append(f"poll(#{number})")

        # 5. Generate and log summary report
        report = generate_summary_report(state)
        logger.info("\n%s", report)


def run_loop() -> None:
    """Run ``run_once`` in a loop with a configurable sleep interval."""
    logger.info(
        "Starting automation loop — interval=%ds target=%s",
        Config.SCAN_INTERVAL_SECONDS,
        Config.TARGET_REPO,
    )
    while True:
        try:
            run_once()
        except SystemExit:
            raise
        except Exception:
            logger.exception("Unhandled error in scan cycle")
        logger.info(
            "Sleeping %ds until next scan …", Config.SCAN_INTERVAL_SECONDS
        )
        time.sleep(Config.SCAN_INTERVAL_SECONDS)


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "loop"
    if mode == "once":
        run_once()
    else:
        run_loop()
