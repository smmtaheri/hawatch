"""Google REP wildcard/longest-match checks without a catalog or database."""
import re

import pytest
from django.test import RequestFactory, override_settings

from hawatch.api.v1.views import robots_txt


def allowed(body, url):
    matches = []
    for line in body.splitlines():
        name, _, rule = line.partition(":")
        if name not in ("Allow", "Disallow"):
            continue
        rule = rule.strip()
        end = rule.endswith("$")
        pattern = re.escape(rule[:-1] if end else rule).replace(r"\*", ".*")
        if re.match(pattern + ("$" if end else ""), url):
            matches.append((len(rule.replace("*", "").rstrip("$")), name == "Allow"))
    return max(matches, default=(0, True))[1]


def body():
    response = robots_txt(RequestFactory().get("/robots.txt"))
    assert response.status_code == 200
    assert response["Content-Type"].startswith("text/plain")
    return response.content.decode()


@pytest.mark.parametrize("path", [
    "/api/v1/points/naz/forecast/day/", "/api/v1/points/tochal/forecast/day/?period=morning",
    "/api/v1/routes/tochal-darband/forecast/day/?date=2026-10-02&speed=medium",
    "/api/v1/points/point-new-999/forecast/", "/api/v1/routes/route-new-999/forecast/?period=night",
    "/api/v1/points/", "/api/v1/catalog-index/", "/api/v1/search/suggestions/?q=naz",
    "/api/v1/routes/?page=2", "/api/v1/destinations/?page=3",
    "/points/naz", "/routes/tochal-darband", "/assets/hawatch.js", "/favicon.png",
])
def test_public_rendering_resources_are_allowed(path):
    assert allowed(body(), path)


@pytest.mark.parametrize("path", [
    "/api/v1/auth/me/", "/api/v1/auth/login/", "/api/v1/auth/logout/", "/api/v1/auth/csrf/",
    "/api/v1/analytics/pageview/", "/api/v1/metrics/", "/api/v1/health/status/",
    "/api/v1/points/naz/", "/api/v1/routes/tochal-darband/", "/api/v1/unknown/",
    "/api/v1/points/naz/forecast/day/private/", "/api/v1/routes/private/forecast/day/admin/",
    "/api/v1/routes/private/forecast/day/extra?x=1", "/api/v1/routes/private/forecast/edit/",
    "/api/v1/catalog-index/admin/", "/api/v1/routes/admin/", "/admin/",
])
def test_private_and_unlisted_endpoints_stay_blocked(path):
    assert not allowed(body(), path)


def test_origin_and_sitemap_policy_are_unchanged():
    with override_settings(PUBLIC_SITE_ORIGIN="https://example.test"):
        assert "Sitemap: https://example.test/sitemap.xml" in body()
    assert "Disallow: /api/" in body()
    assert "Disallow: /admin/" in body()


@pytest.mark.parametrize("path", ["/robots.txt", "/api/v1/seo/robots.txt"])
@pytest.mark.parametrize("agent", ["Mozilla/5.0", "Googlebot", "Google-InspectionTool"])
def test_robots_policy_is_identical_and_not_cacheable(path, agent):
    from hashlib import sha256

    response = robots_txt(RequestFactory().get(path, HTTP_USER_AGENT=agent))
    assert response.content.decode() == body()
    assert response["Cache-Control"] == "no-store, no-cache, must-revalidate, max-age=0"
    assert response["Expires"] == "0"
    assert response["X-Hawatch-Robots-Version"] == sha256(response.content).hexdigest()[:16]


def test_robots_version_changes_with_policy_content():
    first = robots_txt(RequestFactory().get("/robots.txt"))
    with override_settings(PUBLIC_SITE_ORIGIN="https://example.test"):
        second = robots_txt(RequestFactory().get("/robots.txt"))
    assert first["X-Hawatch-Robots-Version"] != second["X-Hawatch-Robots-Version"]


@pytest.mark.parametrize("kind,path", [("point","/points/naz"),("route","/routes/tochal-darband")])
def test_server_article_and_metadata_exist_before_javascript(kind,path):
    from hawatch.modules.catalog.seo_pages import _render
    page = {"kind": kind, "title": "عنوان اختصاصی | هواچ", "headline": "آب‌وهوای نقطهٔ آزمایشی",
            "description": "شرح اختصاصی نقطه", "summary": "ارتفاع و منطقهٔ مقصد",
            "canonical": "https://hawatch.ir"+path, "forecast_summary": "پیش‌بینی ثبت‌شده",
            "routes": [{"href":"/routes/tochal-darband", "title":"مسیر مرتبط"}],
            "points": [{"href":"/points/naz", "name":"نقطهٔ مسیر"}]}
    response = _render(RequestFactory().get(path),page=page)
    html = response.content.decode()
    assert response.status_code == 200
    assert response["X-Robots-Tag"] == "index,follow"
    assert 'data-seo-initial="true"' in html and "<article>" in html
    assert "آب‌وهوای نقطهٔ آزمایشی" in html and "پیش‌بینی ثبت‌شده" in html
    assert f'rel="canonical" href="https://hawatch.ir{path}"' in html
    query_response = _render(RequestFactory().get(path, {"period":"morning"}),page=page)
    assert query_response["X-Robots-Tag"] == "noindex,follow"
    assert f'rel="canonical" href="https://hawatch.ir{path}"' in query_response.content.decode()
