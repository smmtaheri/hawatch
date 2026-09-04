from django.contrib import admin
from django.urls import include, path

from hawatch.modules.catalog import seo_pages

urlpatterns = [
    path("", seo_pages.seo_home, name="seo-home"),
    path("points/<slug:slug>", seo_pages.seo_point, name="seo-point"),
    path("points/<slug:slug>/", seo_pages.seo_point),
    path("routes/<slug:slug>", seo_pages.seo_route, name="seo-route"),
    path("routes/<slug:slug>/", seo_pages.seo_route),
    path("admin/", admin.site.urls),
    path("api/v1/", include("hawatch.api.v1.urls")),
]
