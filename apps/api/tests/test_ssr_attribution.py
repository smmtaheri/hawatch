"""Database-free real-template gate, also run inside the candidate release image."""

import json
import re
from copy import deepcopy

import pytest
from django.test import RequestFactory

from hawatch.modules.catalog.seo_pages import _render


ATTRIBUTION = {
    "source": "Open-Meteo",
    "updated_at": "2026-10-28T12:01:00+03:30",
    "updated_label": "۶ آبان ۱۴۰۵، ۱۲:۰۱",
}
PAGES = [
    ("home", "/", 200),
    ("point", "/points/sample", 200),
    ("route", "/routes/sample", 200),
    ("destinations", "/destinations", 200),
    ("destinations", "/destinations/page/2", 200),
    ("routes", "/routes", 200),
    ("routes", "/routes/page/2", 200),
    ("not-found", "/points/missing", 404),
]


@pytest.fixture(autouse=True)
def isolated_assets(settings):
    settings.HAWATCH_FRONTEND_ASSETS_ROOT = ""
    settings.HAWATCH_QA_NOINDEX = False


def page_context(kind, path, status=200):
    return {
        "kind": kind,
        "title": "آب‌وهوای آزمایشی | هواچ",
        "description": "شرح آزمایشی",
        "headline": "آب‌وهوای آزمایشی",
        "canonical": f"https://hawatch.ir{path}" if status == 200 else "",
    }


@pytest.mark.parametrize("kind,path,status", PAGES)
@pytest.mark.parametrize("query", ["", "?audit=ssr"])
def test_every_page_renders_without_optional_forecast_data(kind, path, status, query):
    response = _render(RequestFactory().get(path + query), page=page_context(kind, path, status), status=status)
    html = response.content.decode()
    robots = "index,follow" if status == 200 and not query else "noindex,follow"
    assert response.status_code == status
    assert 'data-seo-initial="true"' in html
    assert html.count("<h1>") == 1
    assert response["X-Robots-Tag"] == robots
    assert f'name="robots" content="{robots}"' in html
    if status == 200:
        assert f'rel="canonical" href="https://hawatch.ir{path}"' in html
    else:
        assert 'rel="canonical"' not in html
    assert "آخرین به‌روزرسانی:" not in html
    assert "<time " not in html
    if query or status != 200:
        assert response["Cache-Control"] == "no-cache"


@pytest.mark.parametrize("kind", ["home", "point", "route"])
@pytest.mark.parametrize("attribution", [None, {}, ATTRIBUTION])
def test_footer_uses_same_attribution_as_embedded_payload(kind, attribution):
    page = page_context(kind, f"/{kind}/sample")
    payload = {"attribution": attribution, "subject": {"name": "آزمایش"}}
    if kind == "home":
        page["initial_data"] = payload
        script_id = "home-initial-data"
    else:
        page["initial_forecast"] = {"payload": payload, "rendered_at": ATTRIBUTION["updated_at"]}
        script_id = "forecast-initial-data"
    original = deepcopy(page)
    response = _render(RequestFactory().get("/"), page=page)
    html = response.content.decode()
    embedded = json.loads(re.search(rf'<script id="{script_id}" type="application/json">(.*?)</script>', html).group(1))
    assert (embedded if kind == "home" else embedded["payload"]) == payload
    assert page == original
    assert response.status_code == 200
    if attribution:
        assert "دادهٔ هواشناسی: Open-Meteo" in html
        assert f'<time datetime="{ATTRIBUTION["updated_at"]}">{ATTRIBUTION["updated_label"]}</time>' in html
    else:
        assert "<time " not in html


@pytest.mark.parametrize("initial", [None, {}, {"payload": None}, {"payload": {}}, {"payload": {"attribution": None}}])
def test_empty_forecast_envelope_does_not_break_page(initial):
    page = page_context("point", "/points/sample")
    page["initial_forecast"] = initial
    assert _render(RequestFactory().get("/points/sample"), page=page).status_code == 200


def test_footer_escapes_provider_and_never_invents_update_time():
    page = page_context("point", "/points/sample")
    page["initial_forecast"] = {"payload": {"attribution": {
        "source": '<script>alert("provider")</script>',
        "updated_at": None,
        "updated_label": "زمان بدون سند",
    }}}
    html = _render(RequestFactory().get("/points/sample"), page=page).content.decode()
    assert "<script>alert(" not in html
    assert "&lt;script&gt;" in html
    assert "<time " not in html
