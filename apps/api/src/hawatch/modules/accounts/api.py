from __future__ import annotations

from django.conf import settings
from django.contrib.auth import get_user_model, login, logout
from django.middleware.csrf import get_token
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from rest_framework.decorators import api_view
from rest_framework.exceptions import NotAuthenticated, ValidationError
from rest_framework.response import Response

from .models import AccountProfile
from .services import active_policy, effective_plan, resolve_forecast_access


def normalize_iran_phone(value: str) -> str:
    digits = "".join(
        char
        for char in value.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789"))
        if char.isdigit()
    )
    if digits.startswith("00"):
        digits = digits[2:]
    if digits.startswith("0"):
        digits = f"98{digits[1:]}"
    if len(digits) == 10 and digits.startswith("9"):
        digits = f"98{digits}"
    return digits


def _account_payload(request) -> dict:
    if not request.user.is_authenticated:
        raise NotAuthenticated("برای دیدن حساب وارد شوید.")
    policy = active_policy()
    plan = effective_plan(request, policy)
    access = resolve_forecast_access(request)
    return {
        "authenticated": True,
        "plan": {"code": plan.code, "title": plan.title, "tier": plan.tier} if plan else None,
        "forecast_access": access.payload(),
    }


@never_cache
@ensure_csrf_cookie
@api_view(["GET"])
def csrf(request):
    return Response({"csrf_token": get_token(request)})


@never_cache
@csrf_protect
@api_view(["POST"])
def demo_login(request):
    phone = normalize_iran_phone(str(request.data.get("phone", "")))
    code = str(request.data.get("code", "")).translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789"))
    allowed_phone = str(getattr(settings, "DEMO_AUTH_ALLOWED_PHONE", ""))
    allowed_code = str(getattr(settings, "DEMO_AUTH_FIXED_OTP", ""))
    if not allowed_phone or not allowed_code or phone != allowed_phone or code != allowed_code:
        raise ValidationError({"detail": "شماره یا کد ورود معتبر نیست."})

    User = get_user_model()
    user, _ = User.objects.get_or_create(username=f"phone:{phone}", defaults={"is_active": True})
    profile, _ = AccountProfile.objects.get_or_create(user=user, defaults={"phone_e164": phone})
    if profile.phone_e164 != phone:
        raise ValidationError({"detail": "حساب ورود معتبر نیست."})
    login(request, user)
    request.session.set_expiry(int(getattr(settings, "AUTH_SESSION_AGE_SECONDS", 30 * 24 * 60 * 60)))
    return Response(_account_payload(request))


@never_cache
@csrf_protect
@api_view(["POST"])
def session_logout(request):
    logout(request)
    return Response({"authenticated": False})


@never_cache
@api_view(["GET"])
def me(request):
    return Response(_account_payload(request))
