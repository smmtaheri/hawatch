#!/usr/bin/env python3
"""Normalize checked-in catalog fixtures to the canonical identity contract.

This is an offline maintenance helper.  GPX files remain local-only; this
script only rewrites JSON under ``apps/api/fixtures/catalog``.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from hawatch.modules.catalog.identity import (
    POINT_SLUG_MAP,
    ROUTE_SLUG_MAP,
    canonical_point_slug,
    metadata_for_point,
    normalize_identity_text,
)


ROOT = Path(__file__).resolve().parents[1]
CATALOG_DIR = ROOT / "apps" / "api" / "fixtures" / "catalog"
DESTINATION_SLUG_MAP = {"touchal": "tochal"}
DESTINATION_POINT_SLUGS = {
    "alamkuh_summit",
    "azadkouh_summit",
    "damavand_summit",
    "darabad_summit",
    "daryasar_plain",
    "dorfak_summit",
    "eskelim_waterfall",
    "gahar_lake",
    "hazar_summit",
    "sabalan_summit",
    "tar_lake",
    "tochal_summit",
    "zarrinkuh_summit",
}


def point_slug(old: str, row: dict) -> str:
    return canonical_point_slug(
        old,
        preserve_destination=old in DESTINATION_POINT_SLUGS or row.get("kind") == "destination",
    )


def remap_value(value, mapping):
    if isinstance(value, str):
        return mapping.get(value, value)
    if isinstance(value, list):
        return [remap_value(item, mapping) for item in value]
    if isinstance(value, dict):
        return {key: remap_value(item, mapping) for key, item in value.items()}
    return value


def normalize_file(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    destination = data["destination"]
    destination_slug = DESTINATION_SLUG_MAP.get(destination["slug"], destination["slug"])
    destination["slug"] = destination_slug

    old_rows = data["weather_points"]
    mapped_rows: dict[str, dict] = {}
    old_to_new: dict[str, str] = {}
    # Prefer the track waypoint row for known physical duplicates.
    preferred = {
        "hazar-ardikan-babzangi-junction": "hazar_babzangi_route_junction",
        "dorfak-jeyruni-spring": "dorfak_west_jeyruni_spring",
    }
    for old_slug, row in old_rows.items():
        new_slug = point_slug(old_slug, row)
        old_to_new[old_slug] = new_slug
        existing = mapped_rows.get(new_slug)
        if existing is None or preferred.get(new_slug) == old_slug:
            mapped_rows[new_slug] = dict(row)
        else:
            aliases = list(existing.get("aliases") or [])
            for alias in row.get("aliases") or []:
                if alias not in aliases:
                    aliases.append(alias)
            existing["aliases"] = aliases
    data["weather_points"] = mapped_rows
    destination_point = data.get("destination_weather_point")
    if destination_point:
        data["destination_weather_point"] = old_to_new.get(destination_point, destination_point)

    route_sources: dict[str, list[str]] = defaultdict(list)
    for route in (data.get("routes") or {}).values():
        for url in (route.get("timing") or {}).get("source_urls") or []:
            for old_slug in route.get("points") or []:
                route_sources[old_to_new.get(old_slug, old_slug)].append(url)

    for slug, row in mapped_rows.items():
        sources = []
        for url in route_sources.get(slug, []):
            if url not in sources:
                sources.append(url)
        if not sources:
            sources = ["https://open-meteo.com/en/docs"]
        identity = metadata_for_point(
            slug,
            row,
            destination_label=destination.get("name", destination_slug),
            source_urls=sources,
            is_destination=slug == data.get("destination_weather_point"),
        )
        row.update(identity)
        if slug == data.get("destination_weather_point"):
            row["kind"] = "destination"

    # Page names are the SEO-facing identity label. Keep them unique within a
    # catalog even when legacy rows used the same short phrase.
    used: dict[str, int] = {}
    for slug, row in mapped_rows.items():
        key = normalize_identity_text(row["page_name"])
        if key in used:
            used[key] += 1
            row["page_name"] = f"{row['page_name']} · {destination.get('tile_name', destination_slug)} · {used[key]}"
        else:
            used[key] = 1

    for route in (data.get("routes") or {}).values():
        route["slug"] = ROUTE_SLUG_MAP.get(route["slug"], route["slug"])
        route["destination_slug"] = DESTINATION_SLUG_MAP.get(route.get("destination_slug"), route.get("destination_slug"))
        route["points"] = [old_to_new.get(slug, slug) for slug in route.get("points") or []]
        route["public_point_notes"] = {
            old_to_new.get(slug, slug): note
            for slug, note in (route.get("public_point_notes") or {}).items()
        }
        timing = route.get("timing")
        if timing:
            for key in ("cumulative_minutes", "segment_minutes"):
                if isinstance(timing.get(key), dict):
                    timing[key] = {old_to_new.get(slug, slug): value for slug, value in timing[key].items()}
    if data.get("shared_weather_points"):
        data["shared_weather_points"] = [old_to_new.get(slug, slug) for slug in data["shared_weather_points"]]
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
            print(f"{path.name}: {len(data['weather_points'])} points, {len(data['routes'])} routes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
