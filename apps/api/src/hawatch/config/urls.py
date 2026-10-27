import json
import re
from pathlib import Path

from django.conf import settings
from django.contrib import admin
from django.http import HttpResponsePermanentRedirect
from django.urls import include, path

from hawatch.api.v1.share_views import open_share
from hawatch.modules.catalog import seo_pages


def redirect_removed_catalog_index(_request):
    return HttpResponsePermanentRedirect(f"{settings.PUBLIC_SITE_ORIGIN}/")

PUBLIC_PAGE_MANIFEST = Path(__file__).with_name("public_pages.json")
with PUBLIC_PAGE_MANIFEST.open(encoding="utf-8") as manifest_file:
    PUBLIC_PAGES = json.load(manifest_file)

PUBLIC_PAGE_VIEWS = {
    "seo_home": seo_pages.seo_home,
    "seo_point": seo_pages.seo_point,
    "seo_destinations": seo_pages.seo_destinations,
    "seo_route": seo_pages.seo_route,
    "seo_routes": seo_pages.seo_routes,
    "redirect_removed_catalog_index": redirect_removed_catalog_index,
}


def _django_pattern(route: str) -> str:
    return re.sub(r"\{([a-z][a-z0-9_-]*):([a-z]+)\}", r"<\2:\1>", route).lstrip("/")


def _route_patterns(entry: dict, view) -> list:
    base = _django_pattern(entry["path"])
    variants = [base]
    if entry.get("trailing_slash") and base:
        variants.append(f"{base}/")
    return [
        path(pattern, view, name=entry["name"] if index == 0 else None)
        for index, pattern in enumerate(variants)
    ]


urlpatterns = [path("p/<str:code>", open_share)]

for public_page in PUBLIC_PAGES["pages"]:
    if public_page["owner"] == "api":
        urlpatterns.extend(_route_patterns(public_page, PUBLIC_PAGE_VIEWS[public_page["view"]]))

for redirect in PUBLIC_PAGES["redirects"]:
    urlpatterns.extend(_route_patterns(redirect, PUBLIC_PAGE_VIEWS[redirect["view"]]))

urlpatterns.extend([
    path("admin/", admin.site.urls),
    path("api/v1/", include("hawatch.api.v1.urls")),
])
