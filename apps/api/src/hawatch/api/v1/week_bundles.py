"""Public eight-day contracts. Identity/weather appear once; plans reference records.

Arrival durations, rounding, timing validity and +/-90 minute matching remain
those of the existing product. Precipitation has its own preceding-hour interval.
"""
from collections import defaultdict
from datetime import timedelta
from bisect import bisect_left
from hashlib import sha256
import json
from django.conf import settings
from hawatch.common.time import now_tehran, localize_dt, day_payload, paced_route_cumulative_minutes, SPEED_TIME_FACTORS
from hawatch.modules.forecasts.models import ForecastRecord
from hawatch.modules.forecasts.attribution import attribution_for_rows
from hawatch.modules.routes.models import Route
from hawatch.modules.routes.timing import route_mean_elevation_m
from hawatch.integrations.weather.hazards import assessment, assess_records, value, representative_record
from hawatch.integrations.weather.equipment import suggest_equipment
from .serializers import get_point, get_route, serialize_point_profile, serialize_route, serialize_route_summary, reading_payload, route_has_usable_timing, point_discovery_payload

FIELDS = ("temperature_c", "apparent_temperature_c", "wind_speed_kmh", "wind_gust_kmh", "wind_direction_deg", "relative_humidity_pct", "visibility_km", "freezing_level_m", "uv_index", "snowfall_cm")
ROUTE_RECORD_FIELDS = (*FIELDS, "forecast_at", "generated_at", "precipitation_mm", "rain_mm", "precipitation_from", "precipitation_to", "weather_code", "condition", "is_day", "heat_index_c", "heat_index_status", "warnings", "state", "data_quality", "equipment_ids")

def records_for(ids, start, end):
    qs = ForecastRecord.objects.filter(weather_point_id__in=ids, forecast_at__gte=start-timedelta(hours=24), forecast_at__lte=end).select_related("weather_point").order_by("forecast_at", "pk")
    if not settings.DEMO_DATA_ENABLED:
        qs = qs.filter(data_mode="live", provider="open-meteo")
    else:
        qs = qs.filter(data_mode="demo", seed_version=settings.DEMO_SEED_VERSION)
    rows = list(qs)
    grouped = defaultdict(list)
    for row in rows:
        grouped[row.weather_point_id].append(row)
    for point_rows in grouped.values():
        assess_records(point_rows)
    return [row for row in rows if row.forecast_at >= start-timedelta(hours=2)]

def public_reading(row):
    p = reading_payload(row)
    return {**{field: value(row, field) for field in FIELDS},
            "forecast_at": p["forecast_at"], "generated_at": row.generated_at.isoformat(),
            "precipitation_mm": value(row, "precipitation_mm"), "rain_mm": value(row, "rain_mm"),
            "precipitation_from": (row.forecast_at-timedelta(hours=1)).isoformat(),
            "precipitation_to": row.forecast_at.isoformat(),
            "weather_code": p["weather_code"], "condition": p["condition"], "is_day": p.get("is_day"),
            "heat_index_c": p["heat_index_c"], "heat_index_status": p["heat_index_status"],
            "warnings": p["warnings"], "state": p["state"], "data_quality": p["data_quality"]}

def aggregate(rows, start, hours):
    end = start + timedelta(hours=hours)
    instant = [r for r in rows if start <= r.forecast_at < end]
    accumulated = [r for r in rows if start < r.forecast_at <= end]
    def metric(field, method, source=instant, *, valid=lambda v: True):
        values = [value(row, field) for row in source]
        if len(source) != hours or any(v is None or not valid(v) for v in values):
            return None
        return method(values)
    heat_readings = [assessment(row) for row in instant]
    heat_missing = len(instant) != hours or any(r["heat_index_status"] == "missing" for r in heat_readings)
    heat_values = [r["heat_index_c"] for r in heat_readings if r["heat_index_c"] is not None]
    heat_status = "missing" if heat_missing else "available" if heat_values else "not_applicable"
    uv = metric("uv_index", max, valid=lambda v: v >= 0)
    if hours == 24:
        # A daily card summarizes the daytime sky, not whichever hour happens
        # to win a whole-day frequency tie (often midnight). Keep its metrics
        # over the full day, but choose the condition from the fixed Tehran
        # daytime window until per-point sunrise/sunset is available.
        daylight = [r for r in instant if 6 <= now_tehran(r.forecast_at).hour < 19]
        rep = representative_record(daylight or instant)
    else:
        rep = representative_record(instant)
    return {"from": start.isoformat(), "to": end.isoformat(), "hour": start.hour,
            "felt": metric("apparent_temperature_c", lambda a: round(sum(a)/len(a), 1)),
            "felt_min": metric("apparent_temperature_c", min), "felt_max": metric("apparent_temperature_c", max),
            "actual": metric("temperature_c", lambda a: round(sum(a)/len(a), 1)),
            "min": metric("temperature_c", min), "max": metric("temperature_c", max),
            "wind": metric("wind_speed_kmh", max), "gust": metric("wind_gust_kmh", max),
            "rain": metric("precipitation_mm", lambda a: round(sum(a), 1), accumulated),
            "humidity": metric("relative_humidity_pct", lambda a: round(sum(a)/len(a))),
            "visibility": metric("visibility_km", min), "freezing": metric("freezing_level_m", min),
            "uv_index": uv,
            "heat_index_c": max(heat_values) if heat_status == "available" else None,
            "heat_index_status": heat_status,
            "direction": value(rep, "wind_direction_deg") if rep else None,
            "weather": rep.weather_code if rep else "unknown",
            "condition": rep.condition_label if rep else "نامشخص",
            "weather_at": now_tehran(rep.forecast_at).isoformat() if rep else None,
            "warnings": [dict(w, at=r.forecast_at.isoformat()) for r, risk in zip(instant, heat_readings) for w in risk["warnings"]],
            "complete": len(instant) == hours and len(accumulated) == hours}

def build_week(kind, slug, today):
    start = localize_dt(today, 0)
    days = [day_payload(today+timedelta(days=i), today) for i in range(8)]
    base = {"schema_version": "week-2", "kind": kind, "timezone": "Asia/Tehran", "days": days,
            "range_start": today.isoformat(), "range_end": (today+timedelta(days=7)).isoformat(),
            "cache_max_age_seconds": 120, "stale_after_hours": settings.FORECAST_STALE_AFTER_HOURS}
    if kind == "point":
        point = get_point(slug)
        from hawatch.modules.catalog.seo import point_seo_copy
        seo = point_seo_copy(point)
        rows = records_for([point.pk], start, start+timedelta(days=8))
        base.update(subject={**serialize_point_profile(point),"seo_title":seo["title"],"seo_description":seo["description"]}, **point_discovery_payload(point),
                    intervals={str(step): [[aggregate(rows, start+timedelta(days=di, hours=h), step) for h in range(0,24,step)] for di in range(8)] for step in (24,6,3,1)})
    else:
        route = get_route(slug)
        points = list(route.points.select_related("weather_point", "route").all())
        mean_elevation_m = route_mean_elevation_m(points)
        timed = route_has_usable_timing(route, points)
        offsets = {
            speed: [
                paced_route_cumulative_minutes(
                    point.cumulative_minutes,
                    route.one_way_minutes,
                    label,
                    distance_km=float(route.distance_km) if route.distance_km is not None else None,
                    ascent_m=route.ascent_m,
                    descent_m=route.descent_m,
                    mean_elevation_m=mean_elevation_m,
                )
                for point in points
            ]
            if timed
            else []
            for speed, label in (("slow", "آرام"), ("medium", "متوسط"), ("fast", "سریع"))
        }
        tail = max((max(v, default=0) for v in offsets.values()), default=0)
        rows = records_for([p.weather_point_id for p in points if p.weather_point_id], start, start+timedelta(days=8, minutes=tail+90))
        by_point = defaultdict(list)
        for i, r in enumerate(rows):
            by_point[r.weather_point_id].append((r.forecast_at, i, r))
        times = {key: [a[0] for a in values] for key,values in by_point.items()}
        equipment = []
        equipment_index = {}
        row_gear = {}
        for i, row in enumerate(rows):
            row_gear[i] = []
            for item in suggest_equipment([row]):
                key = item["id"]
                if key not in equipment_index:
                    equipment_index[key] = len(equipment)
                    equipment.append({"id": key, "name": item["name"], "reason": item["reason"]})
                row_gear[i].append(equipment_index[key])
        plans = {}
        for di in range(8):
            for speed, durations in offsets.items():
                for hour in range(24):
                    selected, indices = [], []
                    for p, duration in zip(points, durations):
                        target = start+timedelta(days=di, hours=hour, minutes=duration)
                        candidates = by_point[p.weather_point_id]
                        n = bisect_left(times.get(p.weather_point_id, []), target)
                        match = min(candidates[max(0,n-1):n+1], key=lambda a: (abs(a[0]-target),a[0],a[2].pk), default=None)
                        if match is not None and abs(match[0]-target) <= timedelta(minutes=90):
                            indices.append(match[1]); selected.append(match[2])
                        else:
                            indices.append(None)
                    plans[f"{di}:{speed}:{hour}"] = {"records": indices}
        # Ship only hours actually referenced by one of the selectable plans.
        used_rows = sorted({i for plan in plans.values() for i in plan["records"] if i is not None})
        row_remap = {old:new for new,old in enumerate(used_rows)}
        used_gear = sorted({gear for i in used_rows for gear in row_gear[i]})
        gear_remap = {old:new for new,old in enumerate(used_gear)}
        for plan in plans.values():
            plan["records"] = [row_remap[i] if i is not None else None for i in plan["records"]]
        compact_records = []
        for old_index in used_rows:
            reading = public_reading(rows[old_index])
            compact_records.append([
                *(reading[field] for field in ROUTE_RECORD_FIELDS[:-1]),
                [gear_remap[gear] for gear in row_gear[old_index]],
            ])
        rows = [rows[i] for i in used_rows]
        equipment = [equipment[i] for i in used_gear]
        distance = 0
        distances = []
        valid_distance = True
        for i,p in enumerate(points):
            if i:
                if p.segment_distance_m is None: valid_distance = False
                else: distance += p.segment_distance_m
            distances.append(round(distance/1000,2) if valid_distance else None)
        base.update(subject=serialize_route(route), related_routes=[serialize_route_summary(r) for r in Route.objects.filter(points__weather_point=points[-1].weather_point, is_active=True).distinct().order_by("sort_order", "slug")] if points else [], points=[{"slug": p.weather_point.slug if p.weather_point_id else None, "name": p.name, "weather_point_id": p.weather_point_id, "distance_km": distances[i]} for i,p in enumerate(points)], offsets=offsets, record_fields=ROUTE_RECORD_FIELDS, records=compact_records, plans=plans, equipment=equipment, timing_pending=not timed)
    freshness_rows = [r for r in rows if r.forecast_at >= start] if kind == "point" else rows
    attribution = attribution_for_rows(freshness_rows)
    base["attribution"] = attribution
    base["last_generated_at"] = attribution["updated_at"] if attribution else None
    base["data_mode"] = "demo" if settings.DEMO_DATA_ENABLED else "live"
    catalog_identity = {
        key: base.get(key)
        for key in ("subject", "related_routes", "related_destinations", "points", "offsets", "timing_pending")
        if key in base
    }
    base["catalog_signature"] = sha256(
        json.dumps(catalog_identity, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return base


def has_usable_week_data(payload: dict) -> bool:
    """Require usable coverage before replacing the durable last-good bundle."""

    if payload.get("kind") == "point":
        days = (payload.get("intervals") or {}).get("1", [])
        return len(days) == 8 and all(
            sum(bool(row.get("weather_at")) for row in day) >= 18
            for day in days
        )
    if payload.get("kind") == "route":
        point_count = len(payload.get("points") or [])
        return point_count > 0 and bool(payload.get("records")) and any(
            len(plan.get("records", [])) == point_count
            and all(index is not None for index in plan.get("records", []))
            for plan in (payload.get("plans") or {}).values()
        )
    return False
