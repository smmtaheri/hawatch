from django.urls import path

from hawatch.api.v1 import views

urlpatterns = [
    path("metrics/", views.metrics_view),
    path("health/live/", views.health_live),
    path("health/ready/", views.health_ready),
    path("health/status/", views.health_status),
    path("points/", views.points_list),
    path("points/<slug:slug>/", views.point_detail),
    path("routes/<slug:slug>/", views.route_detail),
    path("routes/<slug:slug>/forecast/", views.route_forecast_view),
    path("points/<slug:slug>/forecast/", views.point_forecast_view),
    path("search/suggestions/", views.search_suggestions_view),
    path("seo/robots.txt", views.robots_txt),
    path("seo/sitemap.xml", views.sitemap_xml),
]
