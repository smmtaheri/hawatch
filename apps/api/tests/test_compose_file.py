from pathlib import Path

import pytest


def _find_compose_file() -> Path | None:
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "infra" / "compose" / "compose.yaml"
        if candidate.exists():
            return candidate
    extra = Path("/workspace/infra/compose/compose.yaml")
    return extra if extra.exists() else None


def test_compose_default_services_and_pinned_postgis():
    compose = _find_compose_file()
    if compose is None:
        pytest.skip("compose.yaml is not available in this test environment")
    text = compose.read_text(encoding="utf-8")
    assert "postgres:" in text
    assert "api:" in text
    assert "web:" in text
    assert "nginx:" in text
    assert "postgis/postgis:16-3.5" in text
    assert "image: postgis/postgis:latest" not in text
    # Redis is a default runtime dependency and must not be hidden behind a profile.
    assert "redis:\n    image: redis:7.4.2" in text
    assert 'profiles: ["cache"]' not in text
    assert "kafka" not in text.lower()
    assert "../../.env.example" not in text
    assert "env_file:" in text
    assert "../../.env" in text
    assert "OPEN_METEO_BASE_URL" in text
    assert "FORECAST_STALE_AFTER_HOURS" in text
    assert 'profiles: ["observability"]' in text
    assert "LIVE_INGEST_INTERVAL_SECONDS" not in text
    assert "run --rm ingest" not in text


def test_web_gateway_returns_real_404_for_unknown_spa_paths():
    config = _find_web_nginx_file()
    if config is None:
        pytest.skip("apps/web/nginx.conf is not mounted in this API-only test container")
    text = config.read_text(encoding="utf-8")

    assert "include /etc/nginx/public-pages.inc;" in text
    assert "error_page 404 =404 @spa_not_found;" in text
    assert "try_files $uri =404;" in text


def test_web_gateway_serves_subscription_plans_for_direct_requests():
    config = _find_web_nginx_file()
    if config is None:
        pytest.skip("apps/web/nginx.conf is not mounted in this API-only test container")
    text = config.read_text(encoding="utf-8")
    root = config.parents[2]
    generated = (root / "apps" / "web" / "nginx-public-pages.inc").read_text(encoding="utf-8")

    # BrowserRouter needs the page shell for direct requests. Both slash forms
    # and the existing shared-cache policy come from the route manifest.
    assert "include /etc/nginx/public-pages.inc;" in text
    assert "location = /account/plans {" in generated
    assert "location = /account/plans/ {" in generated
    assert "try_files /plans.html =404;" in generated
    assert "s-maxage=300" in generated


def test_web_gateway_proxies_destination_pagination_to_ssr():
    config = _find_web_nginx_file()
    if config is None:
        pytest.skip("apps/web/nginx.conf is not mounted in this API-only test container")
    text = config.read_text(encoding="utf-8")
    root = config.parents[2]
    generated = (root / "apps" / "web" / "nginx-public-pages.inc").read_text(encoding="utf-8")
    routes = (root / "apps" / "web" / "src" / "app" / "publicPageRoutes.generated.ts").read_text(encoding="utf-8")

    # One manifest generates Django, React and both proxy route tables. Check
    # both listing pagination families so a newly added page cannot silently
    # fall through to the static SPA handler.
    assert "include /etc/nginx/public-pages.inc;" in text
    assert "destinations/page/[0-9]+" in generated
    assert "routes/page/[0-9]+" in generated
    assert '"/destinations/page/:page"' in routes
    assert '"/routes/page/:page"' in routes


def _find_web_nginx_file() -> Path | None:
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "apps" / "web" / "nginx.conf"
        if candidate.exists():
            return candidate
    extra = Path("/workspace/apps/web/nginx.conf")
    return extra if extra.exists() else None
