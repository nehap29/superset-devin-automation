"""Persistent state tracking for processed issues."""

import json
import logging
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone

from src.config import Config

logger = logging.getLogger(__name__)


@dataclass
class SessionRecord:
    """Tracks a Devin session created for a specific issue."""

    issue_number: int
    session_id: str
    session_url: str
    created_at: str
    status: str = "created"  # created | running | finished | errored
    pr_url: str = ""


@dataclass
class State:
    """Maps issue numbers to their session records."""

    records: dict[int, SessionRecord] = field(default_factory=dict)

    def has_session(self, issue_number: int) -> bool:
        return issue_number in self.records

    def add_record(self, record: SessionRecord) -> None:
        self.records[record.issue_number] = record

    def update_status(self, issue_number: int, status: str, pr_url: str = "") -> None:
        if issue_number in self.records:
            self.records[issue_number].status = status
            if pr_url:
                self.records[issue_number].pr_url = pr_url


def _ensure_dir(path: str) -> None:
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)


def load_state() -> State:
    """Load persisted state from disk."""
    path = Config.STATE_FILE
    if not os.path.exists(path):
        logger.info("No existing state file at %s — starting fresh", path)
        return State()

    with open(path, "r") as fh:
        raw = json.load(fh)

    records: dict[int, SessionRecord] = {}
    for key, val in raw.get("records", {}).items():
        records[int(key)] = SessionRecord(**val)
    return State(records=records)


def save_state(state: State) -> None:
    """Persist state to disk."""
    path = Config.STATE_FILE
    _ensure_dir(path)
    payload = {
        "records": {str(k): asdict(v) for k, v in state.records.items()},
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }
    with open(path, "w") as fh:
        json.dump(payload, fh, indent=2)
    logger.info("State saved to %s", path)
