# SPDX-License-Identifier: MPL-2.0
"""Desktop notifications and screen lock monitoring over the session bus."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable, Sequence

from dbus_fast import Message, MessageType
from dbus_fast.aio import MessageBus

from . import APP_ID

log = logging.getLogger(__name__)

_pending: set[asyncio.Task[None]] = set()

SCREENSAVER_MATCH = "type='signal',interface='org.freedesktop.ScreenSaver',member='ActiveChanged'"


ActionCallback = Callable[[str], Awaitable[None]]

NOTIFICATIONS = "org.freedesktop.Notifications"
NOTIFICATION_SIGNALS = (
    f"type='signal',interface='{NOTIFICATIONS}',member='ActionInvoked'",
    f"type='signal',interface='{NOTIFICATIONS}',member='NotificationClosed'",
)


class DesktopNotifier:
    def __init__(self, bus: MessageBus, icon: str = "chronometer") -> None:
        self.bus = bus
        self.icon = icon
        self._callbacks: dict[int, ActionCallback] = {}
        self._watching = False

    async def notify(
        self,
        summary: str,
        body: str = "",
        actions: Sequence[tuple[str, str]] = (),
        on_action: ActionCallback | None = None,
    ) -> None:
        """Show a notification; ``actions`` are (key, label) buttons.

        ``on_action`` is called with the key of the button the user pressed.
        """
        flat = [part for action in actions for part in action]
        message = Message(
            destination=NOTIFICATIONS,
            path="/org/freedesktop/Notifications",
            interface=NOTIFICATIONS,
            member="Notify",
            signature="susssasa{sv}i",
            body=[APP_ID, 0, self.icon, summary, body, flat, {}, -1],
        )
        try:
            if on_action is not None:
                await self._watch_actions()
            reply = await self.bus.call(message)
        except Exception as exc:
            log.warning("notification failed: %s", type(exc).__name__)
            return
        if reply is None:
            return
        if reply.message_type == MessageType.ERROR:
            log.warning("notification failed: %s", reply.error_name)
            return
        if on_action is not None and reply.body:
            self._callbacks[int(reply.body[0])] = on_action

    async def _watch_actions(self) -> None:
        if self._watching:
            return
        self._watching = True
        self.bus.add_message_handler(self._on_signal)
        for rule in NOTIFICATION_SIGNALS:
            reply = await self.bus.call(
                Message(
                    destination="org.freedesktop.DBus",
                    path="/org/freedesktop/DBus",
                    interface="org.freedesktop.DBus",
                    member="AddMatch",
                    signature="s",
                    body=[rule],
                )
            )
            if reply is not None and reply.message_type == MessageType.ERROR:
                log.warning("cannot watch notification actions: %s", reply.error_name)

    def _on_signal(self, message: Message) -> None:
        if message.message_type != MessageType.SIGNAL or message.interface != NOTIFICATIONS:
            return
        if not message.body:
            return
        notification_id = int(message.body[0])
        if message.member == "NotificationClosed":
            self._callbacks.pop(notification_id, None)
        elif message.member == "ActionInvoked" and len(message.body) > 1:
            callback = self._callbacks.pop(notification_id, None)
            if callback is not None:
                task = asyncio.get_running_loop().create_task(callback(str(message.body[1])))
                _pending.add(task)
                task.add_done_callback(_pending.discard)


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
