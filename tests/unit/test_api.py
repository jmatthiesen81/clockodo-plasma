# SPDX-License-Identifier: MPL-2.0
"""API client against mocked responses shaped after the OpenAPI specification."""

from __future__ import annotations

from datetime import UTC, date, datetime

import httpx
import pytest
import respx

from clockodo_plasma import api
from clockodo_plasma.api import ClockodoClient, Context

BASE = "https://my.clockodo.com/api"

RUNNING = {
    "id": 4711,
    "customers_id": 1,
    "projects_id": 5,
    "subprojects_id": None,
    "users_id": 7,
    "texts_id": None,
    "text": None,
    "time_since": "2026-11-19T08:00:00Z",
    "time_until": None,
    "duration": None,
    "time_insert": "2026-11-19T08:00:00Z",
    "time_last_change": "2026-11-19T08:00:00Z",
    "test_data": False,
    "type": 1,
    "services_id": 10,
    "billable": 1,
    "clocked": True,
    "clocked_offline": False,
    "time_clocked_since": "2026-11-19T08:00:00Z",
    "time_last_change_work_time": "2026-11-19T08:00:00Z",
}


@pytest.fixture
def client():
    return ClockodoClient("user@example.org", "secret-key-123", "contact@example.org")


@respx.mock
async def test_headers(client):
    route = respx.get(f"{BASE}/v2/clock").mock(
        return_value=httpx.Response(
            200, json={"running": None, "stopped": None, "current_time": "2026-11-19T09:00:00Z"}
        )
    )
    status = await client.get_clock()
    headers = route.calls.last.request.headers
    assert headers["X-ClockodoApiUser"] == "user@example.org"
    assert headers["X-ClockodoApiKey"] == "secret-key-123"
    assert headers["X-Clockodo-External-Application"] == "clockodo-plasma;contact@example.org"
    assert status.running is None
    assert status.current_time == datetime(2026, 11, 19, 9, tzinfo=UTC)


async def test_contact_defaults_to_user_email():
    client = ClockodoClient("user@example.org", "k")
    with respx.mock:
        route = respx.get(f"{BASE}/v2/clock").mock(
            return_value=httpx.Response(
                200, json={"running": None, "stopped": None, "current_time": "2026-11-19T09:00:00Z"}
            )
        )
        await client.get_clock()
    header = route.calls.last.request.headers["X-Clockodo-External-Application"]
    assert header == "clockodo-plasma;user@example.org"


@respx.mock
async def test_running_clock(client):
    respx.get(f"{BASE}/v2/clock").mock(
        return_value=httpx.Response(
            200, json={"running": RUNNING, "stopped": None, "current_time": "2026-11-19T09:00:00Z"}
        )
    )
    status = await client.get_clock()
    assert status.running.id == 4711
    assert status.running.time_since == datetime(2026, 11, 19, 8, tzinfo=UTC)


@respx.mock
async def test_start_body_and_stopped_entry(client):
    stopped = {**RUNNING, "id": 4710, "time_until": "2026-11-19T09:00:00Z", "duration": 3600}
    route = respx.post(f"{BASE}/v2/clock").mock(
        return_value=httpx.Response(
            200,
            json={
                "running": {**RUNNING, "id": 4712},
                "stopped": stopped,
                "current_time": "2026-11-19T09:00:00Z",
                "stopped_has_been_truncated": False,
                "additional_message": "Billability set to default",
            },
        )
    )
    result = await client.start_clock(Context(customers_id=1, services_id=10, projects_id=5))
    body = route.calls.last.request.content
    assert b'"customers_id":1' in body.replace(b" ", b"")
    assert b"subprojects_id" not in body
    assert result.running.id == 4712
    assert result.stopped.id == 4710
    assert result.additional_message == "Billability set to default"


@respx.mock
async def test_stop_uses_entry_id(client):
    route = respx.delete(f"{BASE}/v2/clock/4711").mock(
        return_value=httpx.Response(
            200,
            json={
                "running": None,
                "stopped": {**RUNNING, "time_until": "2026-11-19T09:00:00Z", "duration": 3600},
                "current_time": "2026-11-19T09:00:00Z",
                "stopped_has_been_truncated": False,
            },
        )
    )
    result = await client.stop_clock(4711)
    assert route.called
    assert result.running is None


@pytest.mark.parametrize(
    ("status", "error"),
    [
        (401, api.AuthError),
        (403, api.ForbiddenError),
        (404, api.ConflictError),
        (409, api.ConflictError),
        (400, api.ApiError),
    ],
)
@respx.mock
async def test_write_error_mapping(client, status, error):
    respx.delete(f"{BASE}/v2/clock/1").mock(
        return_value=httpx.Response(status, json={"errors": [{"message": "nope"}]})
    )
    with pytest.raises(error) as info:
        await client.stop_clock(1)
    assert info.value.message == "nope"


@respx.mock
async def test_server_error_on_write_means_unknown_outcome(client):
    respx.post(f"{BASE}/v2/clock").mock(return_value=httpx.Response(502))
    with pytest.raises(api.WriteOutcomeUnknown):
        await client.start_clock(Context(1, 10))


@respx.mock
async def test_timeout_on_write_means_unknown_outcome(client):
    respx.post(f"{BASE}/v2/clock").mock(side_effect=httpx.ReadTimeout("timeout"))
    with pytest.raises(api.WriteOutcomeUnknown):
        await client.start_clock(Context(1, 10))


@respx.mock
async def test_connect_error_on_write_is_safe(client):
    respx.post(f"{BASE}/v2/clock").mock(side_effect=httpx.ConnectError("refused"))
    with pytest.raises(api.NetworkError):
        await client.start_clock(Context(1, 10))


@respx.mock
async def test_rate_limit_retry_after(client):
    respx.get(f"{BASE}/v2/clock").mock(
        return_value=httpx.Response(429, headers={"Retry-After": "120"}, json={"errors": []})
    )
    with pytest.raises(api.RateLimitError) as info:
        await client.get_clock()
    assert info.value.retry_after == 120


@respx.mock
async def test_errors_never_contain_the_key(client):
    respx.get(f"{BASE}/v2/clock").mock(side_effect=httpx.ConnectError("refused"))
    with pytest.raises(api.NetworkError) as info:
        await client.get_clock()
    assert "secret-key-123" not in repr(info.value)
    assert info.value.__cause__ is None


@respx.mock
async def test_work_intervals(client):
    route = respx.get(f"{BASE}/v2/workTimes").mock(
        return_value=httpx.Response(
            200,
            json={
                "paging": {
                    "items_per_page": 1000,
                    "current_page": 1,
                    "count_pages": 1,
                    "count_items": 1,
                },
                "work_time_days": [
                    {
                        "date": "2026-11-19",
                        "users_id": 7,
                        "offset": 0,
                        "intervals": [
                            {
                                "time_since": "2026-11-19T07:00:00Z",
                                "time_until": "2026-11-19T08:00:00Z",
                            },
                            {"time_since": "2026-11-19T08:30:00Z", "time_until": None},
                        ],
                    }
                ],
            },
        )
    )
    intervals = await client.get_work_intervals(date(2026, 11, 19), 7)
    params = route.calls.last.request.url.params
    assert params["date_since"] == "2026-11-19"
    assert params["users_id"] == "7"
    assert len(intervals) == 2
    assert intervals[1].time_until is None


@respx.mock
async def test_pagination_and_active_filter(client):
    def page(request: httpx.Request) -> httpx.Response:
        assert request.url.params["filter[active]"] == "true"
        number = int(request.url.params["page"])
        return httpx.Response(
            200,
            json={
                "paging": {
                    "items_per_page": 1,
                    "current_page": number,
                    "count_pages": 2,
                    "count_items": 2,
                },
                "data": [{"id": number, "name": f"Customer {number}"}],
            },
        )

    respx.get(f"{BASE}/v3/customers").mock(side_effect=page)
    customers = await client.list_customers()
    assert [c.id for c in customers] == [1, 2]


@respx.mock
async def test_me(client):
    respx.get(f"{BASE}/v4/users/me").mock(
        return_value=httpx.Response(
            200,
            json={
                "data": {
                    "id": 7,
                    "name": "Jane",
                    "email": "user@example.org",
                    "timezone": "Europe/Berlin",
                }
            },
        )
    )
    me = await client.get_me()
    assert me.id == 7
    assert me.timezone == "Europe/Berlin"
