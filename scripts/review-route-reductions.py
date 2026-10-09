#!/usr/bin/env python3
"""Offline review of missing reductions on registered one-way route chains.

Read a public route snapshot, canonical catalog evidence and local GPX only.
Never writes a database, fetches weather, changes timestamps or edits tracks.
Original derive-route-descent.py remains the reproducible legacy baseline.
"""

import argparse, json, sys, hashlib, math
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyze_route_tracks import (
    parse_gpx_track,
    haversine_m,
    cut_at_first_summit_approach,
    robust_smoothed_ascent_m,
)


def review(source_root, registered_routes, catalog_root=None):
    root = source_root.resolve()
    rows = registered_routes
    owners = {}
    for file in sorted(
        (catalog_root or root / "apps/api/fixtures/catalog").glob("*.json")
    ):
        document = json.loads(file.read_text())
        for route in document.get("routes", {}).values():
            owners[route["slug"]] = (
                str(file),
                document.get("point", {}).get("slug"),
                route,
            )
    tracks = []
    for manifest in sorted((root / "tracks").rglob("*manifest.json")):
        doc = json.loads(manifest.read_text())
        for t in doc.get("tracks", []):
            filename = t.get("filename") or t.get("file")
            if not filename:
                continue
            path = (manifest.parent / filename).resolve()
            rec = (path, t, manifest, doc)
            tracks.append(rec)
    cache = {}
    accepted = []
    diagnostics = []
    allcandidates = {}
    for r in rows:
        if r["descent_m"] is not None:
            continue
        slug = r["slug"]
        if slug not in owners:
            diagnostics.append(
                {
                    "slug": slug,
                    "reason": "registered route has no canonical catalog evidence",
                }
            )
            continue
        owner = owners[slug][2]
        timing = owner.get("timing") or {}
        urls = set(
            r["timing_source_urls"]
            + owner.get("source_urls", [])
            + timing.get("source_urls", [])
        )
        paths = owner.get("evidence_tracks", []) + timing.get("evidence_tracks", [])
        candidates = []
        seen = set()
        for path, t, manifest, doc in tracks:
            u = t.get("wikiloc_url") or t.get("source_url") or t.get("source")
            direct = (t.get("route_slug") or t.get("route")) == slug
            section = slug in t.get("route_sections", {})
            linked = (
                u in urls
                and bool(u)
                and "wikiloc.com" in u
                and not u.endswith("wikiloc.com/")
            )
            filelinked = str(path.relative_to(root)) in paths
            if direct or section or linked or filelinked:
                candidates.append((path, t, manifest, doc))
                seen.add(path)
        for rel in paths:
            p = (root / rel).resolve()
            if p not in seen:
                candidates.append((p, {"role": "catalog-evidence"}, None, {}))
                seen.add(p)
        allcandidates[slug] = [str(p.relative_to(root)) for p, _, _, _ in candidates]
        passing = []
        for path, t, manifest, doc in candidates:
            try:
                if not path.is_relative_to(root / "tracks"):
                    raise ValueError("evidence path outside local tracks")
                role = str(t.get("role", "")).lower()
                coverage = str(t.get("coverage", "")).lower()
                source_role = str(t.get("source_role", "")).lower()
                if (
                    t.get("public_route_eligible") is False
                    or role
                    in (
                        "crosscheck",
                        "rejected",
                        "reference",
                        "reference_only",
                        "identity-evidence",
                    )
                    or any(
                        s in coverage
                        for s in (
                            "partial",
                            "crosscheck",
                            "composite",
                            "technical",
                            "glacier",
                            "multiple_approaches",
                        )
                    )
                    or any(
                        s in source_role
                        for s in (
                            "reference_only",
                            "review_only",
                            "not_eligible",
                            "not_a_public",
                            "not_used_for",
                            "not_route_metrics",
                        )
                    )
                ):
                    raise ValueError(
                        "reference/partial/technical evidence; not a reviewed route profile"
                    )
                if "back-country-skiing" in str(t.get("wikiloc_url", "")):
                    raise ValueError("ski activity; not hiking profile")
                content = path.read_bytes()
                sha = hashlib.sha256(content).hexdigest()
                if t.get("sha256") and t["sha256"] != sha:
                    raise ValueError("source hash changed")
                if path not in cache:
                    cache[path] = parse_gpx_track(path)
                raw = cache[path]
                original_count = len(raw)
                direction = "forward"
                bounds = None
                section = t.get("route_sections", {}).get(slug)
                route_spec = next(
                    (
                        v
                        for v in doc.get("routes", [])
                        if isinstance(v, dict) and v.get("slug") == slug
                    ),
                    None,
                )
                if section:
                    indices = section["indices"]
                    if len(indices) != len(r["points"]) or any(
                        not isinstance(i, int)
                        or isinstance(i, bool)
                        or i < 0
                        or i >= len(raw)
                        for i in indices
                    ):
                        raise ValueError("invalid reviewed section indices")
                    reverse = section.get("direction") == "reverse"
                    if any(
                        (b >= a if reverse else b <= a)
                        for a, b in zip(indices, indices[1:])
                    ):
                        raise ValueError("reviewed section direction inconsistent")
                    lo = min(indices)
                    hi = max(indices)
                    raw = raw[lo : hi + 1]
                    bounds = [lo, hi]
                    if section.get("direction") == "reverse":
                        raw = list(reversed(raw))
                        direction = "reverse"
                elif route_spec and route_spec.get("reverse"):
                    raw = list(reversed(raw))
                    direction = "reverse"
                elif t.get("direction") == "reverse":
                    raw = list(reversed(raw))
                    direction = "reverse"
                coords = [(p["latitude"], p["longitude"]) for p in r["points"]]
                if len(coords) < 3:
                    raise ValueError("registered chain incomplete")
                cut, meta = cut_at_first_summit_approach(raw, coords[-1])
                if meta["min_summit_distance_m"] > 100:
                    raise ValueError(
                        f"target gap {meta['min_summit_distance_m']:.0f}m >100m"
                    )
                start = min(
                    range(len(cut)),
                    key=lambda i: haversine_m(
                        (cut[i]["lat"], cut[i]["lon"]), coords[0]
                    ),
                )
                gap = haversine_m((cut[start]["lat"], cut[start]["lon"]), coords[0])
                if gap > 100:
                    raise ValueError(f"origin gap {gap:.0f}m >100m")
                cut = cut[start:]
                if len(cut) < 10 or any(
                    p["ele"] is None or not math.isfinite(p["ele"]) for p in cut
                ):
                    raise ValueError("elevation/geometry incomplete")
                steps = [
                    haversine_m((a["lat"], a["lon"]), (b["lat"], b["lon"]))
                    for a, b in zip(cut, cut[1:])
                ]
                maxgap = max(steps)
                if maxgap > 300:
                    raise ValueError(f"geometry gap {maxgap:.0f}m >300m")
                last = 0
                indices = [0]
                gaps = [round(gap, 1)]
                for coord in coords[1:-1]:
                    nearest = min(
                        range(last, len(cut)),
                        key=lambda i: haversine_m(
                            (cut[i]["lat"], cut[i]["lon"]), coord
                        ),
                    )
                    g = haversine_m((cut[nearest]["lat"], cut[nearest]["lon"]), coord)
                    if g > 500:
                        raise ValueError(f"landmark gap {g:.0f}m >500m")
                    if nearest <= last:
                        raise ValueError(
                            "registered landmarks do not progress along track"
                        )
                    last = nearest
                    indices.append(nearest)
                    gaps.append(round(g, 1))
                indices.append(len(cut) - 1)
                gaps.append(meta["cut_summit_distance_m"])
                along = [0.0]
                for s in steps:
                    along.append(along[-1] + s)
                if indices[-1] <= indices[-2]:
                    raise ValueError("target does not follow landmarks")
                distance = along[-1] / 1000
                registered = float(r["distance_km"])
                if abs(distance - registered) > max(0.5, registered * 0.25):
                    raise ValueError(
                        f"profile distance {distance:.2f}km differs from registered {registered:.2f}km"
                    )
                measures = robust_smoothed_ascent_m(cut)
                descent = round(
                    measures["robust_smoothed_ascent_m"]
                    - measures["net_elevation_change_m"]
                )
                if descent < 0:
                    raise ValueError("negative reduction")
                item = {
                    "slug": slug,
                    "descent_m": descent,
                    "chain": [p["slug"] for p in r["points"]],
                    "evidence": {
                        "method": "gpx-50m-5sample-v1",
                        "source_sha256": sha,
                        "source_url": t.get("wikiloc_url")
                        or t.get("source_url")
                        or t.get("source"),
                        "coverage": "canonical-origin-to-first-target",
                        "reference_only_elevation": True,
                        "catalog_source_urls": sorted(urls),
                        "direction": direction,
                        "analysis_distance_km": round(distance, 3),
                        "analysis_ascent_m": round(
                            measures["robust_smoothed_ascent_m"]
                        ),
                        "origin_gap_m": round(gap, 1),
                        "target_gap_m": meta["cut_summit_distance_m"],
                        "landmark_gaps_m": gaps,
                        "max_step_m": round(maxgap, 1),
                    },
                    "cumulative_distance_m": [round(along[i]) for i in indices],
                }
                if bounds:
                    item["evidence"]["reviewed_source_section"] = bounds
                item["_file"] = str(path.relative_to(root))
                item["_metadata"] = t
                item["_cut"] = {
                    "start": start,
                    "target": meta["cut_index"],
                    "count": len(cut),
                    "original_count": original_count,
                }
                priority = (
                    0
                    if role == "primary"
                    or t.get("status") == "reviewed"
                    or "primary" in source_role
                    else 1
                )
                passing.append((priority, item))
            except (ValueError, TypeError, KeyError, OSError) as e:
                diagnostics.append(
                    {
                        "slug": slug,
                        "file": str(path.relative_to(root)),
                        "reason": str(e),
                    }
                )
        if not candidates:
            diagnostics.append(
                {"slug": slug, "reason": "no catalog/manifest-linked GPX identified"}
            )
        if passing:
            best = [
                i for priority, i in passing if priority == min(p for p, _ in passing)
            ]
            if len(best) > 1 and max(i["descent_m"] for i in best) - min(
                i["descent_m"] for i in best
            ) > max(50, min(i["descent_m"] for i in best) * 0.3):
                diagnostics.append(
                    {
                        "slug": slug,
                        "reason": "conflicting independent reduction profiles",
                        "values": [i["descent_m"] for i in best],
                    }
                )
            else:
                accepted.append(best[0])
    result = {
        "schema_version": "route-descent-1",
        "routes": accepted,
        "unresolved": [
            r["slug"]
            for r in rows
            if r["descent_m"] is None and r["slug"] not in {i["slug"] for i in accepted}
        ],
        "diagnostics": diagnostics,
        "candidates": allcandidates,
    }
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument(
        "--registered-routes",
        type=Path,
        required=True,
        help="Read-only snapshot of actual active routes and ordered point coordinates",
    )
    parser.add_argument("--catalog-root", type=Path)
    args = parser.parse_args()
    print(
        json.dumps(
            review(
                args.source_root,
                json.loads(args.registered_routes.read_text()),
                args.catalog_root,
            ),
            ensure_ascii=False,
            indent=2,
        )
    )
