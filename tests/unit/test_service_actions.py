# SPDX-License-Identifier: MPL-2.0
"""Booking safety (docs/en/architecture.md, "Booking safety")."""

from __future__ import annotations

import asyncio

from clockodo_plasma import api
from clockodo_plasma.state import Status

from ..conftest import entry

CTX = {"customers_id": 1, "projects_id": 5, "services_id": 10}


async def test_start_and_stop(make_service, client):
    service = await make_service()
    assert await service.sync()
    assert service.state.status == Status.STOPPED

    result = await service.start(CTX)
    assert result["ok"], result
    assert service.state.status == Status.RUNNING
    assert service.state.running.label == "ACME › Shop › Development"
    assert not service.state.action_pending

    result = await service.stop(service.state.running.entry_id)
    assert result["ok"], result
    assert service.state.status == Status.STOPPED
    assert [c[0] for c in client.writes()] == ["start", "stop"]


async def test_double_click_starts_only_once(make_service, client):
    service = await make_service()
    await service.sync()
    client.start_delay = 0.05
    first, second = await asyncio.gather(service.start(CTX), service.start(CTX))
    assert first["ok"] is True
    assert second["ok"] is False
    assert len(client.writes()) == 1


async def test_lost_response_is_not_retried_and_state_is_reloaded(make_service, client):
    service = await make_service()
    await service.sync()
    client.start_error = api.WriteOutcomeUnknown("ReadTimeout")
    client.apply_before_error = True  # the server did start the clock

    result = await service.start(CTX)

    assert result["ok"] is False
    assert "Shop" in result["message"]
    assert len(client.writes()) == 1  # no second start
    assert service.state.status == Status.RUNNING
    assert service.state.running.entry_id == client.running.id
    assert not service.state.action_pending


async def test_lost_response_when_nothing_happened(make_service, client):
    service = await make_service()
    await service.sync()
    client.start_error = api.WriteOutcomeUnknown("ReadTimeout")

    result = await service.start(CTX)

    assert result["ok"] is False
    assert service.state.status == Status.STOPPED
    assert len(client.writes()) == 1


async def test_start_refused_when_clock_runs_elsewhere(make_service, client):
    service = await make_service()
    await service.sync()
    # Started on the phone after our last poll.
    client.running = entry(55, customers_id=2, services_id=11)

    result = await service.start(CTX)

    assert result["ok"] is False
    assert "Globex" in result["message"]
    assert client.writes() == []
    assert service.state.running.entry_id == 55


async def test_stop_with_outdated_entry_id_does_nothing(make_service, client):
    service = await make_service()
    client.running = entry(55)
    await service.sync()
    result = await service.stop(54)
    assert result["ok"] is False
    assert client.writes() == []


async def test_stop_conflict_is_not_retried(make_service, client):
    service = await make_service()
    client.running = entry(55)
    await service.sync()
    # Stopped on another device meanwhile.
    client.running = None

    result = await service.stop(55)

    assert result["ok"] is False
    assert client.writes() == [("stop", 55)]
    assert service.state.status == Status.STOPPED


async def test_network_error_books_nothing(make_service, client):
    service = await make_service()
    await service.sync()
    client.start_error = api.NetworkError("ConnectError")

    result = await service.start(CTX)

    assert result["ok"] is False
    assert client.running is None


async def test_switch_uses_one_write_call(make_service, client):
    service = await make_service()
    client.running = entry(55)
    await service.sync()

    result = await service.switch({"customers_id": 2, "services_id": 11}, 55)

    assert result["ok"], result
    assert [c[0] for c in client.writes()] == ["start"]
    assert service.state.running.customers_id == 2


async def test_switch_refused_if_other_entry_runs(make_service, client):
    service = await make_service()
    client.running = entry(55)
    await service.sync()
    client.running = entry(56)

    result = await service.switch({"customers_id": 2, "services_id": 11}, 55)

    assert result["ok"] is False
    assert client.writes() == []
    assert service.state.running.entry_id == 56


async def test_switch_refused_if_stopped_elsewhere(make_service, client):
    service = await make_service()
    client.running = entry(55)
    await service.sync()
    client.running = None

    result = await service.switch({"customers_id": 2, "services_id": 11}, 55)

    assert result["ok"] is False
    assert client.writes() == []


async def test_invalid_context_is_rejected(make_service, client):
    service = await make_service()
    await service.sync()
    # Project 6 belongs to customer 2, not 1.
    result = await service.start({"customers_id": 1, "projects_id": 6, "services_id": 10})
    assert result["ok"] is False
    unknown = await service.start({"customers_id": 99, "services_id": 10})
    assert unknown["ok"] is False
    assert client.writes() == []


async def test_auth_failure_stops_polling(make_service, client, notifier):
    service = await make_service()
    client.get_error = api.AuthError(401, "unauthorized")

    assert not await service.sync()

    assert service.state.status == Status.AUTH_FAILED
    assert service.next_delay() is None
    await asyncio.sleep(0)
    assert notifier.sent  # one notification on the transition


async def test_rate_limit_backs_off(make_service, client):
    service = await make_service()
    client.get_error = api.RateLimitError(429, "slow down", retry_after=600)
    assert not await service.sync()
    assert service.state.stale
    assert service.next_delay() >= 600


async def test_network_error_keeps_last_state(make_service, client):
    service = await make_service()
    client.running = entry(55)
    await service.sync()
    client.get_error = api.NetworkError("ConnectError")

    assert not await service.sync()

    assert service.state.status == Status.RUNNING
    assert service.state.stale
    assert service.next_delay() > 60


async def test_external_start_is_reported(make_service, client):
    service = await make_service()
    await service.sync()
    client.running = entry(77, customers_id=2, services_id=11)
    await service.sync()
    assert service.state.status == Status.RUNNING
    assert "Globex" in service.state.notice


async def test_secret_locked_is_not_unconfigured(make_service):
    service = await make_service(locked=True)
    assert service.state.status == Status.SECRET_LOCKED
    result = await service.start(CTX)
    assert result["ok"] is False


async def test_unlock_then_sync(make_service):
    service = await make_service(locked=True)
    result = await service.unlock()
    assert result["ok"]
    await service.sync()
    assert service.state.status == Status.STOPPED


async def test_unconfigured_without_credentials(make_service):
    service = await make_service(credentials=None)
    assert service.state.status == Status.UNCONFIGURED
    result = await service.set_credentials("test@example.org", "abc-key")
    assert result["ok"], result
    assert service.state.status == Status.UNKNOWN
    assert service.secrets.credentials.api_key == "abc-key"


async def test_recent_contexts_are_remembered(make_service, client, tmp_path):
    service = await make_service()
    await service.sync()
    await service.start(CTX)
    contexts = await service.list_contexts()
    assert contexts["recent"][0]["label"] == "ACME › Shop › Development"
    # Persisted for the next daemon start.
    assert service.store.load_recent_contexts()[0].customers_id == 1


async def test_today_seconds_include_running_clock_once(make_service, client, fake_time):
    service = await make_service()
    client.running = entry(55)
    fake_time.advance(30 * 60)
    client.now = client.now.replace(minute=30)
    await service.sync()
    assert service.state.today_seconds == 30 * 60


async def test_suspend_triggers_sync_and_notice(make_service, client, fake_time, notifier):
    service = await make_service()
    client.running = entry(55)
    await service.sync()
    requested = []
    service.add_sync_requester(lambda: requested.append(True))

    fake_time.advance(3600, suspended=True)
    service.tick()
    await asyncio.sleep(0)

    assert requested
    assert notifier.sent


async def test_screen_lock_reminder_only_when_running(make_service, client, notifier):
    service = await make_service()
    await service.sync()
    await service.on_screen_locked()
    assert notifier.sent == []
    client.running = entry(55)
    await service.sync()
    await service.on_screen_locked()
    assert len(notifier.sent) == 1


async def test_concurrent_syncs_are_merged(make_service, client):
    service = await make_service()
    await asyncio.gather(service.sync(), service.sync(), service.sync())
    assert sum(1 for c in client.calls if c[0] == "get_clock") == 1
