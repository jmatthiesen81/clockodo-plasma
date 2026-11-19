# SPDX-License-Identifier: MPL-2.0
"""Polling loop: one poller for all widget instances.

- Scheduled syncs follow the configured interval (or the back-off after
  failures, see ``Service.next_delay``); 0 switches scheduled polling off.
- ``trigger()`` requests an immediate sync (popup opened, after resume, day
  change). Triggers that arrive while a sync runs are merged into one follow-up
  sync.
- A one-second tick drives jump/day-change detection and reminders; once a
  minute the daily total is recomputed locally.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging

from .service import Service

log = logging.getLogger(__name__)


class Poller:
    def __init__(self, service: Service, tick_seconds: float = 1.0) -> None:
        self.service = service
        self.tick_seconds = tick_seconds
        self._event = asyncio.Event()
        self._tasks: list[asyncio.Task[None]] = []
        service.add_sync_requester(self.trigger)

    def trigger(self) -> None:
        self._event.set()

    def start(self) -> None:
        loop = asyncio.get_running_loop()
        self._tasks = [loop.create_task(self._poll_loop()), loop.create_task(self._tick_loop())]

    async def stop(self) -> None:
        for task in self._tasks:
            task.cancel()
        for task in self._tasks:
            with contextlib.suppress(asyncio.CancelledError):
                await task

    async def _poll_loop(self) -> None:
        # Initial sync right after start.
        self._event.set()
        while True:
            delay = self.service.next_delay()
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(self._event.wait(), timeout=delay)
            self._event.clear()
            try:
                await self.service.sync()
            except asyncio.CancelledError:
                raise
            except Exception:
                log.exception("sync failed unexpectedly")

    async def _tick_loop(self) -> None:
        ticks = 0
        while True:
            await asyncio.sleep(self.tick_seconds)
            ticks += 1
            try:
                self.service.tick()
                if ticks % 60 == 0:
                    self.service.minute_update()
            except Exception:
                log.exception("tick failed")
