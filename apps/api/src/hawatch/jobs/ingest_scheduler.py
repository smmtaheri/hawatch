"""Run the existing live-ingest command at fixed local wall-clock times."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo


DEFAULT_SCHEDULE = ("00:00", "06:00", "12:00", "18:00")
DEFAULT_TIMEZONE = "Asia/Tehran"


def parse_schedule(value: str | None) -> tuple[int, ...]:
    """Return unique minutes after midnight from a comma-separated HH:MM list."""

    raw_values = list(DEFAULT_SCHEDULE) if value is None else value.split(",")
    minutes: set[int] = set()
    for raw_value in raw_values:
        item = raw_value.strip()
        parts = item.split(":")
        if len(parts) != 2 or not all(part.isdigit() for part in parts):
            raise ValueError(f"invalid ingest schedule time: {item!r}")
        hour, minute = (int(part) for part in parts)
        if not 0 <= hour <= 23 or not 0 <= minute <= 59:
            raise ValueError(f"invalid ingest schedule time: {item!r}")
        minutes.add(hour * 60 + minute)
    if not minutes:
        raise ValueError("ingest schedule cannot be empty")
    return tuple(sorted(minutes))


def next_scheduled_run(
    now: datetime, schedule: tuple[int, ...], tz: ZoneInfo
) -> datetime:
    """Return the next scheduled wall-clock instant strictly after ``now``."""

    localized_now = now.astimezone(tz) if now.tzinfo else now.replace(tzinfo=tz)
    local_midnight = localized_now.replace(hour=0, minute=0, second=0, microsecond=0)
    for minute_of_day in schedule:
        candidate = local_midnight + timedelta(minutes=minute_of_day)
        if candidate > localized_now:
            return candidate
    return local_midnight + timedelta(days=1, minutes=schedule[0])


def _log(event: str, **fields: object) -> None:
    payload = {
        "@timestamp": datetime.now(timezone.utc).isoformat(),
        "level": "INFO",
        "service": "hawatch-ingest-scheduler",
        "event": event,
        **fields,
    }
    print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), flush=True)


def main() -> int:
    try:
        timezone_name = os.getenv("HAWATCH_TIMEZONE", DEFAULT_TIMEZONE)
        tz = ZoneInfo(timezone_name)
        schedule = parse_schedule(os.getenv("HAWATCH_INGEST_SCHEDULE"))
    except (ValueError, KeyError) as exc:
        _log("ingest.scheduler_config_error", error=str(exc))
        return 2

    _log(
        "ingest.scheduler_started",
        timezone=timezone_name,
        schedule=[f"{minute // 60:02d}:{minute % 60:02d}" for minute in schedule],
    )

    try:
        while True:
            now = datetime.now(tz)
            target = next_scheduled_run(now, schedule, tz)
            wait_seconds = max(0.0, (target - now).total_seconds())
            _log(
                "ingest.scheduler_waiting",
                scheduled_for=target.isoformat(),
                wait_seconds=round(wait_seconds),
            )
            time.sleep(wait_seconds)

            _log("ingest.scheduler_run_started", scheduled_for=target.isoformat())
            result = subprocess.run(
                [sys.executable, "manage.py", "ingest_open_meteo"],
                check=False,
            )
            _log(
                "ingest.scheduler_run_finished",
                scheduled_for=target.isoformat(),
                exit_code=result.returncode,
                status="success" if result.returncode == 0 else "failed",
            )
    except KeyboardInterrupt:
        _log("ingest.scheduler_stopped")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
