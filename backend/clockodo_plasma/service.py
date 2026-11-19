# SPDX-License-Identifier: MPL-2.0
"""Orchestration: synchronisation, start/stop/switch and the published state.

Booking safety rules (docs/en/architecture.md, "Booking safety") are enforced here:

1. Write calls are never retried automatically.
2. Before a start the clock is read fresh; a running clock is never replaced
   silently.
3. Stop always uses the entry id the user saw.
4. If the outcome of a write is unknown, the state is re-read before the
   buttons are released.
5. Only one action at a time.
6. The state changes only after Clockodo answered.
7. Network errors never cause bookings.
8. Only active customers/projects/services that the daemon loaded itself are
   accepted.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import time as _time
from collections.abc import Awaitable, Callable, Sequence
from datetime import UTC, date, datetime, timedelta, tzinfo
from typing import Any, Protocol
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from . import api
from .api import ClockEntry, ClockStatus, Context, Interval, NamedItem, User
from .clock import ServerClock
from .config import ConfigStore, RecentContexts, Settings
from .messages import LANGUAGES, SYSTEM, resolve_language, set_language, t
from .secret_store import Credentials, SecretLocked, SecretStore, SecretUnavailable
from .state import RunningInfo, State, Status
from .time_calculator import day_bounds, work_seconds

log = logging.getLogger(__name__)

CONTEXT_MAX_AGE = 600.0  # seconds before customers/projects/services are reloaded
MAX_BACKOFF = 900.0
RESUME_NOTICE_SECONDS = 120.0
TARGET_RETRY_SECONDS = 900.0  # retry interval after the daily target could not be read

ActionCallback = Callable[[str], Awaitable[None]]


class Notifier(Protocol):
    async def notify(
        self,
        summary: str,
        body: str = "",
        actions: Sequence[tuple[str, str]] = (),
        on_action: ActionCallback | None = None,
    ) -> None: ...


class NullNotifier:
    async def notify(
        self,
        summary: str,
        body: str = "",
        actions: Sequence[tuple[str, str]] = (),
        on_action: ActionCallback | None = None,
    ) -> None:
        log.info("notification: %s", summary)


def format_hm(seconds: int) -> str:
    minutes = max(0, int(seconds)) // 60
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


ClientFactory = Callable[[str, str, str | None], Any]


def default_client_factory(email: str, api_key: str, contact: str | None) -> api.ClockodoClient:
    return api.ClockodoClient(email, api_key, contact)


def local_timezone() -> tzinfo:
    tz = datetime.now().astimezone().tzinfo
    return tz if tz is not None else UTC


class Service:
    def __init__(
        self,
        store: ConfigStore,
        secrets: SecretStore,
        *,
        client_factory: ClientFactory = default_client_factory,
        clock: ServerClock | None = None,
        notifier: Notifier | None = None,
        local_tz: Callable[[], tzinfo] = local_timezone,
        monotonic: Callable[[], float] = _time.monotonic,
    ) -> None:
        self.store = store
        self.secrets = secrets
        self.client_factory = client_factory
        self.clock = clock or ServerClock()
        self.notifier: Notifier = notifier or NullNotifier()
        self.local_tz = local_tz
        self.monotonic = monotonic

        self.settings = Settings()
        self.recent = RecentContexts()
        self.state = State()
        self.client: Any = None
        self.credentials: Credentials | None = None
        self.user: User | None = None
        self.user_tz: tzinfo | None = None

        self.customers: dict[int, NamedItem] = {}
        self.projects: dict[int, NamedItem] = {}
        self.services: dict[int, NamedItem] = {}
        self._contexts_loaded_at: float | None = None

        self._intervals: list[Interval] = []
        self._day: date | None = None
        self._sync_task: asyncio.Task[bool] | None = None
        self._action_lock = asyncio.Lock()
        self._failures = 0
        self._retry_after: float | None = None
        self._long_notified_entry: int | None = None
        self._day_requested: date | None = None
        self._target_day: date | None = None
        self._target_retry_at = 0.0
        self._overtime_day: date | None = None
        self._overtime_last: float | None = None

        self._listeners: list[Callable[[State], None]] = []
        self._sync_requests: list[Callable[[], None]] = []

    # ------------------------------------------------------------------ wiring

    def add_listener(self, callback: Callable[[State], None]) -> None:
        self._listeners.append(callback)

    def add_sync_requester(self, callback: Callable[[], None]) -> None:
        """Called when the service wants the poller to sync soon."""
        self._sync_requests.append(callback)

    def publish(self) -> None:
        self._update_choices()
        for callback in self._listeners:
            try:
                callback(self.state)
            except Exception:  # pragma: no cover - listener bugs must not break the daemon
                log.exception("state listener failed")

    def request_sync(self) -> None:
        for callback in self._sync_requests:
            callback()

    # ------------------------------------------------------------------ setup

    async def initialize(self) -> None:
        self.settings = self.store.load_settings()
        self._apply_settings()
        self.recent = RecentContexts(self.store.load_recent_contexts())
        await self.load_credentials()
        self.publish()

    def _apply_settings(self) -> None:
        language = resolve_language(self.settings.language)
        set_language(language)
        self.state.language = language
        self.state.poll_interval = self.settings.poll_interval
        self.state.ui = self.settings.ui()

    async def load_credentials(self) -> bool:
        try:
            credentials = await self.secrets.load()
        except SecretLocked:
            self._set_status(Status.SECRET_LOCKED, t("secret_locked"))
            return False
        except SecretUnavailable:
            self._set_status(Status.SECRET_LOCKED, t("secret_unavailable"))
            return False
        except Exception:  # D-Bus errors of the secret provider
            log.exception("reading credentials failed")
            self._set_status(Status.SECRET_LOCKED, t("secret_unavailable"))
            return False
        if credentials is None:
            self._set_status(Status.UNCONFIGURED, t("not_configured"))
            return False
        await self._use_credentials(credentials)
        return True

    async def _use_credentials(self, credentials: Credentials, user: User | None = None) -> None:
        await self._close_client()
        self.credentials = credentials
        self.client = self.client_factory(
            credentials.email, credentials.api_key, self.settings.contact_email or None
        )
        self.user = user
        self.state.account = credentials.email
        if user is not None:
            self._apply_user(user)
        if self.state.status in (
            Status.UNCONFIGURED,
            Status.SECRET_LOCKED,
            Status.AUTH_FAILED,
        ):
            self.state.status = Status.UNKNOWN
            self.state.error = None

    async def _close_client(self) -> None:
        if self.client is not None:
            with contextlib.suppress(Exception):
                await self.client.aclose()
        self.client = None

    async def shutdown(self) -> None:
        if self._sync_task is not None:
            self._sync_task.cancel()
            with contextlib.suppress(BaseException):
                await self._sync_task
        await self._close_client()

    def _apply_user(self, user: User) -> None:
        self.user = user
        tz: tzinfo | None = None
        if user.timezone:
            try:
                tz = ZoneInfo(user.timezone)
            except (ZoneInfoNotFoundError, ValueError):
                tz = None
        self.user_tz = tz
        self.state.timezone = user.timezone
        self.state.timezone_mismatch = self._timezone_mismatch()

    def _timezone_mismatch(self) -> bool:
        if self.user_tz is None:
            return False
        now = datetime.now(UTC)
        local = now.astimezone(self.local_tz()).utcoffset()
        remote = now.astimezone(self.user_tz).utcoffset()
        return local != remote

    def day_tz(self) -> tzinfo:
        """Time zone that defines "today": the Clockodo time zone of the user."""
        return self.user_tz or self.local_tz()

    def _set_status(self, status: Status, error: str | None = None) -> None:
        previous = self.state.status
        self.state.status = status
        self.state.error = error
        if status in (Status.UNCONFIGURED, Status.SECRET_LOCKED, Status.AUTH_FAILED):
            self.state.running = None
        if status == Status.AUTH_FAILED and previous != Status.AUTH_FAILED:
            self._spawn(self.notifier.notify(t("auth_failed_title"), t("auth_failed")))

    def _spawn(self, coro: Any) -> None:
        task = asyncio.get_running_loop().create_task(coro)
        task.add_done_callback(lambda tsk: tsk.exception() if not tsk.cancelled() else None)

    # ------------------------------------------------------------------ polling support

    def next_delay(self) -> float | None:
        """Seconds until the next scheduled sync, or None if polling is off."""
        if self.client is None or self.state.status == Status.AUTH_FAILED:
            return None
        interval = float(self.settings.poll_interval)
        if interval <= 0:
            return None
        if self._failures == 0:
            return interval
        delay = min(interval * (2 ** min(self._failures, 6)), MAX_BACKOFF)
        if self._retry_after is not None:
            delay = max(delay, self._retry_after)
        return delay

    def tick(self) -> None:
        """Called every second by the poller: jump and day-change detection."""
        jump = self.clock.check_jump()
        if jump:
            log.info("wall clock jumped by %.0f s (suspend or clock change)", jump)
            if (
                jump >= RESUME_NOTICE_SECONDS
                and self.state.status == Status.RUNNING
                and self.state.running is not None
            ):
                self._spawn(
                    self.notifier.notify(
                        t("reminder_resume_title"),
                        t(
                            "reminder_resume_body",
                            minutes=int(jump // 60),
                            label=self.state.running.label,
                        ),
                    )
                )
            self.request_sync()
            return
        today = self._today()
        if self._day is not None and today != self._day and self._day_requested != today:
            self._day_requested = today  # request once per day change, not every second
            self.request_sync()
            return
        self._check_long_running()
        self._check_overtime()

    def minute_update(self) -> None:
        """Recompute the daily total with the local clock and publish it."""
        if self._day is None or self.state.status not in (Status.RUNNING, Status.STOPPED):
            return
        self._recompute()
        self.publish()

    def _today(self) -> date:
        return self.clock.now().astimezone(self.day_tz()).date()

    def _check_long_running(self) -> None:
        hours = self.settings.long_running_hours
        running = self.state.running
        if not hours or running is None or self.state.status != Status.RUNNING:
            return
        if self._long_notified_entry == running.entry_id:
            return
        if self.clock.now() - running.time_since >= timedelta(hours=hours):
            self._long_notified_entry = running.entry_id
            self._spawn(
                self.notifier.notify(
                    t("reminder_long_title", hours=hours),
                    t("reminder_lock_body", label=running.label, since=self._fmt(running)),
                )
            )

    def _check_overtime(self) -> None:
        """Warn when today's work time exceeds the daily target while the clock runs."""
        settings = self.settings
        target = self.state.target_seconds
        running = self.state.running
        if (
            not settings.overtime_notify
            or not target
            or running is None
            or self.state.status != Status.RUNNING
            or self._day is None
        ):
            return
        total = self.state.today_seconds
        if total - target < settings.overtime_after_minutes * 60:
            return
        now = self.monotonic()
        if self._overtime_day == self._day:
            repeat = settings.overtime_repeat_minutes * 60
            if not repeat or self._overtime_last is None or now - self._overtime_last < repeat:
                return
        self._overtime_day = self._day
        self._overtime_last = now
        entry_id = running.entry_id

        async def on_action(key: str) -> None:
            if key != "stop":
                return
            result = await self.stop(entry_id)
            if not result["ok"]:
                await self.notifier.notify(t("quick_failed_title"), result["message"])

        self._spawn(
            self.notifier.notify(
                t("overtime_title"),
                t(
                    "overtime_body",
                    total=format_hm(total),
                    target=format_hm(target),
                    label=running.label,
                ),
                actions=[("stop", t("action_stop")), ("continue", t("action_continue"))],
                on_action=on_action,
            )
        )

    def _fmt(self, running: RunningInfo) -> str:
        return running.time_since.astimezone(self.local_tz()).strftime("%H:%M")

    async def on_screen_locked(self) -> None:
        running = self.state.running
        if not self.settings.notify_on_lock or running is None:
            return
        if self.state.status != Status.RUNNING:
            return
        await self.notifier.notify(
            t("reminder_lock_title"),
            t("reminder_lock_body", label=running.label, since=self._fmt(running)),
        )

    # ------------------------------------------------------------------ synchronisation

    async def sync(self) -> bool:
        """Synchronise with Clockodo; concurrent callers share one request."""
        if self._sync_task is None or self._sync_task.done():
            self._sync_task = asyncio.get_running_loop().create_task(self._do_sync())
        return await asyncio.shield(self._sync_task)

    async def _do_sync(self) -> bool:
        if self.client is None:
            if self.state.status not in (Status.SECRET_LOCKED, Status.UNKNOWN):
                return False
            if not await self.load_credentials():
                self.publish()
                return False

        self.state.syncing = True
        self.publish()
        try:
            if self.user is None:
                self._apply_user(await self.client.get_me())
            status = await self.client.get_clock()
            self.clock.sync(status.current_time)
            day = self._today()
            assert self.user is not None
            intervals = await self.client.get_work_intervals(day, self.user.id)
            if not self.customers:
                # Names for the default booking and the recent contexts.
                await self._ensure_contexts_quietly()
            await self._apply_clock(status, external=True)
            self._intervals = intervals
            self._day = day
            await self._load_target(day)
            self._recompute()
            self.state.last_sync = datetime.now(UTC)
            self.state.stale = False
            self.state.error = None
            self._failures = 0
            self._retry_after = None
            return True
        except api.AuthError:
            self._set_status(Status.AUTH_FAILED, t("auth_failed"))
            return False
        except api.RateLimitError as exc:
            self._sync_failed(t("rate_limited"), exc.retry_after)
            return False
        except api.NetworkError:
            self._sync_failed(t("network"))
            return False
        except api.ApiError as exc:
            self._sync_failed(t("server_error", detail=exc.message))
            return False
        except (ValueError, KeyError, TypeError) as exc:
            log.warning("unexpected response from Clockodo: %s", type(exc).__name__)
            self._sync_failed(t("server_error", detail=type(exc).__name__))
            return False
        finally:
            self.state.syncing = False
            self.publish()

    async def _load_target(self, day: date) -> None:
        """Read the daily target once per day; it is optional and never fails a sync."""
        if self._target_day == day or self.user is None:
            return
        if self._target_day is not None:
            self.state.target_seconds = None  # yesterday's target no longer applies
        if self.monotonic() < self._target_retry_at:
            return
        try:
            target = await self.client.get_day_target(self.user.id, day)
        except api.AuthError:
            raise
        except api.ForbiddenError:
            log.info("no permission to read the daily target")
            self._target_day = day  # try again tomorrow
            self.state.target_seconds = None
            return
        except (api.ApiError, api.NetworkError, ValueError, KeyError, TypeError) as exc:
            log.info("reading the daily target failed: %s", type(exc).__name__)
            self._target_retry_at = self.monotonic() + TARGET_RETRY_SECONDS
            return
        self._target_day = day
        self._target_retry_at = 0.0
        self.state.target_seconds = target or None

    def _sync_failed(self, message: str, retry_after: float | None = None) -> None:
        self._failures += 1
        self._retry_after = retry_after
        self.state.stale = True
        self.state.error = message

    async def _apply_clock(self, status: ClockStatus, *, external: bool) -> None:
        """Take over the clock state from Clockodo."""
        previous_status = self.state.status
        previous = self.state.running
        entry = status.running
        if entry is None:
            self.state.running = None
            self.state.status = Status.STOPPED
            if external and previous is not None and previous_status == Status.RUNNING:
                self.state.set_notice(t("external_stopped"))
            return
        if previous is None or previous.entry_id != entry.id or self.customers == {}:
            await self._ensure_contexts_quietly()
        self.state.running = self._running_info(entry)
        self.state.status = Status.RUNNING
        if (
            external
            and previous_status in (Status.RUNNING, Status.STOPPED)
            and (previous is None or previous.entry_id != entry.id)
        ):
            self.state.set_notice(t("external_started", label=self.state.running.label))
        if self.recent.remember(entry.context):
            self._save_recent()

    def _running_info(self, entry: ClockEntry) -> RunningInfo:
        return RunningInfo(
            entry_id=entry.id,
            customers_id=entry.customers_id,
            projects_id=entry.projects_id,
            subprojects_id=entry.subprojects_id,
            services_id=entry.services_id,
            text=entry.text,
            time_since=entry.time_since,
            label=self.label(entry.context),
        )

    def _recompute(self) -> None:
        if self._day is None:
            return
        now = self.clock.now()
        bounds = day_bounds(self._day, self.day_tz())
        running_since = self.state.running.time_since if self.state.running else None
        self.state.today_seconds = work_seconds(self._intervals, bounds, now, running_since)
        self.state.computed_at = now

    def _save_recent(self) -> None:
        try:
            self.store.save_recent_contexts(self.recent.items)
        except OSError as exc:
            log.warning("cannot save recent contexts: %s", exc)

    # ------------------------------------------------------------------ booking contexts

    async def ensure_contexts(self, max_age: float = CONTEXT_MAX_AGE) -> None:
        if self.client is None:
            raise RuntimeError("no client")
        loaded = self._contexts_loaded_at
        if loaded is not None and self.monotonic() - loaded < max_age:
            return
        customers, projects, services = await asyncio.gather(
            self.client.list_customers(),
            self.client.list_projects(),
            self.client.list_services(),
        )
        self.customers = {c.id: c for c in customers}
        self.projects = {p.id: p for p in projects}
        self.services = {s.id: s for s in services}
        self._contexts_loaded_at = self.monotonic()

    async def _ensure_contexts_quietly(self) -> None:
        try:
            await self.ensure_contexts()
        except Exception as exc:  # names are cosmetic; never fail a sync because of them
            log.info("loading booking contexts failed: %s", type(exc).__name__)

    def _update_choices(self) -> None:
        """Default booking and recent contexts with names, for menu and popup."""
        loaded = bool(self.customers)
        default = self.settings.default_context()
        if default is None:
            self.state.quick = None
        else:
            valid = loaded and self.validate_context(default) is None
            self.state.quick = {
                **default.to_dict(),
                "label": self.label(default) if loaded else None,
                "valid": valid,
            }
        self.state.recent = (
            [
                {**c.to_dict(), "label": self.label(c)}
                for c in self.recent.items
                if self.validate_context(c) is None
            ]
            if loaded
            else []
        )

    def label(self, context: Context) -> str:
        parts = [self._name(self.customers, context.customers_id)]
        if context.projects_id:
            parts.append(self._name(self.projects, context.projects_id))
        parts.append(self._name(self.services, context.services_id))
        return " › ".join(parts)

    @staticmethod
    def _name(items: dict[int, NamedItem], item_id: int) -> str:
        item = items.get(item_id)
        return item.name if item else f"#{item_id}"

    def validate_context(self, context: Context) -> str | None:
        """Return a problem description or None if the context is usable."""
        if context.customers_id not in self.customers:
            return f"customer #{context.customers_id}"
        if context.services_id not in self.services:
            return f"service #{context.services_id}"
        if context.projects_id:
            project = self.projects.get(context.projects_id)
            if project is None or project.parent_id != context.customers_id:
                return f"project #{context.projects_id}"
        if context.subprojects_id:
            return "subprojects are not supported yet"
        return None

    async def list_contexts(self) -> dict[str, Any]:
        if self.client is None:
            return {"ok": False, "message": t("not_ready")}
        try:
            await self.ensure_contexts()
        except api.AuthError:
            self._set_status(Status.AUTH_FAILED, t("auth_failed"))
            self.publish()
            return {"ok": False, "message": t("auth_failed")}
        except api.NetworkError:
            return {"ok": False, "message": t("network")}
        except api.ApiError as exc:
            return {"ok": False, "message": t("server_error", detail=exc.message)}
        recent = []
        for context in self.recent.items:
            if self.validate_context(context) is None:
                recent.append({**context.to_dict(), "label": self.label(context)})
        return {
            "ok": True,
            "customers": sorted(
                ({"id": c.id, "name": c.name} for c in self.customers.values()),
                key=lambda x: x["name"].casefold(),
            ),
            "projects": sorted(
                (
                    {"id": p.id, "name": p.name, "customers_id": p.parent_id}
                    for p in self.projects.values()
                ),
                key=lambda x: x["name"].casefold(),
            ),
            "services": sorted(
                ({"id": s.id, "name": s.name} for s in self.services.values()),
                key=lambda x: x["name"].casefold(),
            ),
            "recent": recent,
        }

    # ------------------------------------------------------------------ actions

    def _result(self, ok: bool, message: str) -> dict[str, Any]:
        return {"ok": ok, "message": message}

    async def _begin_action(self) -> dict[str, Any] | None:
        if self.client is None or self.state.status in (
            Status.UNCONFIGURED,
            Status.SECRET_LOCKED,
            Status.AUTH_FAILED,
        ):
            return self._result(False, t("not_ready"))
        return None

    async def _finish_action(self) -> None:
        # Re-read the server state before releasing the buttons (rule 4).
        await self.sync()
        self.state.action_pending = False
        self.publish()

    async def start(self, context_data: dict[str, Any]) -> dict[str, Any]:
        if self._action_lock.locked():
            return self._result(False, t("busy"))
        async with self._action_lock:
            refused = await self._begin_action()
            if refused:
                return refused
            self.state.action_pending = True
            self.publish()
            try:
                return await self._start(context_data)
            finally:
                await self._finish_action()

    async def _start(self, context_data: dict[str, Any]) -> dict[str, Any]:
        try:
            context = Context.from_dict(context_data)
        except (KeyError, TypeError, ValueError):
            return self._result(False, t("invalid_context", detail="customer/service"))
        try:
            await self.ensure_contexts()
            problem = self.validate_context(context)
            if problem:
                return self._result(False, t("invalid_context", detail=problem))
            fresh = await self.client.get_clock()
            self.clock.sync(fresh.current_time)
            if fresh.running is not None:
                await self._apply_clock(fresh, external=True)
                running = self.state.running
                assert running is not None
                return self._result(
                    False,
                    t("already_running", label=running.label, since=self._fmt(running)),
                )
            result = await self.client.start_clock(context)
        except api.WriteOutcomeUnknown:
            return await self._outcome_unknown()
        except api.NetworkError:
            return self._result(False, t("network_nothing_booked"))
        except api.AuthError:
            self._set_status(Status.AUTH_FAILED, t("auth_failed"))
            return self._result(False, t("auth_failed"))
        except api.ApiError as exc:
            return self._result(False, t("server_error", detail=exc.message))

        self.clock.sync(result.current_time)
        await self._apply_clock(result, external=False)
        if self.recent.remember(context):
            self._save_recent()
        messages = [t("started", label=self.label(context))]
        messages += self._result_notes(result)
        return self._result(True, " ".join(messages))

    def _result_notes(self, result: ClockStatus) -> list[str]:
        notes = []
        if result.stopped is not None:
            notes.append(t("start_stopped_other", label=self.label(result.stopped.context)))
        if result.stopped_has_been_truncated:
            notes.append(t("truncated"))
        if result.additional_message:
            notes.append(t("clockodo_note", detail=result.additional_message))
        return notes

    async def _outcome_unknown(self) -> dict[str, Any]:
        await self.sync()
        running = self.state.running
        if self.state.status == Status.RUNNING and running is not None:
            outcome = t("result_running", label=running.label)
        else:
            outcome = t("result_stopped")
        return self._result(False, t("outcome_unknown", result=outcome))

    async def quick_toggle(self, seen_entry_id: str) -> dict[str, Any]:
        """Stop the entry the widget showed, or start the default booking.

        ``seen_entry_id`` is empty if the widget showed a stopped clock. The
        usual safety rules apply: a clock running elsewhere is never replaced,
        and stop only stops the entry the user saw. Failures are also shown as
        a notification because the popup is usually closed.
        """
        if seen_entry_id:
            result = await self.stop(seen_entry_id)
        else:
            context = self.settings.default_context()
            if context is None:
                return {"ok": False, "message": t("no_default"), "needs_picker": True}
            result = await self.start(context.to_dict())
        if not result["ok"]:
            self._spawn(self.notifier.notify(t("quick_failed_title"), result["message"]))
        return result

    async def stop(self, entry_id: str | int) -> dict[str, Any]:
        if self._action_lock.locked():
            return self._result(False, t("busy"))
        async with self._action_lock:
            refused = await self._begin_action()
            if refused:
                return refused
            self.state.action_pending = True
            self.publish()
            try:
                return await self._stop(int(entry_id))
            finally:
                await self._finish_action()

    async def _stop(self, entry_id: int) -> dict[str, Any]:
        running = self.state.running
        if running is None or running.entry_id != entry_id:
            return self._result(False, t("stale_entry"))
        try:
            result = await self.client.stop_clock(entry_id)
        except api.WriteOutcomeUnknown:
            return await self._outcome_unknown()
        except api.ConflictError:
            return self._result(False, t("stale_entry"))
        except api.NetworkError:
            return self._result(False, t("network_nothing_booked"))
        except api.AuthError:
            self._set_status(Status.AUTH_FAILED, t("auth_failed"))
            return self._result(False, t("auth_failed"))
        except api.ApiError as exc:
            return self._result(False, t("server_error", detail=exc.message))
        self.clock.sync(result.current_time)
        await self._apply_clock(result, external=False)
        messages = [t("stopped")]
        if result.stopped_has_been_truncated:
            messages.append(t("truncated"))
        return self._result(True, " ".join(messages))

    async def switch(self, context_data: dict[str, Any], entry_id: str | int) -> dict[str, Any]:
        """Replace the running entry ``entry_id`` with a new context in one call.

        ``POST /v2/clock`` stops a running clock itself, so a switch needs only
        one write call and leaves no gap. It is only sent after a fresh read
        confirmed that exactly ``entry_id`` is running.
        """
        if self._action_lock.locked():
            return self._result(False, t("busy"))
        async with self._action_lock:
            refused = await self._begin_action()
            if refused:
                return refused
            self.state.action_pending = True
            self.publish()
            try:
                return await self._switch(context_data, int(entry_id))
            finally:
                await self._finish_action()

    async def _switch(self, context_data: dict[str, Any], entry_id: int) -> dict[str, Any]:
        try:
            context = Context.from_dict(context_data)
        except (KeyError, TypeError, ValueError):
            return self._result(False, t("invalid_context", detail="customer/service"))
        try:
            await self.ensure_contexts()
            problem = self.validate_context(context)
            if problem:
                return self._result(False, t("invalid_context", detail=problem))
            fresh = await self.client.get_clock()
            self.clock.sync(fresh.current_time)
            if fresh.running is None:
                await self._apply_clock(fresh, external=True)
                return self._result(False, t("switch_not_running"))
            if fresh.running.id != entry_id:
                await self._apply_clock(fresh, external=True)
                return self._result(False, t("stale_entry"))
            result = await self.client.start_clock(context)
        except api.WriteOutcomeUnknown:
            return await self._outcome_unknown()
        except api.NetworkError:
            return self._result(False, t("network_nothing_booked"))
        except api.AuthError:
            self._set_status(Status.AUTH_FAILED, t("auth_failed"))
            return self._result(False, t("auth_failed"))
        except api.ApiError as exc:
            return self._result(False, t("server_error", detail=exc.message))
        self.clock.sync(result.current_time)
        await self._apply_clock(result, external=False)
        if self.recent.remember(context):
            self._save_recent()
        messages = [t("switched", label=self.label(context))]
        if result.stopped is not None and result.stopped.id != entry_id:
            messages.append(t("start_stopped_other", label=self.label(result.stopped.context)))
        if result.stopped_has_been_truncated:
            messages.append(t("truncated"))
        if result.additional_message:
            messages.append(t("clockodo_note", detail=result.additional_message))
        return self._result(True, " ".join(messages))

    # ------------------------------------------------------------------ credentials & settings

    async def set_credentials(self, email: str, api_key: str) -> dict[str, Any]:
        email = email.strip()
        api_key = api_key.strip()
        if not email or not api_key:
            return self._result(False, t("credentials_incomplete"))
        client = self.client_factory(email, api_key, self.settings.contact_email or None)
        try:
            user = await client.get_me()
        except api.AuthError:
            return self._result(False, t("credentials_wrong"))
        except api.NetworkError:
            return self._result(False, t("network"))
        except api.ApiError as exc:
            return self._result(False, t("server_error", detail=exc.message))
        finally:
            with contextlib.suppress(Exception):
                await client.aclose()
        credentials = Credentials(email, api_key)
        try:
            await self.secrets.store(credentials)
        except SecretLocked:
            return self._result(False, t("secret_locked"))
        except SecretUnavailable:
            return self._result(False, t("secret_unavailable"))
        self._contexts_loaded_at = None
        self._day = None
        self._target_day = None
        self._target_retry_at = 0.0
        self.state.target_seconds = None
        await self._use_credentials(credentials, user)
        self.publish()
        self.request_sync()
        return self._result(True, t("credentials_saved", name=user.name or user.email))

    async def unlock(self) -> dict[str, Any]:
        try:
            unlocked = await self.secrets.unlock()
        except (SecretUnavailable, SecretLocked):
            return self._result(False, t("secret_unavailable"))
        if not unlocked:
            return self._result(False, t("unlock_failed"))
        ok = await self.load_credentials()
        self.publish()
        if ok:
            self.request_sync()
            return self._result(True, "")
        return self._result(False, self.state.error or t("unlock_failed"))

    def get_settings(self) -> dict[str, Any]:
        system = resolve_language(SYSTEM)
        return {
            **self.settings.to_dict(),
            "language_effective": self.state.language,
            "languages": [{"code": SYSTEM, "name": f"{t('language_system')} ({LANGUAGES[system]})"}]
            + [{"code": code, "name": name} for code, name in LANGUAGES.items()],
        }

    async def set_settings(self, changes: dict[str, Any]) -> dict[str, Any]:
        try:
            settings = self.settings.updated(changes)
        except (TypeError, ValueError) as exc:
            return self._result(False, t("settings_invalid", detail=str(exc)))
        contact_changed = settings.contact_email != self.settings.contact_email
        language_changed = settings.language != self.settings.language
        self.settings = settings
        self._apply_settings()
        if language_changed and self.state.error:
            # Texts of the current error were produced in the old language.
            self.state.error = None
        try:
            self.store.save_settings(settings)
        except OSError as exc:
            return self._result(False, t("settings_invalid", detail=str(exc)))
        if contact_changed and self.credentials is not None:
            await self._use_credentials(self.credentials, self.user)
        self.publish()
        self.request_sync()
        return self._result(True, t("settings_saved"))
