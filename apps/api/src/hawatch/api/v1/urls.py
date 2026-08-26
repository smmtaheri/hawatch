from django.urls import path

from hawatch.api.v1 import views

urlpatterns = [
    path("health/live/", views.health_live),
    path("health/ready/", views.health_ready),
    path("destinations/", views.destinations_list),
    path("destinations/<slug:slug>/", views.destination_detail),
    path("destinations/<slug:slug>/forecast/", views.destination_forecast_view),
    path("routes/<slug:slug>/", views.route_detail),
    path("routes/<slug:slug>/forecast/", views.route_forecast_view),
]
