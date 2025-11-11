from datetime import datetime, timedelta, timezone

from app.services.crawl.time_slicer import (
    TimeSlice,
    generate_slices,
    split_slice,
    needs_split,
    can_split,
)


def _dt(y, m, d, h=0):
    return datetime(y, m, d, h, tzinfo=timezone.utc)


def test_generate_slices_overlap():
    since = _dt(2024, 1, 1)
    until = _dt(2024, 2, 1)
    slices = generate_slices(since, until, slice_days=10, overlap_seconds=7200)
    assert slices, "should generate slices"
    # consecutive slices should overlap by ~2h
    for i in range(1, len(slices)):
        prev = slices[i - 1]
        cur = slices[i]
        assert prev.end >= cur.start, "overlap or contiguous"
    # last slice should end at until
    assert slices[-1].end == until
    # sanity: number of slices finite
    assert len(slices) < 100


def test_split_and_threshold():
    ts = TimeSlice(_dt(2024, 1, 1), _dt(2024, 2, 1))
    assert can_split(ts, min_slice_days=1)
    assert needs_split(950, split_threshold=900)
    left, right = split_slice(ts)
    assert left.start == ts.start and right.end == ts.end
    # halves are smaller than original
    assert left.duration_days() < ts.duration_days()
    assert right.duration_days() < ts.duration_days()
