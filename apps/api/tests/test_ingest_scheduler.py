from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from hawatch.jobs.ingest_scheduler import next_scheduled_run, parse_schedule


TEHRAN = ZoneInfo("Asia/Tehran")
SCHEDULE = parse_schedule("00:00,06:00,12:00,18:00")


def test_default_schedule_is_four_fixed_tehran_runs():
    assert SCHEDULE == (0, 360, 720, 1080)


@pytest.mark.parametrize(
    ("local_time", "expected"),
    [
        (
            datetime(2026, 8, 30, 1, 0, tzinfo=TEHRAN),
            datetime(2026, 8, 30, 6, tzinfo=TEHRAN),
        ),
        (
            datetime(2026, 8, 30, 6, 1, tzinfo=TEHRAN),
            datetime(2026, 8, 30, 12, tzinfo=TEHRAN),
        ),
        (
            datetime(2026, 8, 30, 18, 1, tzinfo=TEHRAN),
            datetime(2026, 8, 31, 0, tzinfo=TEHRAN),
        ),
    ],
)
def test_next_run_uses_tehran_wall_clock(local_time, expected):
    assert next_scheduled_run(local_time, SCHEDULE, TEHRAN) == expected


def test_schedule_parser_sorts_and_deduplicates():
    assert parse_schedule("12:00, 00:00, 12:00, 06:30") == (0, 390, 720)


@pytest.mark.parametrize("value", ["", "25:00", "12:60", "noon", "12"])
def test_schedule_parser_rejects_invalid_values(value):
    with pytest.raises(ValueError):
        parse_schedule(value)
