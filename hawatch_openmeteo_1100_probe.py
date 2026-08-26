#!/usr/bin/env python3
"""
دریافت آزمایشی آب‌وهوا برای ۱۱۰۰ نقطه از Open-Meteo.

اگر فایل points.json وجود داشته باشد، نقاط واقعی از آن خوانده می‌شوند.
در غیر این صورت، برای تست API، ۱۱۰۰ نقطه‌ی آزمایشی در محدوده‌ی ایران ساخته می‌شود.

فرمت points.json:
[
  {
    "id": "tochal-summit",
    "latitude": 35.8842,
    "longitude": 51.4197,
    "elevation": 3964
  }
]
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


API_URL = "https://api.open-meteo.com/v1/forecast"
POINTS_FILE = Path("points.json")
OUTPUT_FILE = Path("hawatch_openmeteo_1100_result.json")

TOTAL_POINTS = 1100
BATCH_SIZE = 100
PAUSE_AFTER_SUCCESS_SECONDS = 30
MINUTE_RETRY_WAIT_SECONDS = 65
MAX_MINUTE_RETRIES = 3

# حداکثر ۱۰ متغیر تا تست به شکل محافظه‌کارانه و کم‌مصرف انجام شود.
HOURLY_VARIABLES = ",".join(
    [
        "temperature_2m",
        "apparent_temperature",
        "precipitation_probability",
        "precipitation",
        "snowfall",
        "weather_code",
        "visibility",
        "wind_speed_10m",
        "wind_direction_10m",
        "wind_gusts_10m",
    ]
)


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def make_test_points(count: int) -> list[dict[str, Any]]:
    """نقاط آزمایشی معتبر؛ برای تست API، نه داده‌ی واقعی مسیرها."""
    points = []
    for index in range(count):
        row = index // 50
        col = index % 50
        points.append(
            {
                "id": f"test-{index + 1:04d}",
                "latitude": round(27.0 + row * 0.45, 5),
                "longitude": round(44.0 + col * 0.38, 5),
            }
        )
    return points


def load_points() -> tuple[list[dict[str, Any]], str]:
    if not POINTS_FILE.exists():
        return make_test_points(TOTAL_POINTS), "generated_test_points"

    points = json.loads(POINTS_FILE.read_text(encoding="utf-8"))
    if not isinstance(points, list):
        raise ValueError("points.json باید یک آرایه از نقاط باشد")

    normalized = []
    for index, point in enumerate(points, start=1):
        if not isinstance(point, dict):
            raise ValueError(f"نقطه‌ی شماره‌ی {index} آبجکت نیست")
        if "latitude" not in point or "longitude" not in point:
            raise ValueError(f"نقطه‌ی شماره‌ی {index} مختصات کامل ندارد")

        normalized.append(
            {
                "id": str(point.get("id", f"point-{index:04d}")),
                "latitude": float(point["latitude"]),
                "longitude": float(point["longitude"]),
                **(
                    {"elevation": float(point["elevation"])}
                    if point.get("elevation") is not None
                    else {}
                ),
            }
        )

    if len(normalized) != TOTAL_POINTS:
        raise ValueError(
            f"برای تست باید دقیقاً {TOTAL_POINTS} نقطه داشته باشیم؛ "
            f"تعداد فعلی: {len(normalized)}"
        )
    return normalized, "points.json"


def build_url(points: list[dict[str, Any]]) -> str:
    params: dict[str, str] = {
        "latitude": ",".join(f"{p['latitude']:.5f}" for p in points),
        "longitude": ",".join(f"{p['longitude']:.5f}" for p in points),
        "timezone": "Asia/Tehran",
        "models": "best_match",
        "cell_selection": "land",
        "forecast_hours": "72",
        "hourly": HOURLY_VARIABLES,
        "temperature_unit": "celsius",
        "wind_speed_unit": "kmh",
        "precipitation_unit": "mm",
        "timeformat": "iso8601",
    }

    # فقط وقتی همه‌ی نقاط batch ارتفاع دارند، elevation را ارسال می‌کنیم.
    if all("elevation" in point for point in points):
        params["elevation"] = ",".join(str(point["elevation"]) for point in points)

    return f"{API_URL}?{urlencode(params)}"


def save_result(result: dict[str, Any]) -> None:
    OUTPUT_FILE.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def fetch_batch(batch_points: list[dict[str, Any]]) -> tuple[int, Any, float]:
    url = build_url(batch_points)
    started = time.monotonic()
    request = Request(url, headers={"User-Agent": "hawatch-openmeteo-probe/1.0"})

    try:
        with urlopen(request, timeout=60) as response:
            body = response.read().decode("utf-8")
            return response.status, json.loads(body), time.monotonic() - started
    except HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        try:
            parsed_body = json.loads(body)
        except json.JSONDecodeError:
            parsed_body = {"raw_error": body}
        return error.code, parsed_body, time.monotonic() - started
    except (URLError, TimeoutError) as error:
        return 0, {"transport_error": str(error)}, time.monotonic() - started


def response_is_valid(payload: Any, expected_count: int) -> tuple[bool, str]:
    if not isinstance(payload, list):
        return False, "پاسخ آرایه نیست"
    if len(payload) != expected_count:
        return False, f"تعداد نقاط برگشتی {len(payload)} است، انتظار {expected_count} بود"

    for index, item in enumerate(payload, start=1):
        if not isinstance(item, dict):
            return False, f"آیتم {index} آبجکت نیست"
        hourly = item.get("hourly")
        if not isinstance(hourly, dict) or not hourly.get("time"):
            return False, f"آیتم {index} داده‌ی hourly ندارد"

    return True, "ok"


def main() -> None:
    points, source = load_points()
    batches = [
        points[start : start + BATCH_SIZE]
        for start in range(0, len(points), BATCH_SIZE)
    ]

    result: dict[str, Any] = {
        "schema_version": "hawatch.openmeteo-probe.v1",
        "started_at_utc": now_utc(),
        "source": source,
        "total_points": len(points),
        "batch_size": BATCH_SIZE,
        "total_batches": len(batches),
        "pause_after_success_seconds": PAUSE_AFTER_SUCCESS_SECONDS,
        "endpoint": API_URL,
        "hourly_variables": HOURLY_VARIABLES.split(","),
        "batches": [],
        "summary": {
            "successful_batches": 0,
            "successful_points": 0,
            "failed_batches": 0,
            "returned_points": 0,
            "all_batches_http_200": False,
            "all_points_have_data": False,
        },
    }
    save_result(result)

    for batch_number, batch_points in enumerate(batches, start=1):
        print(
            f"Batch {batch_number}/{len(batches)} "
            f"({len(batch_points)} points) ...",
            flush=True,
        )

        attempts = 0
        while True:
            attempts += 1
            status, payload, elapsed = fetch_batch(batch_points)

            if status == 200:
                valid, validation_message = response_is_valid(
                    payload, len(batch_points)
                )
                batch_result = {
                    "batch_number": batch_number,
                    "requested_points": len(batch_points),
                    "http_status": status,
                    "attempts": attempts,
                    "elapsed_seconds": round(elapsed, 3),
                    "returned_points": len(payload) if isinstance(payload, list) else 0,
                    "validation_ok": valid,
                    "validation_message": validation_message,
                    "point_ids": [point["id"] for point in batch_points],
                    "data": payload if valid else None,
                }
                result["batches"].append(batch_result)
                result["summary"]["successful_batches"] += int(valid)
                result["summary"]["successful_points"] += len(batch_points) if valid else 0
                result["summary"]["returned_points"] += (
                    len(payload) if isinstance(payload, list) else 0
                )
                save_result(result)
                print(
                    f"  HTTP 200 | returned={batch_result['returned_points']} "
                    f"| data={'yes' if valid else 'no'}",
                    flush=True,
                )
                break

            reason = str(payload.get("reason", "")) if isinstance(payload, dict) else ""
            batch_result = {
                "batch_number": batch_number,
                "requested_points": len(batch_points),
                "http_status": status,
                "attempts": attempts,
                "elapsed_seconds": round(elapsed, 3),
                "reason": reason,
                "point_ids": [point["id"] for point in batch_points],
            }
            result["batches"].append(batch_result)
            result["summary"]["failed_batches"] += 1
            save_result(result)

            if "Minutely" in reason and attempts <= MAX_MINUTE_RETRIES:
                print(
                    f"  HTTP 429 minutely; waiting {MINUTE_RETRY_WAIT_SECONDS}s ...",
                    flush=True,
                )
                time.sleep(MINUTE_RETRY_WAIT_SECONDS)
                result["batches"].pop()
                result["summary"]["failed_batches"] -= 1
                continue

            if "Hourly" in reason:
                print("  HTTP 429 hourly; stop and keep partial JSON.", flush=True)
            elif "Daily" in reason:
                print("  HTTP 429 daily; stop and keep partial JSON.", flush=True)
            else:
                print(f"  request failed: HTTP {status}; stop.", flush=True)
            break

        if result["batches"][-1].get("http_status") != 200:
            break

        if batch_number < len(batches):
            print(f"  sleeping {PAUSE_AFTER_SUCCESS_SECONDS}s ...", flush=True)
            time.sleep(PAUSE_AFTER_SUCCESS_SECONDS)

    successful_points = result["summary"]["successful_points"]
    successful_batches = result["summary"]["successful_batches"]
    result["summary"]["all_batches_http_200"] = successful_batches == len(batches)
    result["summary"]["all_points_have_data"] = successful_points == len(points)
    result["finished_at_utc"] = now_utc()
    save_result(result)

    print("\nFinished")
    print(f"  successful batches: {successful_batches}/{len(batches)}")
    print(f"  successful points: {successful_points}/{len(points)}")
    print(f"  output: {OUTPUT_FILE.resolve()}")


if __name__ == "__main__":
    main()