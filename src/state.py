"""Persistent state tracking for processed issues.

State is persisted as a JSON file with atomic writes (write-to-temp then
``os.replace``) to prevent corruption on crashes.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone

from src.config import Config
from src.models import SessionRecord

logger = logging.getLogger(__name__)


@dataclass
class State:
    """Maps issue numbers to their ``SessionRecord``s."""

    records: dict[int, SessionRecord] = field(default_factory=dict)

    def has_session(self, issue_number: int) -> bool:
        return issue_number in self.records

    def add_record(self, record: SessionRecord) -> None:
        self.records[record.issue_number] = record

    def update_status(
        self, issue_number: int, status: str, pr_url: str = ""
    ) -> None:
        if issue_number not in self.records:
            return
        self.records[issue_number].status = status
        if pr_url:
            self.records[issue_number].pr_url = pr_url

    # ── Convenience queries for reporting ────────────────────────────

    def count_by_status(self) -> dict[str, int]:
        """Return ``{status: count}`` across all records."""
        counts: dict[str, int] = {}
        for rec in self.records.values():
            counts[rec.status] = counts.get(rec.status, 0) + 1
        return counts


# ── Persistence ──────────────────────────────────────────────────────


def _ensure_dir(path: str) -> None:
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)


def load_state() -> State:
    """Load persisted state from disk."""
    path = Config.STATE_FILE
    if not os.path.exists(path):
        logger.info("No state file at %s — starting fresh", path)
        return State()

    try:
        with open(path, "r") as fh:
            raw = json.load(fh)
    except (json.JSONDecodeError, OSError):
        logger.warning("Corrupted state file — starting fresh", exc_info=True)
        return State()

    records: dict[int, SessionRecord] = {}
    for key, val in raw.get("records", {}).items():
        records[int(key)] = SessionRecord(**val)
    return State(records=records)


def save_state(state: State) -> None:
    """Atomically persist state to disk (write tmp → rename)."""
    path = Config.STATE_FILE
    _ensure_dir(path)

    payload = {
        "records": {str(k): asdict(v) for k, v in state.records.items()},
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }

    tmp = path + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(payload, fh, indent=2)
    os.replace(tmp, path)

    logger.debug("State saved — %d record(s)", len(state.records))
