"""Read the current frontend build's preload graph from the shared asset volume."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from django.conf import settings


@lru_cache(maxsize=2)
def _read_manifest(path: str, modified: int) -> dict:
    return json.loads(Path(path).read_text())


def page_assets(kind: str) -> dict[str, list[str]]:
    root = getattr(settings, "HAWATCH_FRONTEND_ASSETS_ROOT", "")
    version = settings.HAWATCH_ASSET_VERSION
    if not root or not version:
        return {}
    path = Path(root) / "static-assets" / version / "page-assets.json"
    try:
        manifest = _read_manifest(str(path), path.stat().st_mtime_ns)
    except FileNotFoundError:
        # Optional preload hints; API can start before the web image is published.
        # A missing file is not cached, so the next document sees the new graph.
        return {}
    if manifest["version"] != version:
        raise ValueError("Frontend asset manifest does not match the HTML release")
    return manifest["pages"].get(kind, {})


def validate_page_assets() -> int:
    """Deployment gate: the graph and every referenced file must be published."""
    root = Path(settings.HAWATCH_FRONTEND_ASSETS_ROOT) / "static-assets" / settings.HAWATCH_ASSET_VERSION
    manifest = _read_manifest(str(root / "page-assets.json"), (root / "page-assets.json").stat().st_mtime_ns)
    if manifest["version"] != settings.HAWATCH_ASSET_VERSION:
        raise ValueError("Frontend asset manifest does not match the HTML release")
    pages = manifest["pages"]
    for kind in ("home", "point", "route", "destinations", "routes", "login", "plans", "not-found"):
        assets = pages[kind]
        if not assets["scripts"]:
            raise ValueError(f"Missing frontend entry for {kind}")
        for file in assets["scripts"] + assets["styles"]:
            if not (root / file).is_file():
                raise ValueError(f"Unpublished frontend asset: {file}")
    return len(pages)
