# SPDX-License-Identifier: MPL-2.0
from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime
from typing import Any

import pytest

from clockodo_plasma import api
from clockodo_plasma.api import ClockEntry, ClockStatus, Context, Interval, NamedItem, User
from clockodo_plasma.clock import ServerClock
from clockodo_plasma.config import ConfigStore
from clockodo_plasma.secret_store import Credentials, SecretLocked
from clockodo_plasma.service import Service

DEFAULT_CREDENTIALS = Credentials("test@example.org", "secret-key-123")
T0 = datetime(2026, 11, 19, 9, 0, tzinfo=UTC)


def entry(entry_id: int, customers_id: int = 1, services_id: int = 10, **kw: Any) -> ClockEntry:
    return ClockEntry(
        id=entry_id,
        customers_id=customers_id,
        projects_id=kw.get("projects_id"),
        subprojects_id=None,
        services_id=services_id,
        text=None,
        time_since=kw.get("time_since", T0),
        time_until=kw.get("time_until"),
    )


class FakeClient:
    """In-memory stand-in for ClockodoClient that records write calls."""

    def __init__(self) -> None:
        self.running: ClockEntry | None = None
        self.now = T0
        self.calls: list[tuple[str, Any]] = []
        self.next_id = 100
        self.start_error: Exception | None = None
        self.stop_error: Exception | None = None
        self.get_error: Exception | None = None
        self.start_delay = 0.0
        self.apply_before_error = False  # lost response: the action happened anyway
        self.intervals: list[Interval] = []
        self.target: int | None = None  # daily target in seconds
        self.target_error: Exception | None = None

    async def aclose(self) -> None:
        pass

    async def get_me(self) -> User:
        return User(1, "Test User", "test@example.org", "UTC")

    async def get_clock(self) -> ClockStatus:
        self.calls.append(("get_clock", None))
        if self.get_error:
            raise self.get_error
        return ClockStatus(self.running, None, self.now)

    async def get_work_intervals(self, day: date, users_id: int) -> list[Interval]:
        intervals = list(self.intervals)
        if self.running:
            intervals.append(Interval(self.running.time_since, None))
        return intervals

    async def get_day_target(self, users_id: int, day: date) -> int | None:
        self.calls.append(("get_day_target", day))
        if self.target_error:
            raise self.target_error
        return self.target

    async def start_clock(self, context: Context) -> ClockStatus:
        self.calls.append(("start", context))
        if self.start_delay:
            await asyncio.sleep(self.start_delay)
        if self.start_error and not self.apply_before_error:
            raise self.start_error
        stopped = self.running
        self.next_id += 1
        self.running = ClockEntry(
            self.next_id,
            context.customers_id,
            context.projects_id,
            None,
            context.services_id,
            None,
            self.now,
            None,
        )
        if self.start_error:
            raise self.start_error
        return ClockStatus(self.running, stopped, self.now)

    async def stop_clock(self, entry_id: int) -> ClockStatus:
        self.calls.append(("stop", entry_id))
        if self.stop_error and not self.apply_before_error:
            raise self.stop_error
        if self.running is None or self.running.id != entry_id:
            raise api.ConflictError(404, "not running")
        stopped = self.running
        self.running = None
        if self.stop_error:
            raise self.stop_error
        return ClockStatus(None, stopped, self.now)

    async def list_customers(self) -> list[NamedItem]:
        return [NamedItem(1, "ACME"), NamedItem(2, "Globex")]

    async def list_projects(self) -> list[NamedItem]:
        return [NamedItem(5, "Shop", 1), NamedItem(6, "Intranet", 2)]

    async def list_services(self) -> list[NamedItem]:
        return [NamedItem(10, "Development"), NamedItem(11, "Meeting")]

    def writes(self) -> list[tuple[str, Any]]:
        return [c for c in self.calls if c[0] in ("start", "stop")]


class FakeSecrets:
    def __init__(self, credentials: Credentials | None = None, locked: bool = False) -> None:
        self.credentials = credentials
        self.locked = locked
        self.unlock_result = True

    async def load(self) -> Credentials | None:
        if self.locked:
            raise SecretLocked("locked")
        return self.credentials

    async def store(self, credentials: Credentials) -> None:
        if self.locked:
            raise SecretLocked("locked")
        self.credentials = credentials

    async def unlock(self) -> bool:
        if self.unlock_result:
            self.locked = False
        return self.unlock_result


class FakeNotifier:
    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []
        self.actions: list[list[tuple[str, str]]] = []
        self.callbacks: list[Any] = []

    async def notify(
        self,
        summary: str,
        body: str = "",
        actions: Any = (),
        on_action: Any = None,
    ) -> None:
        self.sent.append((summary, body))
        self.actions.append(list(actions))
        self.callbacks.append(on_action)


class FakeTime:
    def __init__(self) -> None:
        self.mono = 1000.0
        self.wall = T0.timestamp()

    def advance(self, seconds: float, *, suspended: bool = False) -> None:
        self.wall += seconds
        if not suspended:
            self.mono += seconds


@pytest.fixture
def fake_time() -> FakeTime:
    return FakeTime()


@pytest.fixture
def client() -> FakeClient:
    return FakeClient()


@pytest.fixture
def notifier() -> FakeNotifier:
    return FakeNotifier()


@pytest.fixture
def make_service(tmp_path, client, notifier, fake_time):
    async def factory(
        credentials: Credentials | None = DEFAULT_CREDENTIALS,
        locked: bool = False,
    ) -> Service:
        service = Service(
            ConfigStore(tmp_path / "config", tmp_path / "state"),
            FakeSecrets(credentials, locked),  # type: ignore[arg-type]
            client_factory=lambda email, key, contact: client,
            clock=ServerClock(lambda: fake_time.mono, lambda: fake_time.wall),
            notifier=notifier,
            local_tz=lambda: UTC,
            monotonic=lambda: fake_time.mono,
        )
        await service.initialize()
        return service

    return factory
