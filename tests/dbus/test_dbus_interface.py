# SPDX-License-Identifier: MPL-2.0
"""Exercise the exported D-Bus interface on a private session bus.

Run under ``dbus-run-session`` (scripts/test.sh does this); skipped otherwise.
"""

from __future__ import annotations

import asyncio
import json
import os

import pytest
from dbus_fast import BusType, Message, MessageType
from dbus_fast.aio import MessageBus

from clockodo_plasma import DBUS_INTERFACE, DBUS_NAME, DBUS_PATH
from clockodo_plasma.dbus_interface import ClockodoInterface

from ..conftest import entry

pytestmark = pytest.mark.skipif(
    not os.environ.get("DBUS_SESSION_BUS_ADDRESS"), reason="needs a session bus"
)


async def call(bus: MessageBus, member: str, signature: str = "", body: list | None = None):
    reply = await bus.call(
        Message(
            destination=DBUS_NAME,
            path=DBUS_PATH,
            interface=DBUS_INTERFACE,
            member=member,
            signature=signature,
            body=body or [],
        )
    )
    assert reply.message_type == MessageType.METHOD_RETURN, reply.body
    return reply.body[0] if reply.body else None


@pytest.fixture
async def buses(make_service, client):
    service = await make_service()
    server = await MessageBus(bus_type=BusType.SESSION).connect()
    server.export(DBUS_PATH, ClockodoInterface(service))
    await server.request_name(DBUS_NAME)
    caller = await MessageBus(bus_type=BusType.SESSION).connect()
    yield service, caller
    caller.disconnect()
    server.disconnect()


async def test_state_and_actions_over_dbus(buses, client):
    service, bus = buses
    await service.sync()

    state = json.loads(await call(bus, "GetState"))
    assert state["status"] == "stopped"

    contexts = json.loads(await call(bus, "ListContexts"))
    assert {c["name"] for c in contexts["customers"]} == {"ACME", "Globex"}

    signals: list[dict] = []

    def on_message(message: Message) -> None:
        if message.message_type == MessageType.SIGNAL and message.member == "StateChanged":
            signals.append(json.loads(message.body[0]))

    bus.add_message_handler(on_message)
    await bus.call(
        Message(
            destination="org.freedesktop.DBus",
            path="/org/freedesktop/DBus",
            interface="org.freedesktop.DBus",
            member="AddMatch",
            signature="s",
            body=[f"type='signal',interface='{DBUS_INTERFACE}'"],
        )
    )

    result = json.loads(
        await call(bus, "Start", "s", [json.dumps({"customers_id": 1, "services_id": 10})])
    )
    assert result["ok"], result
    await asyncio.sleep(0.1)
    assert any(s["status"] == "running" for s in signals)
    assert any(s["action_pending"] for s in signals)

    entry_id = json.loads(await call(bus, "GetState"))["running"]["entry_id"]
    assert isinstance(entry_id, str)
    result = json.loads(await call(bus, "Stop", "s", [entry_id]))
    assert result["ok"], result


async def test_state_never_contains_the_key(buses, client):
    service, bus = buses
    client.running = entry(5)
    await service.sync()
    for member in ("GetState", "GetSettings"):
        assert "secret-key-123" not in await call(bus, member)


async def test_invalid_input_is_rejected(buses):
    _, bus = buses
    result = json.loads(await call(bus, "Stop", "s", ["not-a-number"]))
    assert result["ok"] is False
    result = json.loads(await call(bus, "Start", "s", ["{broken"]))
    assert result["ok"] is False


async def test_quick_toggle_over_dbus(buses, client):
    service, bus = buses
    await service.sync()
    result = json.loads(await call(bus, "QuickToggle", "s", [""]))
    assert result == {"ok": False, "message": result["message"], "needs_picker": True}

    changes = {"default_customers_id": 1, "default_services_id": 10}
    assert json.loads(await call(bus, "SetSettings", "s", [json.dumps(changes)]))["ok"]
    state = json.loads(await call(bus, "GetState"))
    assert state["quick"]["label"] == "ACME › Development"
    assert state["ui"]["panel_style"] == "ring"

    assert json.loads(await call(bus, "QuickToggle", "s", [""]))["ok"]
    entry_id = json.loads(await call(bus, "GetState"))["running"]["entry_id"]
    assert json.loads(await call(bus, "QuickToggle", "s", [entry_id]))["ok"]
    assert json.loads(await call(bus, "QuickToggle", "s", ["nope"]))["ok"] is False
