# SPDX-License-Identifier: MPL-2.0
"""Central state that is published to the widget.

The widget receives the state as a JSON string (``GetState`` and the
``StateChanged`` signal); JSON keeps the D-Bus marshalling between Python and
QML trivial.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


class Status(StrEnum):
    UNKNOWN = "unknown"  # not synchronised yet
    UNCONFIGURED = "unconfigured"
    SECRET_LOCKED = "secret_locked"
    AUTH_FAILED = "auth_failed"
    RUNNING = "running"
    STOPPED = "stopped"


@dataclass
class RunningInfo:
    entry_id: int
    customers_id: int
    projects_id: int | None
    subprojects_id: int | None
    services_id: int
    text: str | None
    time_since: datetime
    label: str  # "Customer › Project › Service"


@dataclass
class State:
    status: Status = Status.UNKNOWN
    running: RunningInfo | None = None
    today_seconds: int = 0
    computed_at: datetime | None = None  # server time when today_seconds was computed
    last_sync: datetime | None = None  # local wall time of the last successful sync
    syncing: bool = False
    action_pending: bool = False
    stale: bool = False
    error: str | None = None
    notice: str | None = None  # one-time information (e.g. "clock was started elsewhere")
    notice_id: int = 0
    context_missing: bool = False
    timezone: str | None = None
    timezone_mismatch: bool = False
    poll_interval: int = 60
    account: str | None = None
    language: str = "en"  # effective language for the widget
    target_seconds: int | None = None  # daily target from Clockodo, None = unknown
    quick: dict[str, Any] | None = None  # default booking with "label" and "valid"
    recent: list[dict[str, Any]] = field(default_factory=list)  # with "label"
    ui: dict[str, Any] = field(default_factory=dict)  # panel and mouse settings

    def set_notice(self, text: str | None) -> None:
        self.notice = text
        if text:
            self.notice_id += 1

    def to_dict(self) -> dict[str, Any]:
        running = None
        if self.running is not None:
            r = self.running
            running = {
                "entry_id": str(r.entry_id),  # string: avoid int64 precision issues in JS
                "customers_id": r.customers_id,
                "projects_id": r.projects_id,
                "subprojects_id": r.subprojects_id,
                "services_id": r.services_id,
                "text": r.text,
                "time_since": r.time_since.isoformat(),
                "label": r.label,
            }
        return {
            "status": self.status.value,
            "running": running,
            "today_seconds": self.today_seconds,
            "computed_at": self.computed_at.isoformat() if self.computed_at else None,
            "last_sync": self.last_sync.isoformat() if self.last_sync else None,
            "syncing": self.syncing,
            "action_pending": self.action_pending,
            "stale": self.stale,
            "error": self.error,
            "notice": self.notice,
            "notice_id": self.notice_id,
            "context_missing": self.context_missing,
            "timezone": self.timezone,
            "timezone_mismatch": self.timezone_mismatch,
            "poll_interval": self.poll_interval,
            "account": self.account,
            "language": self.language,
            "target_seconds": self.target_seconds,
            "quick": self.quick,
            "recent": self.recent,
            "ui": self.ui,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)
