from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path


def root(_request):
    return JsonResponse(
        {
            "product": "هواچ",
            "name": "Hawatch",
            "api": "/api/v1/",
        }
    )


urlpatterns = [
    path("", root),
    path("admin/", admin.site.urls),
    path("api/v1/", include("hawatch.api.v1.urls")),
]
