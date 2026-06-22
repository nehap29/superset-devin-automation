"""Entrypoint: scan issues, create sessions, update status, report."""

import logging
import sys
import time

from src.config import Config
from src.reporter import (
    generate_summary_report,
    notify_session_created,
    notify_session_update,
)
from src.scanner import fetch_open_issues
from src.session_manager import create_session, get_session_status
from src.state import load_state, save_state

logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


def run_once() -> None:
    """Execute a single scan-create-report cycle."""
    missing = Config.validate()
    if missing:
        logger.error("Missing required config: %s", ", ".join(missing))
        sys.exit(1)

    # 1. Load persisted state
    state = load_state()
    logger.info("Loaded state with %d existing record(s)", len(state.records))

    # 2. Fetch open issues
    issues = fetch_open_issues()
    new_issues = [i for i in issues if not state.has_session(i.number)]
    logger.info("%d new issue(s) to process", len(new_issues))

    # 3. Create Devin sessions for new issues
    for issue in new_issues:
        try:
            record = create_session(issue)
            state.add_record(record)
            save_state(state)
            notify_session_created(record)
        except Exception:
            logger.exception("Failed to create session for issue #%d", issue.number)

    # 4. Check status of existing sessions
    for number, record in list(state.records.items()):
        if record.status in ("finished", "errored"):
            continue
        try:
            status_data = get_session_status(record.session_id)
            new_status = status_data.get("status_enum", record.status)
            pr_url = ""

            # Try to extract PR URL from structured output if available
            structured = status_data.get("structured_outputs")
            if isinstance(structured, dict):
                pr_url = structured.get("pr_url", "")

            if new_status != record.status or pr_url:
                state.update_status(number, new_status, pr_url)
                save_state(state)
                notify_session_update(state.records[number])
        except Exception:
            logger.exception("Failed to poll session for issue #%d", number)

    # 5. Generate and log summary report
    report = generate_summary_report(state)
    logger.info("\n%s", report)


def run_loop() -> None:
    """Run the scanner in a loop with a configurable interval."""
    logger.info(
        "Starting automation loop — interval %ds, target %s",
        Config.SCAN_INTERVAL_SECONDS,
        Config.TARGET_REPO,
    )
    while True:
        try:
            run_once()
        except Exception:
            logger.exception("Unhandled error in scan cycle")
        logger.info("Sleeping %ds until next scan …", Config.SCAN_INTERVAL_SECONDS)
        time.sleep(Config.SCAN_INTERVAL_SECONDS)


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "loop"
    if mode == "once":
        run_once()
    else:
        run_loop()
