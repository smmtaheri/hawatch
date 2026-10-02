"""Private, read-only day contracts for fast planner interactions.

Route choices are evaluated by the existing serializer, not by an alternate
browser risk/ETA algorithm. Forecasts are read once across the longest supported
journey, clipped at the viewer's entitlement boundary, including tolerance.
"""
from collections import defaultdict
from datetime import timedelta
from hashlib import sha256
import json

from django.conf import settings

from hawatch.integrations.weather.hazards import (
    assess_records, warning_intervals, representative_record, POLICY_VERSION, RANK, assessment,
)

from hawatch.common.time import (
    ARRIVAL_FORECAST_TOLERANCE_MINUTES, PERIOD_IDS, SPEED_TIME_FACTORS,
    localize_dt, now_tehran, paced_duration_minutes, planner_period_payload,
)
from hawatch.modules.catalog.seed import refresh_if_bucket_changed
from hawatch.modules.forecasts.models import ForecastRecord
from .serializers import (
    _hourly_for_period, _reading_for_period_summary, _records_for_day,
    meta_base, point_forecast, reading_payload, route_forecast, serialize_route,
)


def _revision(records, access, *, identity):
    # Every read returns the revisions actually used, including partial ingest
    # and Admin entitlement changes. No public or persistent weather cache.
    stamp = [(row.pk, row.generated_at.isoformat(), row.forecast_at.isoformat()) for row in records]
    return sha256(json.dumps([POLICY_VERSION, identity, stamp, access.payload(), access.expires_at.isoformat() if access.expires_at else None], sort_keys=True).encode()).hexdigest()


def point_day_bundle(point, *, selected_date, period, access):
    base = point_forecast(point, selected_date=selected_date, period=period)
    records = _records_for_day(point, selected_date)
    local = now_tehran()
    periods = {}
    for period_id in PERIOD_IDS:
        hourly = _hourly_for_period(point, selected_date, period_id, now=local, records=records)
        periods[period_id] = {
            "period": planner_period_payload(period_id),
            "hourly": hourly,
            "current": _reading_for_period_summary(point, selected_date, period_id, local, records=records),
            "empty": not records,
            "partial": len(hourly) < 3,
        }
    temperatures = [row.apparent_temperature_c for row in records if row.apparent_temperature_c is not None]
    representative = representative_record(records)
    intervals = warning_intervals(records, now=local if selected_date == local.date() else None)
    summary = {
        "apparent_min_c": min(temperatures) if temperatures else None,
        "apparent_max_c": max(temperatures) if temperatures else None,
        "condition": representative.condition_label if representative else "پیش‌بینی این روز در دسترس نیست",
        "severity": max((w["severity"] for w in intervals), key=RANK.get, default="normal"),
        "warnings": intervals,
        "wind_alert": None,
        "policy_version": POLICY_VERSION,
        "weather_code": representative.weather_code if representative else None,
        "forecast_at": representative.forecast_at.isoformat() if representative else None,
        "complete": len({row.forecast_at for row in records}) >= 24 and all(assessment(row)["data_quality"] == "complete" for row in records),
    }
    base.update({"periods": periods, "daily_summary": summary,
                 "data_revision": _revision(records, access, identity=point.slug),
                 "cache_max_age_seconds": 300,
                 "cache_expires_at": access.expires_at.isoformat() if access.expires_at else None})
    return base


def route_day_bundle(route, *, selected_date, period, start_minutes, speed, access):
    refresh_if_bucket_changed()
    local = now_tehran()
    points = list(route.points.select_related("weather_point", "route").all())
    periods = {key: planner_period_payload(key) for key in PERIOD_IDS}
    slots = [slot for spec in periods.values() for slot in spec["planner_slots"]]
    max_duration = max(
        (paced_duration_minutes(point.cumulative_minutes, pace)
         for point in points if point.cumulative_minutes is not None
         for pace in SPEED_TIME_FACTORS), default=0,
    )
    tolerance = timedelta(minutes=ARRIVAL_FORECAST_TOLERANCE_MINUTES)
    start_at = localize_dt(selected_date, 0)
    entitlement_end = localize_dt(access.available_through + timedelta(days=1), 0)
    end_at = min(start_at + timedelta(minutes=max(slots) + max_duration) + tolerance + timedelta(hours=2), entitlement_end)
    point_ids = {point.weather_point_id for point in points if point.weather_point_id}
    if route.target_weather_point_id:
        point_ids.add(route.target_weather_point_id)
    qs = ForecastRecord.objects.filter(
        weather_point_id__in=point_ids,
        forecast_at__gte=start_at - tolerance - timedelta(hours=23), forecast_at__lte=end_at,
        forecast_at__lt=entitlement_end,
    ).order_by("forecast_at", "pk")
    if not settings.DEMO_DATA_ENABLED:
        qs = qs.filter(data_mode="live", provider="open-meteo")
    records = list(qs)
    by_point = defaultdict(list)
    for record in records:
        # The selected day may be outside the data horizon, but access is
        # never widened by forecast matching or midnight tolerance.
        if access.status_for(record.forecast_at.astimezone(local.tzinfo).date()) == "available":
            by_point[record.weather_point_id].append(record)
    for rows in by_point.values():
        assess_records(rows)
    readings = {}

    def closest(wp, target):
        if access.status_for(target.date()) != "available":
            return None
        candidates = [row for row in by_point[wp.pk] if abs(row.forecast_at - target) <= tolerance]
        if not candidates:
            return None
        row = min(candidates, key=lambda item: (abs(item.forecast_at - target), item.forecast_at, item.pk))
        if row.pk not in readings:
            readings[row.pk] = reading_payload(row, now=local)
        return readings[row.pk]

    context = {
        "local": local, "points": points, "route": serialize_route(route),
        "closest": closest, "meta": meta_base(selected_date=selected_date, period=period),
        "hourly": {
            key: _hourly_for_period(route.target_weather_point, selected_date, key, now=local,
                                    records=by_point[route.target_weather_point_id])
            if route.target_weather_point_id else [] for key in PERIOD_IDS
        },
    }
    plans = {}
    point_fields = (
        "arrival_minutes", "arrival_at", "time", "weather_available", "forecast_at",
        "temp", "wind", "icon", "condition", "state", "weather_code", "is_day", "warnings", "data_quality",
    )
    for key, spec in periods.items():
        for pace in SPEED_TIME_FACTORS:
            for slot in spec["planner_slots"]:
                payload = route_forecast(route, selected_date=selected_date, period=key,
                                         start_minutes=slot, speed=pace, _context=context)
                plans[f"{pace}:{slot}"] = {
                    "points": [{field: point[field] for field in point_fields} for point in payload["points"]],
                    "decision": payload["decision"], "stats": payload["stats"], "hero": payload["hero"],
                }
    base = route_forecast(route, selected_date=selected_date, period=period,
                          start_minutes=start_minutes, speed=speed, _context=context)
    base.update({"plans": plans, "periods": periods,
                 "data_revision": _revision(records, access, identity=[route.slug, route.timing_version,
                     [(point.pk, point.cumulative_minutes) for point in points]]),
                 "coverage": {"from": (start_at - tolerance).isoformat(), "to": end_at.isoformat(),
                              "access_through": access.available_through.isoformat()},
                 "cache_max_age_seconds": 300,
                 "cache_expires_at": access.expires_at.isoformat() if access.expires_at else None})
    return base
