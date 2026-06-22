"""Lightweight analytics for answering "is this system working?"

Tracks per-cycle and cumulative metrics, persisted to a JSON file so they
survive container restarts.  Every scan cycle records:

  - Timing (cycle duration, scan duration)
  - Throughput (issues scanned, sessions created)
  - Outcomes (successes, failures, status transitions)

The `MetricsSummary` provides a snapshot that can be logged, rendered into a
dashboard, or exposed via an API.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from src.config import Config

logger = logging.getLogger(__name__)

METRICS_FILE = os.environ.get("METRICS_FILE", "/data/metrics.json")


# ── Per-cycle snapshot ───────────────────────────────────────────────


@dataclass
class CycleMetrics:
    """Metrics captured during a single scan cycle."""

    started_at: str = ""
    finished_at: str = ""
    duration_seconds: float = 0.0
    issues_scanned: int = 0
    new_issues_found: int = 0
    sessions_created: int = 0
    sessions_failed: int = 0
    sessions_polled: int = 0
    status_changes_detected: int = 0
    comments_posted: int = 0
    errors: list[str] = field(default_factory=list)


# ── Cumulative / historical metrics ─────────────────────────────────


@dataclass
class MetricsSummary:
    """Cumulative metrics across all cycles."""

    total_cycles: int = 0
    total_issues_scanned: int = 0
    total_sessions_created: int = 0
    total_sessions_failed: int = 0
    total_status_changes: int = 0
    total_comments_posted: int = 0
    total_errors: int = 0

    # Outcome counters (by final session status)
    sessions_finished: int = 0
    sessions_errored: int = 0
    sessions_running: int = 0

    # Timing
    last_cycle_at: str = ""
    last_cycle_duration_seconds: float = 0.0
    avg_cycle_duration_seconds: float = 0.0
    _total_duration: float = 0.0

    # Recent cycle history (last N cycles for trend visibility)
    recent_cycles: list[dict[str, Any]] = field(default_factory=list)

    def record_cycle(self, cycle: CycleMetrics) -> None:
        """Fold a completed cycle into the cumulative summary."""
        self.total_cycles += 1
        self.total_issues_scanned += cycle.issues_scanned
        self.total_sessions_created += cycle.sessions_created
        self.total_sessions_failed += cycle.sessions_failed
        self.total_status_changes += cycle.status_changes_detected
        self.total_comments_posted += cycle.comments_posted
        self.total_errors += len(cycle.errors)

        self.last_cycle_at = cycle.finished_at
        self.last_cycle_duration_seconds = cycle.duration_seconds
        self._total_duration += cycle.duration_seconds
        if self.total_cycles > 0:
            self.avg_cycle_duration_seconds = round(
                self._total_duration / self.total_cycles, 2
            )

        snapshot = {
            "cycle": self.total_cycles,
            "at": cycle.finished_at,
            "duration_s": round(cycle.duration_seconds, 2),
            "scanned": cycle.issues_scanned,
            "created": cycle.sessions_created,
            "done": cycle.status_changes_detected,
            "failed": cycle.sessions_failed,
            "errors": len(cycle.errors),
        }
        self.recent_cycles.append(snapshot)
        # Keep only the last 50 cycles
        self.recent_cycles = self.recent_cycles[-50:]

    def success_rate(self) -> float:
        """Percentage of session-creation attempts that succeeded."""
        total = self.total_sessions_created + self.total_sessions_failed
        if total == 0:
            return 100.0
        return round((self.total_sessions_created / total) * 100, 1)


# ── Persistence ──────────────────────────────────────────────────────


def load_metrics() -> MetricsSummary:
    """Load persisted metrics from disk."""
    if not os.path.exists(METRICS_FILE):
        return MetricsSummary()
    try:
        with open(METRICS_FILE, "r") as fh:
            raw = json.load(fh)
        summary = MetricsSummary()
        for key, value in raw.items():
            if hasattr(summary, key):
                setattr(summary, key, value)
        return summary
    except (json.JSONDecodeError, OSError):
        logger.warning("Corrupted metrics file — resetting", exc_info=True)
        return MetricsSummary()


def save_metrics(summary: MetricsSummary) -> None:
    """Persist metrics to disk."""
    directory = os.path.dirname(METRICS_FILE)
    if directory:
        os.makedirs(directory, exist_ok=True)
    data = asdict(summary)
    data["_saved_at"] = datetime.now(timezone.utc).isoformat()
    tmp = METRICS_FILE + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(data, fh, indent=2)
    os.replace(tmp, METRICS_FILE)
    logger.debug("Metrics saved to %s", METRICS_FILE)


# ── Cycle context manager ───────────────────────────────────────────


class CycleTracker:
    """Context manager that times a scan cycle and records its metrics.

    Usage::

        with CycleTracker() as cycle:
            cycle.issues_scanned = 5
            cycle.sessions_created = 2
            ...
        # On exit, the cycle is folded into the cumulative summary and saved.
    """

    def __init__(self) -> None:
        self.cycle = CycleMetrics()
        self._start: float = 0.0

    def __enter__(self) -> CycleMetrics:
        self._start = time.monotonic()
        self.cycle.started_at = datetime.now(timezone.utc).isoformat()
        return self.cycle

    def __exit__(self, exc_type: type | None, exc_val: BaseException | None, exc_tb: Any) -> None:
        elapsed = time.monotonic() - self._start
        self.cycle.duration_seconds = round(elapsed, 2)
        self.cycle.finished_at = datetime.now(timezone.utc).isoformat()

        if exc_val is not None:
            self.cycle.errors.append(f"Unhandled: {exc_type.__name__}: {exc_val}" if exc_type else str(exc_val))

        summary = load_metrics()
        summary.record_cycle(self.cycle)
        save_metrics(summary)

        logger.info(
            "Cycle #%d complete — %d scanned, %d created, %d failed, %.1fs",
            summary.total_cycles,
            self.cycle.issues_scanned,
            self.cycle.sessions_created,
            self.cycle.sessions_failed,
            self.cycle.duration_seconds,
        )
