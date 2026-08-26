from django.contrib import admin
from django.contrib.gis.admin import GISModelAdmin

from hawatch.modules.routes.models import Route, RoutePoint


class RoutePointInline(admin.TabularInline):
    model = RoutePoint
    extra = 0


@admin.register(Route)
class RouteAdmin(GISModelAdmin):
    list_display = ("slug", "title", "destination", "featured")
    inlines = [RoutePointInline]


@admin.register(RoutePoint)
class RoutePointAdmin(GISModelAdmin):
    list_display = ("slug", "name", "route", "sort_order")
