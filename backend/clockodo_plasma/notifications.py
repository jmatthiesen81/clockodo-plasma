# SPDX-License-Identifier: MPL-2.0
"""Desktop notifications and screen lock monitoring over the session bus."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable

from dbus_fast import Message, MessageType
from dbus_fast.aio import MessageBus

from . import APP_ID

log = logging.getLogger(__name__)

_pending: set[asyncio.Task[None]] = set()

SCREENSAVER_MATCH = "type='signal',interface='org.freedesktop.ScreenSaver',member='ActiveChanged'"


class DesktopNotifier:
    def __init__(self, bus: MessageBus, icon: str = "chronometer") -> None:
        self.bus = bus
        self.icon = icon

    async def notify(self, summary: str, body: str = "") -> None:
        message = Message(
            destination="org.freedesktop.Notifications",
            path="/org/freedesktop/Notifications",
            interface="org.freedesktop.Notifications",
            member="Notify",
            signature="susssasa{sv}i",
            body=[APP_ID, 0, self.icon, summary, body, [], {}, -1],
        )
        try:
            reply = await self.bus.call(message)
        except Exception as exc:
            log.warning("notification failed: %s", type(exc).__name__)
            return
        if reply is not None and reply.message_type == MessageType.ERROR:
            log.warning("notification failed: %s", reply.error_name)


async def watch_screen_lock(bus: MessageBus, on_locked: Callable[[], Awaitable[None]]) -> None:
    """Call ``on_locked`` when the screen gets locked.

    KDE emits ``ActiveChanged`` on two object paths; only the transition from
    unlocked to locked is reported, so duplicates are ignored.
    """
    locked = False

    def handler(message: Message) -> None:
        nonlocal locked
        if (
            message.message_type != MessageType.SIGNAL
            or message.interface != "org.freedesktop.ScreenSaver"
            or message.member != "ActiveChanged"
        ):
            return
        active = bool(message.body[0]) if message.body else False
        if active and not locked:
            locked = True
            # Message handlers run inside the event loop.
            task = asyncio.get_running_loop().create_task(on_locked())
            _pending.add(task)
            task.add_done_callback(_pending.discard)
        elif not active:
            locked = False

    bus.add_message_handler(handler)
    reply = await bus.call(
        Message(
            destination="org.freedesktop.DBus",
            path="/org/freedesktop/DBus",
            interface="org.freedesktop.DBus",
            member="AddMatch",
            signature="s",
            body=[SCREENSAVER_MATCH],
        )
    )
    if reply is not None and reply.message_type == MessageType.ERROR:
        log.warning("cannot watch the screen lock: %s", reply.error_name)
