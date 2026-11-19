# SPDX-License-Identifier: MPL-2.0
"""Daily work time from Clockodo work time intervals.

Clockodo's ``/v2/workTimes`` already merges overlapping entries and leaves out
lump sums. This module clips the intervals to the local day, adds the running
clock exactly once (merging makes a duplicate harmless) and sums them up.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta, tzinfo

from .api import Interval


@dataclass(frozen=True)
class DayBounds:
    start: datetime
    end: datetime


def day_bounds(day: date, tz: tzinfo) -> DayBounds:
    """Start and end of a calendar day in ``tz`` (handles DST: 23 h / 25 h days)."""
    # Converted to UTC: Python does wall-clock arithmetic between datetimes that
    # share a tzinfo, which would ignore the DST switch.
    start = datetime.combine(day, time.min, tzinfo=tz).astimezone(UTC)
    end = datetime.combine(day + timedelta(days=1), time.min, tzinfo=tz).astimezone(UTC)
    return DayBounds(start, end)


def _merge(spans: Iterable[tuple[datetime, datetime]]) -> list[tuple[datetime, datetime]]:
    merged: list[tuple[datetime, datetime]] = []
    for start, end in sorted(spans):
        if end <= start:
            continue
        if merged and start <= merged[-1][1]:
            if end > merged[-1][1]:
                merged[-1] = (merged[-1][0], end)
        else:
            merged.append((start, end))
    return merged


def work_seconds(
    intervals: Iterable[Interval],
    bounds: DayBounds,
    now: datetime,
    running_since: datetime | None = None,
) -> int:
    """Seconds worked within ``bounds`` up to ``now``.

    ``running_since`` is the start of the running clock (if any); it is merged
    with the intervals so it counts exactly once even if Clockodo already
    reports it as an open interval.
    """
    limit = min(bounds.end, now)
    spans: list[tuple[datetime, datetime]] = []
    all_intervals = list(intervals)
    if running_since is not None:
        all_intervals.append(Interval(running_since, None))
    now = now.astimezone(UTC)
    limit = limit.astimezone(UTC)
    for interval in all_intervals:
        start = max(interval.time_since.astimezone(UTC), bounds.start)
        end = interval.time_until.astimezone(UTC) if interval.time_until is not None else now
        end = min(end, limit)
        if end > start:
            spans.append((start, end))
    return int(sum((end - start).total_seconds() for start, end in _merge(spans)))


def format_hhmm(seconds: int) -> str:
    minutes = max(0, int(seconds)) // 60
    return f"{minutes // 60:02d}:{minutes % 60:02d}"
