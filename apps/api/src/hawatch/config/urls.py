from django.conf import settings
from django.contrib import admin
from django.http import HttpResponsePermanentRedirect
from django.urls import include, path

from hawatch.modules.catalog import seo_pages


def redirect_removed_catalog_index(_request):
    return HttpResponsePermanentRedirect(f"{settings.PUBLIC_SITE_ORIGIN}/")

urlpatterns = [
    path("", seo_pages.seo_home, name="seo-home"),
    path("points", redirect_removed_catalog_index, name="removed-points-index"),
    path("points/", redirect_removed_catalog_index),
    path("points/<slug:slug>", seo_pages.seo_point, name="seo-point"),
    path("points/<slug:slug>/", seo_pages.seo_point),
    path("routes", redirect_removed_catalog_index, name="removed-routes-index"),
    path("routes/", redirect_removed_catalog_index),
    path("routes/<slug:slug>", seo_pages.seo_route, name="seo-route"),
    path("routes/<slug:slug>/", seo_pages.seo_route),
    path("admin/", admin.site.urls),
    path("api/v1/", include("hawatch.api.v1.urls")),
]
