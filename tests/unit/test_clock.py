# SPDX-License-Identifier: MPL-2.0
from __future__ import annotations

from datetime import timedelta

from clockodo_plasma.clock import ServerClock

from ..conftest import T0, FakeTime


def test_now_follows_server_time_not_wall_clock():
    ft = FakeTime()
    ft.wall += 300  # local clock is 5 minutes fast
    clock = ServerClock(lambda: ft.mono, lambda: ft.wall)
    clock.sync(T0)
    ft.advance(60)
    assert clock.now() == T0 + timedelta(seconds=60)
    assert round(clock.offset_seconds()) == -300


def test_detects_suspend_and_moves_anchor():
    ft = FakeTime()
    clock = ServerClock(lambda: ft.mono, lambda: ft.wall)
    clock.sync(T0)
    ft.advance(1)
    assert clock.check_jump() == 0.0
    ft.advance(3600, suspended=True)
    assert round(clock.check_jump()) == 3600
    assert clock.now() == T0 + timedelta(seconds=3601)
    assert clock.check_jump() == 0.0


def test_unsynced_clock_uses_wall_time():
    ft = FakeTime()
    clock = ServerClock(lambda: ft.mono, lambda: ft.wall)
    assert not clock.synced
    assert clock.now() == T0
