# SPDX-License-Identifier: MPL-2.0
"""Clockodo REST API client.

Endpoints and fields follow the official OpenAPI specification
(https://docs.clockodo.com/openapi.yaml, version 2026-11-17).

Rules (see docs/en/architecture.md, "Booking safety"):
- Write calls (start/stop) are never retried here or anywhere else.
- A write call whose request may have reached the server but whose response
  was lost raises ``WriteOutcomeUnknown``; the caller must re-read the state.
- Credentials never appear in exceptions or log messages.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

import httpx

from . import APP_ID, __version__

log = logging.getLogger(__name__)

BASE_URL = "https://my.clockodo.com/api"
DEFAULT_TIMEOUT = httpx.Timeout(15.0, connect=10.0)
PAGE_SIZE = 1000
USER_REPORT_DAYS = 3  # UserReportType "Day": month → week → day details


# --------------------------------------------------------------------------- errors


class ApiError(Exception):
    """Clockodo answered with an error status."""

    def __init__(self, status: int, message: str) -> None:
        super().__init__(f"HTTP {status}: {message}")
        self.status = status
        self.message = message


class AuthError(ApiError):
    """401: e-mail/API key wrong or the key was invalidated (password change)."""


class ForbiddenError(ApiError):
    """403: missing rights."""


class ConflictError(ApiError):
    """404/409 on clock actions: the entry no longer runs or the state changed."""


class RateLimitError(ApiError):
    def __init__(self, status: int, message: str, retry_after: float | None) -> None:
        super().__init__(status, message)
        self.retry_after = retry_after


class ServerError(ApiError):
    """5xx."""


class NetworkError(Exception):
    """The request did not reach Clockodo (connection failed). Safe to retry reads."""


class WriteOutcomeUnknown(Exception):
    """A write request may or may not have been executed (timeout after sending)."""


# --------------------------------------------------------------------------- models


def parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    # Python 3.11+ understands the trailing "Z".
    return datetime.fromisoformat(value)


@dataclass(frozen=True)
class Context:
    """Booking context for starting the clock."""

    customers_id: int
    services_id: int
    projects_id: int | None = None
    subprojects_id: int | None = None
    text: str | None = None

    def key(self) -> tuple[int, int | None, int | None, int]:
        return (self.customers_id, self.projects_id, self.subprojects_id, self.services_id)

    def to_body(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "customers_id": self.customers_id,
            "services_id": self.services_id,
        }
        if self.projects_id:
            body["projects_id"] = self.projects_id
        if self.subprojects_id:
            body["subprojects_id"] = self.subprojects_id
        if self.text:
            body["text"] = self.text
        return body

    def to_dict(self) -> dict[str, Any]:
        return {
            "customers_id": self.customers_id,
            "projects_id": self.projects_id,
            "subprojects_id": self.subprojects_id,
            "services_id": self.services_id,
            "text": self.text,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Context:
        def opt_int(name: str) -> int | None:
            value = data.get(name)
            return int(value) if value not in (None, "", 0) else None

        text = data.get("text")
        return cls(
            customers_id=int(data["customers_id"]),
            services_id=int(data["services_id"]),
            projects_id=opt_int("projects_id"),
            subprojects_id=opt_int("subprojects_id"),
            text=str(text) if text else None,
        )


@dataclass(frozen=True)
class ClockEntry:
    id: int
    customers_id: int
    projects_id: int | None
    subprojects_id: int | None
    services_id: int
    text: str | None
    time_since: datetime
    time_until: datetime | None

    @property
    def context(self) -> Context:
        return Context(
            customers_id=self.customers_id,
            services_id=self.services_id,
            projects_id=self.projects_id,
            subprojects_id=self.subprojects_id,
            text=self.text,
        )

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> ClockEntry:
        since = parse_time(data.get("time_since"))
        if since is None:
            raise ValueError("clock entry without time_since")
        return cls(
            id=int(data["id"]),
            customers_id=int(data["customers_id"]),
            projects_id=data.get("projects_id"),
            subprojects_id=data.get("subprojects_id"),
            services_id=int(data["services_id"]),
            text=data.get("text"),
            time_since=since,
            time_until=parse_time(data.get("time_until")),
        )


@dataclass(frozen=True)
class ClockStatus:
    running: ClockEntry | None
    stopped: ClockEntry | None
    current_time: datetime
    stopped_has_been_truncated: bool = False
    additional_message: str | None = None

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> ClockStatus:
        current = parse_time(data.get("current_time"))
        if current is None:
            raise ValueError("clock response without current_time")
        running = data.get("running")
        stopped = data.get("stopped")
        return cls(
            running=ClockEntry.from_api(running) if running else None,
            stopped=ClockEntry.from_api(stopped) if stopped else None,
            current_time=current,
            stopped_has_been_truncated=bool(data.get("stopped_has_been_truncated", False)),
            additional_message=data.get("additional_message") or None,
        )


@dataclass(frozen=True)
class User:
    id: int
    name: str
    email: str
    timezone: str | None


@dataclass(frozen=True)
class Interval:
    time_since: datetime
    time_until: datetime | None


@dataclass(frozen=True)
class NamedItem:
    id: int
    name: str
    parent_id: int | None = None  # customers_id for projects, projects_id for subprojects


# --------------------------------------------------------------------------- client


def _error_message(response: httpx.Response) -> str:
    try:
        data = response.json()
    except ValueError:
        return response.reason_phrase or "error"
    errors = data.get("errors") if isinstance(data, dict) else None
    if isinstance(errors, list) and errors:
        parts = []
        for err in errors:
            if isinstance(err, dict):
                parts.append(str(err.get("message") or err.get("code") or err))
            else:
                parts.append(str(err))
        return "; ".join(parts)
    error = data.get("error") if isinstance(data, dict) else None
    if isinstance(error, dict) and error.get("message"):
        return str(error["message"])
    return response.reason_phrase or "error"


def _retry_after(response: httpx.Response) -> float | None:
    value = response.headers.get("Retry-After")
    if not value:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        return None


class ClockodoClient:
    def __init__(
        self,
        email: str,
        api_key: str,
        contact_email: str | None = None,
        *,
        base_url: str = BASE_URL,
        transport: httpx.AsyncBaseTransport | None = None,
        timeout: httpx.Timeout = DEFAULT_TIMEOUT,
    ) -> None:
        contact = contact_email or email
        headers = {
            "X-ClockodoApiUser": email,
            "X-ClockodoApiKey": api_key,
            "X-Clockodo-External-Application": f"{APP_ID};{contact}",
            "User-Agent": f"{APP_ID}/{__version__}",
            "Accept": "application/json",
        }
        self._client = httpx.AsyncClient(
            base_url=base_url,
            headers=headers,
            timeout=timeout,
            transport=transport,
            follow_redirects=False,
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    # ---------------------------------------------------------------- transport

    def _raise_for_status(self, response: httpx.Response, *, clock_action: bool) -> None:
        status = response.status_code
        if status < 400:
            return
        message = _error_message(response)
        if status == 401:
            raise AuthError(status, message)
        if status == 403:
            raise ForbiddenError(status, message)
        if status == 429:
            raise RateLimitError(status, message, _retry_after(response))
        if clock_action and status in (404, 409):
            raise ConflictError(status, message)
        if status >= 500:
            raise ServerError(status, message)
        raise ApiError(status, message)

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        try:
            response = await self._client.get(path, params=params)
        except httpx.TransportError as exc:
            raise NetworkError(type(exc).__name__) from None
        self._raise_for_status(response, clock_action=False)
        return response.json()

    async def _write(
        self, method: str, path: str, json: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        try:
            response = await self._client.request(method, path, json=json)
        except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
            # The request never left this machine.
            raise NetworkError(type(exc).__name__) from None
        except httpx.TransportError as exc:
            raise WriteOutcomeUnknown(type(exc).__name__) from None
        if response.status_code >= 500:
            # The server may have executed the action before failing.
            raise WriteOutcomeUnknown(f"HTTP {response.status_code}")
        self._raise_for_status(response, clock_action=True)
        return response.json()

    async def _get_all(self, path: str, params: dict[str, Any], key: str) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        page = 1
        while True:
            data = await self._get(path, {**params, "page": page, "items_per_page": PAGE_SIZE})
            items.extend(data.get(key) or [])
            paging = data.get("paging") or {}
            if page >= int(paging.get("count_pages") or 1):
                return items
            page += 1

    # ---------------------------------------------------------------- endpoints

    async def get_me(self) -> User:
        data = (await self._get("/v4/users/me"))["data"]
        return User(
            id=int(data["id"]),
            name=str(data.get("name") or ""),
            email=str(data.get("email") or ""),
            timezone=data.get("timezone") or None,
        )

    async def get_clock(self) -> ClockStatus:
        return ClockStatus.from_api(await self._get("/v2/clock"))

    async def start_clock(self, context: Context) -> ClockStatus:
        return ClockStatus.from_api(await self._write("POST", "/v2/clock", context.to_body()))

    async def stop_clock(self, entry_id: int) -> ClockStatus:
        return ClockStatus.from_api(await self._write("DELETE", f"/v2/clock/{int(entry_id)}"))

    async def get_work_intervals(self, day: date, users_id: int) -> list[Interval]:
        params = {
            "date_since": day.isoformat(),
            "date_until": day.isoformat(),
            "users_id": users_id,
        }
        days = await self._get_all("/v2/workTimes", params, "work_time_days")
        intervals: list[Interval] = []
        for work_day in days:
            if work_day.get("date") != day.isoformat():
                continue
            for item in work_day.get("intervals") or []:
                since = parse_time(item.get("time_since"))
                if since is None:
                    continue
                intervals.append(Interval(since, parse_time(item.get("time_until"))))
        return intervals

    async def get_day_target(self, users_id: int, day: date) -> int | None:
        """Target work time of ``day`` in seconds, or None if Clockodo has none.

        The day report already accounts for public holidays, absences and
        changed target hours. It covers the whole year, so the caller fetches
        it once per day.
        """
        data = await self._get(
            f"/userreports/{int(users_id)}", {"year": day.year, "type": USER_REPORT_DAYS}
        )
        wanted = day.isoformat()
        for month in data["userreport"].get("month_details") or []:
            for week in month.get("week_details") or []:
                for item in week.get("day_details") or []:
                    if item.get("date") == wanted:
                        target = item.get("target")
                        return int(target) if target is not None else None
        return None

    async def list_customers(self) -> list[NamedItem]:
        rows = await self._get_all("/v3/customers", {"filter[active]": "true"}, "data")
        return [NamedItem(int(r["id"]), str(r.get("name") or r["id"])) for r in rows]

    async def list_projects(self) -> list[NamedItem]:
        params = {"filter[active]": "true", "filter[completed]": "false"}
        rows = await self._get_all("/v4/projects", params, "data")
        return [
            NamedItem(int(r["id"]), str(r.get("name") or r["id"]), int(r["customers_id"]))
            for r in rows
        ]

    async def list_services(self) -> list[NamedItem]:
        rows = await self._get_all("/v4/services", {"filter[active]": "true"}, "data")
        return [NamedItem(int(r["id"]), str(r.get("name") or r["id"])) for r in rows]
