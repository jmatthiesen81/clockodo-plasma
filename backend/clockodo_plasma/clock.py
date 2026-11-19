# SPDX-License-Identifier: MPL-2.0
"""Server-anchored time keeping and detection of wall clock jumps.

The running duration is derived from Clockodo's ``current_time`` and advanced
with the monotonic clock, so a wrong local wall clock does not matter.
``CLOCK_MONOTONIC`` stops during suspend; the difference between wall clock and
monotonic clock therefore jumps after resume, which is how suspend (and manual
clock changes) are detected.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

JUMP_THRESHOLD = 5.0  # seconds


class ServerClock:
    def __init__(
        self,
        monotonic: Callable[[], float] = time.monotonic,
        wall: Callable[[], float] = time.time,
    ) -> None:
        self._monotonic = monotonic
        self._wall = wall
        self._anchor_server: datetime | None = None
        self._anchor_mono = 0.0
        self._last_drift = self._drift()

    def _drift(self) -> float:
        return self._wall() - self._monotonic()

    def sync(self, server_time: datetime) -> None:
        self._anchor_server = server_time.astimezone(UTC)
        self._anchor_mono = self._monotonic()

    @property
    def synced(self) -> bool:
        return self._anchor_server is not None

    def now(self) -> datetime:
        """Best estimate of the server's current time (UTC)."""
        if self._anchor_server is None:
            return datetime.fromtimestamp(self._wall(), UTC)
        return self._anchor_server + timedelta(seconds=self._monotonic() - self._anchor_mono)

    def offset_seconds(self) -> float:
        """Server time minus local wall time."""
        return (self.now() - datetime.fromtimestamp(self._wall(), UTC)).total_seconds()

    def check_jump(self) -> float:
        """Return the size of a wall clock jump since the last check (0 if none).

        After a jump the anchor is moved by the same amount, so ``now()`` stays
        plausible until the next sync with the server.
        """
        drift = self._drift()
        delta = drift - self._last_drift
        self._last_drift = drift
        if abs(delta) < JUMP_THRESHOLD:
            return 0.0
        if self._anchor_server is not None and delta > 0:
            # Suspend: monotonic time stood still, real time went on.
            self._anchor_server += timedelta(seconds=delta)
        return delta
