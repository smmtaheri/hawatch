from __future__ import annotations

import hashlib
import hmac
import re

from django.conf import settings
from django.core.cache import cache
from django.db import IntegrityError, transaction
from rest_framework.decorators import api_view
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response

from hawatch.modules.forecasts.models import WeatherPoint
from hawatch.modules.routes.models import Route

from .models import PageViewEvent


_TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]{16,128}$")
_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_BOT_RE = re.compile(
    r"bot|crawler|spider|slurp|bingpreview|headless|facebookexternalhit|uptimerobot|curl|wget|healthcheck",
    re.IGNORECASE,
)
_MAX_BODY_BYTES = 2048
_DEFAULT_RATE_LIMIT = 60


def _visitor_digest(visitor_id: str) -> str:
    secret = str(settings.SECRET_KEY).encode("utf-8")
    return hmac.new(secret, visitor_id.encode("utf-8"), hashlib.sha256).hexdigest()


def _valid_page(page_type: str, slug: str) -> bool:
    if page_type == PageViewEvent.PageType.POINT:
        return WeatherPoint.objects.filter(slug=slug, is_active=True).exists()
    return Route.objects.filter(slug=slug, is_active=True).exists()


def _rate_limited(visitor_hash: str) -> bool:
    limit = int(getattr(settings, "ANALYTICS_RATE_LIMIT_PER_MINUTE", _DEFAULT_RATE_LIMIT))
    key = f"hawatch:analytics:rate:{visitor_hash}"
    try:
        if cache.add(key, 1, timeout=60):
            return False
        return int(cache.incr(key)) > limit
    except Exception:
        # A cache backend without atomic increment must not make page loads fail.
        return False


@api_view(["POST"])
def page_view_event(request):
    """Accept one idempotent, privacy-preserving public page navigation."""

    content_length = request.META.get("CONTENT_LENGTH")
    try:
        too_large = content_length and int(content_length) > _MAX_BODY_BYTES
    except (TypeError, ValueError):
        too_large = True
    if too_large:
        raise ValidationError("بدنهٔ درخواست بیش از حد بزرگ است.")

    django_user = getattr(getattr(request, "_request", None), "user", None)
    if getattr(request.user, "is_staff", False) or getattr(django_user, "is_staff", False):
        return Response({"accepted": False, "ignored": "staff"})
    if _BOT_RE.search(request.META.get("HTTP_USER_AGENT", "")):
        return Response({"accepted": False, "ignored": "bot"})

    payload = request.data
    if not isinstance(payload, dict):
        raise ValidationError("بدنهٔ درخواست نامعتبر است.")
    page_type = payload.get("page_type")
    slug = payload.get("slug")
    visitor_id = payload.get("visitor_id")
    navigation_id = payload.get("navigation_id")
    if page_type not in {PageViewEvent.PageType.POINT, PageViewEvent.PageType.ROUTE}:
        raise ValidationError("نوع صفحه نامعتبر است.")
    if not isinstance(slug, str) or not _SLUG_RE.fullmatch(slug):
        raise ValidationError("شناسهٔ صفحه نامعتبر است.")
    if not isinstance(visitor_id, str) or not _TOKEN_RE.fullmatch(visitor_id):
        raise ValidationError("شناسهٔ بازدیدکننده نامعتبر است.")
    if not isinstance(navigation_id, str) or not _TOKEN_RE.fullmatch(navigation_id):
        raise ValidationError("شناسهٔ پیمایش نامعتبر است.")
    if not _valid_page(page_type, slug):
        raise NotFound("این صفحه وجود ندارد.")

    visitor_hash = _visitor_digest(visitor_id)
    if _rate_limited(visitor_hash):
        return Response({"accepted": False, "rate_limited": True}, status=429)
    try:
        with transaction.atomic():
            PageViewEvent.objects.create(
                page_type=page_type,
                page_slug=slug,
                visitor_hash=visitor_hash,
                navigation_id=navigation_id,
            )
    except IntegrityError:
        return Response({"accepted": False, "duplicate": True})
    return Response({"accepted": True}, status=201)
