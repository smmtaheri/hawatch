from django.urls import path
from .week_views import week_forecast, week_visit
from .share_views import create_share

from hawatch.api.v1 import views
from hawatch.modules.analytics.api import page_view_event
from hawatch.modules.accounts import api as account_api

urlpatterns = [
    path("shares/", create_share),
    path("points/<slug:slug>/forecast/visit/", week_visit, {"kind": "point"}),
    path("routes/<slug:slug>/forecast/visit/", week_visit, {"kind": "route"}),
    path("points/<slug:slug>/forecast/week/", week_forecast, {"kind": "point"}),
    path("routes/<slug:slug>/forecast/week/", week_forecast, {"kind": "route"}),
    path("metrics/", views.metrics_view),
    path("health/live/", views.health_live),
    path("health/ready/", views.health_ready),
    path("health/status/", views.health_status),
    path("points/", views.points_list),
    path("destinations/", views.destinations_index),
    path("routes/", views.routes_index),
    path("catalog-index/", views.catalog_index),
    path("catalog/search-index/", views.search_index_view),
    path("points/<slug:slug>/", views.point_detail),
    path("routes/<slug:slug>/", views.route_detail),
    path("routes/<slug:slug>/forecast/", views.route_forecast_view),
    path("points/<slug:slug>/forecast/", views.point_forecast_view),
    path("points/<slug:slug>/forecast/day/", views.point_day_forecast_view),
    path("routes/<slug:slug>/forecast/day/", views.route_day_forecast_view),
    path("search/suggestions/", views.search_suggestions_view),
    path("analytics/pageview/", page_view_event),
    path("auth/csrf/", account_api.csrf),
    path("auth/login/", account_api.demo_login),
    path("auth/logout/", account_api.session_logout),
    path("auth/me/", account_api.me),
    path("auth/plans/", account_api.plans),
    path("seo/robots.txt", views.robots_txt),
    path("seo/sitemap.xml", views.sitemap_xml),
]
