from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta

from django.db.models import Q
from django.conf import settings

from hawatch.common.time import day_window, now_tehran

from .models import AccountProfile, ForecastAccessPolicy, ForecastPlan, Membership


@dataclass(frozen=True)
class ForecastAccess:
    viewer: str
    plan: ForecastPlan | None
    display_days: int
    visible_days_from_yesterday: int
    available_through: date
    member_available_through: date
    today: date
    expires_at: datetime | None = None

    @property
    def is_authenticated(self) -> bool:
        return self.viewer == "member"

    def status_for(self, selected: date) -> str:
        if selected <= self.available_through:
            return "available"
        # A guest always gets the login CTA first. Once authenticated, the
        # same date is evaluated against the member's plan and can become a
        # subscription CTA. This keeps the flow unambiguous for visitors.
        if not self.is_authenticated:
            return "login_required"
        return "plan_required"

    def payload(self) -> dict:
        return {
            "viewer": self.viewer,
            "plan_title": self.plan.title if self.plan else None,
            "display_day_count": self.display_days,
            "visible_days_from_yesterday": self.visible_days_from_yesterday,
            "available_through": self.available_through.isoformat(),
        }


def active_policy() -> ForecastAccessPolicy:
    # Migration creates this row. The fallback protects a restored legacy DB.
    policy = ForecastAccessPolicy.objects.select_related("default_authenticated_plan").filter(singleton=1).first()
    if policy is not None:
        return policy
    plan, _ = ForecastPlan.objects.get_or_create(
        code="free", defaults={"title": "عضویت رایگان", "tier": ForecastPlan.Tier.FREE, "visible_days_from_yesterday": 2}
    )
    return ForecastAccessPolicy.objects.create(default_authenticated_plan=plan)


def effective_membership(request) -> Membership | None:
    if not getattr(request.user, "is_authenticated", False):
        return None
    now = now_tehran()
    return (
        Membership.objects.select_related("plan")
        .filter(profile__user=request.user, is_active=True, starts_at__lte=now)
        .filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now))
        .filter(plan__is_active=True)
        .order_by("-plan__visible_days_from_yesterday", "-starts_at", "-id")
        .first()
    )


def effective_plan(request, policy: ForecastAccessPolicy) -> ForecastPlan | None:
    if not getattr(request.user, "is_authenticated", False):
        return None
    membership = effective_membership(request)
    return membership.plan if membership else policy.default_authenticated_plan


def resolve_forecast_access(request, *, today: date | None = None) -> ForecastAccess:
    today = today or now_tehran().date()
    # Forecast is public for today and seven following days; account products remain separate.
    member = getattr(request.user, "is_authenticated", False)
    policy = active_policy() if member else None
    membership = effective_membership(request) if member else None
    plan = membership.plan if membership else (policy.default_authenticated_plan if policy else None)
    return ForecastAccess(viewer="member" if member else "anonymous", plan=plan, display_days=8,
                          visible_days_from_yesterday=8, available_through=today+timedelta(days=7),
                          member_available_through=today+timedelta(days=7), today=today,
                          expires_at=membership.expires_at if membership else None)


def decorate_forecast_payload(payload: dict, access: ForecastAccess) -> dict:
    days = day_window(access.today)[: access.display_days]
    decorated = []
    for day in days:
        # Existing serializers already calculate presentation/Jalali fields;
        # retain their payload when available and only add access metadata.
        source = next((item for item in payload.get("days", []) if item.get("date") == day.isoformat()), None)
        if source is None:
            continue
        entry = dict(source)
        entry["access"] = access.status_for(day)
        decorated.append(entry)
    payload["days"] = decorated
    if isinstance(payload.get("forecast"), dict):
        payload["forecast"] = {**payload["forecast"], "days": decorated}
    payload["forecast_access"] = access.payload()
    return payload
