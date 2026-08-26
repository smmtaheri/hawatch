from django.contrib import admin
from django.contrib.gis.admin import GISModelAdmin

from hawatch.modules.destinations.models import Destination


@admin.register(Destination)
class DestinationAdmin(GISModelAdmin):
    list_display = ("slug", "name", "region", "is_popular")
    prepopulated_fields = {"slug": ("name",)}
