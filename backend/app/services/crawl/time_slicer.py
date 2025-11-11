from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable, List, Tuple


SECONDS_PER_DAY = 86400


@dataclass(frozen=True)
class TimeSlice:
    start: datetime
    end: datetime

    def duration_days(self) -> float:
        return (self.end - self.start).total_seconds() / SECONDS_PER_DAY


def generate_slices(
    since: datetime,
    until: datetime,
    *,
    slice_days: int = 30,
    overlap_seconds: int = 2 * 3600,
) -> List[TimeSlice]:
    """
    Generate time slices from [since, until], each slice of `slice_days` length,
    with an overlap (default 2h) to reduce boundary loss.
    """
    if since.tzinfo is None:
        since = since.replace(tzinfo=timezone.utc)
    if until.tzinfo is None:
        until = until.replace(tzinfo=timezone.utc)
    if since >= until:
        return []
    step = timedelta(days=max(1, slice_days))
    overlap = timedelta(seconds=max(0, overlap_seconds))

    slices: List[TimeSlice] = []
    cursor = since
    while cursor < until:
        end = min(until, cursor + step)
        slices.append(TimeSlice(start=cursor, end=end))
        # If we've reached the end, stop to prevent infinite loops when using overlap
        if end >= until:
            break
        # Next slice starts at end - overlap (move forward by step-overlap)
        cursor = end - overlap
    return slices


def split_slice(ts: TimeSlice) -> Tuple[TimeSlice, TimeSlice]:
    mid = ts.start + (ts.end - ts.start) / 2
    # preserve 1 second overlap
    left = TimeSlice(ts.start, mid)
    right = TimeSlice(mid - timedelta(seconds=1), ts.end)
    return left, right


def needs_split(hit_count: int, split_threshold: int = 900) -> bool:
    return hit_count >= max(1, split_threshold)


def can_split(ts: TimeSlice, min_slice_days: int = 1) -> bool:
    return ts.duration_days() > max(0, min_slice_days)
