# SPDX-License-Identifier: MPL-2.0
"""Quick start/stop with the default booking, daily target and overtime warning."""

from __future__ import annotations

import asyncio
from datetime import timedelta

import pytest

from clockodo_plasma import api
from clockodo_plasma.config import Settings
from clockodo_plasma.state import Status

from ..conftest import T0, entry

DEFAULT = {"default_customers_id": 1, "default_projects_id": 5, "default_services_id": 10}


async def test_quick_toggle_without_default_asks_for_the_picker(make_service, client):
    service = await make_service()
    await service.sync()
    result = await service.quick_toggle("")
    assert result["ok"] is False
    assert result["needs_picker"] is True
    assert client.writes() == []


async def test_quick_toggle_starts_default_and_stops_seen_entry(make_service, client):
    service = await make_service()
    await service.sync()
    assert (await service.set_settings(DEFAULT))["ok"]
    assert service.state.quick["label"] == "ACME › Shop › Development"
    assert service.state.quick["valid"] is True

    result = await service.quick_toggle("")
    assert result["ok"], result
    assert service.state.status == Status.RUNNING
    started = client.writes()[0][1]
    assert (started.customers_id, started.projects_id, started.services_id) == (1, 5, 10)

    result = await service.quick_toggle(str(service.state.running.entry_id))
    assert result["ok"], result
    assert service.state.status == Status.STOPPED


async def test_quick_toggle_never_replaces_a_clock_running_elsewhere(
    make_service, client, notifier
):
    service = await make_service()
    await service.sync()
    await service.set_settings(DEFAULT)
    client.running = entry(55, customers_id=2, services_id=11)  # started on the phone

    result = await service.quick_toggle("")  # the widget still showed "stopped"
    await asyncio.sleep(0)

    assert result["ok"] is False
    assert client.writes() == []
    assert notifier.sent  # the popup is closed, so the user gets a notification


async def test_quick_toggle_stops_only_the_seen_entry(make_service, client):
    service = await make_service()
    client.running = entry(55)
    await service.sync()
    result = await service.quick_toggle("54")
    assert result["ok"] is False
    assert client.writes() == []


async def test_recent_contexts_are_published_with_labels(make_service, client):
    service = await make_service()
    await service.sync()
    await service.start({"customers_id": 2, "services_id": 11})
    assert service.state.recent[0]["label"] == "Globex › Meeting"
    assert service.state.to_dict()["recent"] == service.state.recent


async def test_target_is_read_once_per_day(make_service, client):
    client.target = 8 * 3600
    service = await make_service()
    await service.sync()
    await service.sync()
    assert service.state.target_seconds == 8 * 3600
    assert sum(1 for c in client.calls if c[0] == "get_day_target") == 1


async def test_missing_target_does_not_fail_the_sync(make_service, client, fake_time):
    client.target_error = api.ServerError(500, "boom")
    service = await make_service()
    assert await service.sync()
    assert service.state.target_seconds is None
    await service.sync()  # no retry before the retry interval
    assert sum(1 for c in client.calls if c[0] == "get_day_target") == 1

    client.target_error = None
    client.target = 3600
    fake_time.advance(901)
    await service.sync()
    assert service.state.target_seconds == 3600


async def test_forbidden_target_is_not_retried_today(make_service, client, fake_time):
    client.target_error = api.ForbiddenError(403, "no access")
    service = await make_service()
    assert await service.sync()
    fake_time.advance(3600)
    await service.sync()
    assert sum(1 for c in client.calls if c[0] == "get_day_target") == 1


async def running_over_target(make_service, client, **settings):
    client.target = 3600
    client.running = entry(55, time_since=T0 - timedelta(hours=2))
    service = await make_service()
    await service.set_settings(settings)
    await service.sync()
    assert service.state.today_seconds >= 2 * 3600
    return service


async def test_overtime_warning_once_then_repeated(make_service, client, notifier, fake_time):
    service = await running_over_target(make_service, client, overtime_repeat_minutes=60)
    service.tick()
    await asyncio.sleep(0)
    assert len(notifier.sent) == 1
    assert notifier.actions[0][0][0] == "stop"

    service.tick()
    fake_time.advance(30 * 60)
    service.tick()
    await asyncio.sleep(0)
    assert len(notifier.sent) == 1

    fake_time.advance(31 * 60)
    service.tick()
    await asyncio.sleep(0)
    assert len(notifier.sent) == 2


async def test_overtime_warning_respects_tolerance_and_can_be_disabled(
    make_service, client, notifier
):
    service = await running_over_target(make_service, client, overtime_after_minutes=120)
    service.tick()
    await asyncio.sleep(0)
    assert notifier.sent == []  # 1 h over target, tolerance is 2 h

    await service.set_settings({"overtime_after_minutes": 0, "overtime_notify": False})
    service.tick()
    await asyncio.sleep(0)
    assert notifier.sent == []


async def test_overtime_action_stops_the_warned_entry(make_service, client, notifier):
    service = await running_over_target(make_service, client)
    service.tick()
    await asyncio.sleep(0)
    await notifier.callbacks[0]("stop")
    assert client.writes() == [("stop", 55)]
    assert service.state.status == Status.STOPPED


def test_default_booking_needs_customer_and_service():
    with pytest.raises(ValueError):
        Settings().updated({"default_customers_id": 1})
    with pytest.raises(ValueError):
        Settings().updated({"default_projects_id": 5, "default_services_id": 10})
    settings = Settings().updated(DEFAULT | {"default_text": " Daily "})
    context = settings.default_context()
    assert context is not None
    assert (context.customers_id, context.projects_id, context.text) == (1, 5, "Daily")
    assert Settings().default_context() is None


@pytest.mark.parametrize(
    "changes",
    [
        {"panel_style": "disco"},
        {"modifier": "hyper"},
        {"middle_click": "explode"},
        {"overtime_after_minutes": 241},
        {"overtime_repeat_minutes": -1},
    ],
)
def test_invalid_ui_settings_are_rejected(changes):
    with pytest.raises(ValueError):
        Settings().updated(changes)


def test_ui_settings_are_published():
    ui = Settings().ui()
    assert ui == {
        "panel_style": "ring",
        "colorize": True,
        "modifier": "ctrl",
        "modifier_click": "quick",
        "middle_click": "quick",
        "overtime_color": True,
    }
