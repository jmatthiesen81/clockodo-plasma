# SPDX-License-Identifier: MPL-2.0
from __future__ import annotations

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from clockodo_plasma.api import Interval
from clockodo_plasma.time_calculator import day_bounds, format_hhmm, work_seconds

BERLIN = ZoneInfo("Europe/Berlin")


def utc(h: int, m: int = 0, day: int = 19, month: int = 11) -> datetime:
    return datetime(2026, month, day, h, m, tzinfo=UTC)


def test_sums_closed_intervals():
    bounds = day_bounds(date(2026, 11, 19), UTC)
    intervals = [Interval(utc(8), utc(10)), Interval(utc(11), utc(12, 30))]
    assert work_seconds(intervals, bounds, utc(18)) == int(3.5 * 3600)


def test_running_interval_counts_until_now():
    bounds = day_bounds(date(2026, 11, 19), UTC)
    intervals = [Interval(utc(8), utc(9)), Interval(utc(10), None)]
    assert work_seconds(intervals, bounds, utc(10, 30)) == int(1.5 * 3600)


def test_running_clock_is_counted_exactly_once():
    bounds = day_bounds(date(2026, 11, 19), UTC)
    intervals = [Interval(utc(10), None)]
    # Clockodo already reports the open interval and we add the running clock.
    assert work_seconds(intervals, bounds, utc(11), running_since=utc(10)) == 3600
    # Work times may lag behind: the running clock alone still counts.
    assert work_seconds([], bounds, utc(11), running_since=utc(10)) == 3600


def test_overlaps_are_merged():
    bounds = day_bounds(date(2026, 11, 19), UTC)
    intervals = [Interval(utc(8), utc(10)), Interval(utc(9), utc(11))]
    assert work_seconds(intervals, bounds, utc(18)) == 3 * 3600


def test_entry_across_midnight_counts_only_today():
    bounds = day_bounds(date(2026, 11, 19), UTC)
    intervals = [Interval(utc(22, day=18), None)]
    assert work_seconds(intervals, bounds, utc(1)) == 3600


def test_future_end_is_clipped_to_now():
    bounds = day_bounds(date(2026, 11, 19), UTC)
    assert work_seconds([Interval(utc(8), utc(12))], bounds, utc(9)) == 3600


def test_dst_switch_day_has_23_hours():
    bounds = day_bounds(date(2026, 3, 29), BERLIN)
    assert (bounds.end - bounds.start).total_seconds() == 23 * 3600
    # 00:00 local (CET) = 23:00 UTC of the previous day; 2 hours of work over the switch.
    start = datetime(2026, 3, 29, 1, 0, tzinfo=BERLIN)  # 00:00 UTC
    end = datetime(2026, 3, 29, 4, 0, tzinfo=BERLIN)  # 02:00 UTC
    assert work_seconds([Interval(start, end)], bounds, end) == 2 * 3600


def test_local_day_bounds_in_other_timezone():
    bounds = day_bounds(date(2026, 11, 19), BERLIN)
    # 23:30 UTC on the 18th is 00:30 in Berlin on the 19th.
    intervals = [Interval(utc(23, 30, day=18), utc(0, 30))]
    assert work_seconds(intervals, bounds, utc(12)) == 3600


def test_format_hhmm():
    assert format_hhmm(0) == "00:00"
    assert format_hhmm(3599) == "00:59"
    assert format_hhmm(10 * 3600 + 5 * 60) == "10:05"
