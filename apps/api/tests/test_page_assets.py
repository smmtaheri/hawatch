import json
import os
import subprocess
import shutil
import pytest
from pathlib import Path

from django.test import RequestFactory, override_settings

from hawatch.modules.catalog.page_assets import page_assets, validate_page_assets
from hawatch.modules.catalog.seo_pages import _render


def test_current_page_preloads_are_rendered_before_the_application_entry(tmp_path):
    directory = tmp_path / "static-assets" / "release1"
    directory.mkdir(parents=True)
    graph = {"scripts": ["assets/hawatch.js", "assets/chunks/point-123.js"], "styles": ["assets/hawatch.css", "assets/detail-123.css"]}
    (directory / "page-assets.json").write_text(json.dumps({"version": "release1", "pages": {"point": graph}}))
    with override_settings(HAWATCH_ASSET_VERSION="release1", HAWATCH_FRONTEND_ASSETS_ROOT=str(tmp_path)):
        response = _render(RequestFactory().get("/points/sample"), page={"kind":"point", "title":"آزمایش", "headline":"آزمایش", "canonical":"https://hawatch.ir/points/sample"})
    html = response.content.decode()
    assert 'rel="modulepreload" crossorigin href="/static-assets/release1/assets/chunks/point-123.js"' in html
    assert 'rel="preload" as="style" crossorigin href="/static-assets/release1/assets/detail-123.css"' in html
    assert html.index('rel="modulepreload"') < html.index('<script type="module"')
    assert html.count('rel="stylesheet"') == 1
    assert 'name="robots" content="index,follow"' in html
    assert 'rel="canonical" href="https://hawatch.ir/points/sample"' in html
    assert '__hawatchInitialPageRequest' in html
    assert "cache: /\\/forecast\\/week\\/$/.test(endpoint) ? 'no-cache' : 'default'" in html


def test_not_yet_published_manifest_is_not_cached(tmp_path):
    with override_settings(HAWATCH_ASSET_VERSION="new-release", HAWATCH_FRONTEND_ASSETS_ROOT=str(tmp_path)):
        assert page_assets("point") == {}
        directory = tmp_path / "static-assets" / "new-release"
        directory.mkdir(parents=True)
        (directory / "page-assets.json").write_text(json.dumps({"version":"new-release", "pages":{"point":{"scripts":["assets/point.js"],"styles":[]}}}))
        assert page_assets("point")["scripts"] == ["assets/point.js"]


def test_deployment_gate_checks_the_version_and_every_referenced_file(tmp_path):
    directory = tmp_path / "static-assets" / "release1"
    (directory / "assets").mkdir(parents=True)
    entry = directory / "assets/entry.js"
    entry.write_text("ready")
    kinds = ("home", "point", "route", "destinations", "routes", "login", "plans", "not-found")
    manifest = {"version":"release1", "pages":{kind:{"scripts":["assets/entry.js"],"styles":[]} for kind in kinds}}
    (directory / "page-assets.json").write_text(json.dumps(manifest))
    with override_settings(HAWATCH_ASSET_VERSION="release1", HAWATCH_FRONTEND_ASSETS_ROOT=str(tmp_path)):
        assert validate_page_assets() == 8
        entry.unlink()
        with pytest.raises(ValueError, match="Unpublished frontend asset"):
            validate_page_assets()
        manifest["version"] = "another-release"
        (directory / "page-assets.json").write_text(json.dumps(manifest))
        with pytest.raises(ValueError, match="does not match"):
            validate_page_assets()


def test_asset_publishing_retains_cached_releases_and_bounds_disk_usage(tmp_path):
    source = tmp_path / "build"
    destination = tmp_path / "published"
    script = Path(__file__).resolve().parents[3] / "apps/web/publish-assets.sh"
    for release in range(7):
        version = f"release{release}"
        bundle = source / "static-assets" / version
        (bundle / "assets").mkdir(parents=True)
        (bundle / "assets/entry.js").write_text(version)
        (bundle / "page-assets.json").write_text(json.dumps({"version":version}))
        public = source / "static-public" / version
        public.mkdir(parents=True)
        (public / "icon.svg").write_text(version)
        # Each web image contains only its own build, like production.
        env = {**os.environ, "HAWATCH_FRONTEND_BUILD_ROOT":str(source), "HAWATCH_FRONTEND_ASSETS_ROOT":str(destination)}
        subprocess.run(["sh",str(script)],env=env,check=True)
        shutil.rmtree(bundle)
        shutil.rmtree(public)
    assert {p.name for p in (destination / "static-assets").iterdir()} == {f"release{i}" for i in range(2,7)}
    assert {p.name for p in (destination / "static-public").iterdir()} == {"release5","release6"}
    assert (destination / "static-assets/release2/assets/entry.js").read_text() == "release2"
    assert json.loads((destination / "static-assets/release6/page-assets.json").read_text())["version"] == "release6"
