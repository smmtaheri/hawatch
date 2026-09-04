#!/usr/bin/env python3
"""Normalize checked-in catalog fixtures to the point/route identity contract.

This offline helper only rewrites catalog JSON.  It never creates points or
routes and it never reads, copies, or publishes GPX files.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from hawatch.modules.catalog.identity import (
    ROUTE_SLUG_MAP,
    canonical_point_slug,
    metadata_for_point,
    normalize_identity_text,
)


ROOT = Path(__file__).resolve().parents[1]
CATALOG_DIR = ROOT / "apps" / "api" / "fixtures" / "catalog"


def remap_point_slug(slug: str) -> str:
    return canonical_point_slug(str(slug))


def normalize_file(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    profile = dict(data.get("point") or {})
    old_rows = data.get("weather_points") or {}
    old_to_new: dict[str, str] = {}
    mapped_rows: dict[str, dict] = {}

    # Canonical identity mappings deliberately collapse known physical
    # duplicates (for example the two historical Hazar/Dorfak junction rows).
    preferred = {
        "hazar-ardikan-babzangi-junction": "hazar-babzangi-route-junction",
        "dorfak-jeyruni-spring": "dorfak-west-jeyruni-spring",
    }
    for old_slug, raw_row in old_rows.items():
        row = dict(raw_row)
        new_slug = remap_point_slug(old_slug)
        old_to_new[old_slug] = new_slug
        existing = mapped_rows.get(new_slug)
        if existing is None or preferred.get(new_slug) == old_slug:
            mapped_rows[new_slug] = row
            continue
        aliases = list(existing.get("aliases") or [])
        for alias in row.get("aliases") or []:
            if alias not in aliases:
                aliases.append(alias)
        existing["aliases"] = aliases

    primary_old = data.get("primary_point")
    if not primary_old:
        primary_old = profile.get("slug")
    primary_slug = old_to_new.get(primary_old, remap_point_slug(primary_old or ""))

    profile["slug"] = primary_slug
    data["point"] = profile
    data["primary_point"] = primary_slug
    data["weather_points"] = mapped_rows

    route_sources: dict[str, list[str]] = defaultdict(list)
    for route in (data.get("routes") or {}).values():
        for url in (route.get("timing") or {}).get("source_urls") or []:
            for old_slug in route.get("points") or []:
                route_sources[old_to_new.get(old_slug, remap_point_slug(old_slug))].append(url)

    for slug, row in mapped_rows.items():
        sources = list(dict.fromkeys(route_sources.get(slug, [])))
        identity = metadata_for_point(
            slug,
            row,
            primary_label=str(profile.get("name") or profile.get("tile_name") or primary_slug),
            source_urls=sources or ["https://open-meteo.com/en/docs"],
            is_primary=slug == primary_slug,
        )
        row.update(identity)
        if slug == primary_slug:
            row["kind"] = "primary"

    used: dict[str, int] = {}
    for row in mapped_rows.values():
        key = normalize_identity_text(str(row.get("page_name") or row.get("name") or ""))
        if key in used:
            used[key] += 1
            row["page_name"] = f"{row.get('page_name') or row.get('name')} · {profile.get('tile_name') or primary_slug} · {used[key]}"
        else:
            used[key] = 1

    for route in (data.get("routes") or {}).values():
        route["slug"] = ROUTE_SLUG_MAP.get(route.get("slug"), route.get("slug"))
        route["points"] = [old_to_new.get(slug, remap_point_slug(slug)) for slug in route.get("points") or []]
        route["public_point_notes"] = {
            old_to_new.get(slug, remap_point_slug(slug)): note
            for slug, note in (route.get("public_point_notes") or {}).items()
        }
        timing = route.get("timing") or {}
        for key in ("cumulative_minutes", "segment_minutes"):
            if isinstance(timing.get(key), dict):
                timing[key] = {
                    old_to_new.get(slug, remap_point_slug(slug)): value
                    for slug, value in timing[key].items()
                }
    if data.get("shared_weather_points"):
        data["shared_weather_points"] = [
            old_to_new.get(slug, remap_point_slug(slug))
            for slug in data["shared_weather_points"]
        ]
    return data


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="rewrite files; default is a dry-run")
    args = parser.parse_args()
    for path in sorted(CATALOG_DIR.glob("*.json")):
        data = normalize_file(path)
        payload = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
        if args.write:
            path.write_text(payload, encoding="utf-8")
        else:
            print(f"{path.name}: {len(data['weather_points'])} points, {len(data.get('routes') or {})} routes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
