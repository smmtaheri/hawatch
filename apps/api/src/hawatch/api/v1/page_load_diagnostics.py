"""Bounded failure reports for public page loading; no analytics or DB writes."""
import hashlib
import logging

from django.http import HttpResponse
from rest_framework import serializers
from rest_framework.decorators import api_view, authentication_classes, permission_classes, throttle_classes
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.throttling import SimpleRateThrottle

log = logging.getLogger("hawatch.observability")
ASSET_PATH = r"^/static-assets/[a-zA-Z0-9_-]{1,64}/[a-zA-Z0-9_./-]{1,180}\.(?:js|css)$"


class LoadFailureThrottle(SimpleRateThrottle):
    scope = "page_load_failure"
    rate = "30/min"

    def get_cache_key(self, request, view):
        ident = hashlib.sha256(self.get_ident(request).encode()).hexdigest()
        return self.cache_format % {"scope": self.scope, "ident": ident}


class LoadFailure(serializers.Serializer):
    path = serializers.RegexField(r"^/(?:$|(?:points|routes)/[a-z0-9-]+/?$|(?:destinations|routes)(?:/page/[1-9][0-9]*)?/?$|account/plans/?$|login/?$)", max_length=200)
    version = serializers.RegexField(r"^[a-zA-Z0-9_-]{1,64}$")
    reason = serializers.ChoiceField(choices=("timeout", "asset", "application"))
    elapsed_ms = serializers.IntegerField(min_value=0, max_value=3_600_000)
    app_ready = serializers.BooleanField()
    data_ready = serializers.BooleanField()
    initial_data = serializers.BooleanField()
    effective_type = serializers.ChoiceField(choices=("unknown", "slow-2g", "2g", "3g", "4g"))
    failed_assets = serializers.ListField(child=serializers.RegexField(ASSET_PATH), max_length=8)
    pending_assets = serializers.ListField(child=serializers.RegexField(ASSET_PATH), max_length=8)


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
@throttle_classes([LoadFailureThrottle])
def page_load_failure(request):
    if len(request.body) > 4096:
        raise ValidationError("گزارش بیش از حد بزرگ است.")
    report = LoadFailure(data=request.data)
    report.is_valid(raise_exception=True)
    log.warning("Public page loading incomplete", extra={
        "event": "web.page_load_incomplete", "page_load": report.validated_data,
    })
    response = HttpResponse(status=204)
    response["Cache-Control"] = "no-store"
    return response
