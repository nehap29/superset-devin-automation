"""Domain models shared across the application."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Issue:
    """A GitHub issue to be processed."""

    number: int
    title: str
    body: str
    labels: list[str] = field(default_factory=list)
    html_url: str = ""


@dataclass
class SessionRecord:
    """Tracks a Devin session created for a specific issue."""

    issue_number: int
    session_id: str
    session_url: str
    created_at: str
    status: str = "created"
    pr_url: str = ""

    # Devin v1 API status_enum values (not enforced as enum to stay
    # forward-compatible):
    #   working   — Devin is actively working
    #   blocked   — Devin is waiting on user input
    #   finished  — session completed (or blocked+PR, promoted by us)
    #   expired   — session timed out
