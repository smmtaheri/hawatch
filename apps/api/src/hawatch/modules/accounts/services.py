from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from django.db.models import Q

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

    @property
    def is_authenticated(self) -> bool:
        return self.viewer == "member"

    def status_for(self, selected: date) -> str:
        if selected <= self.available_through:
            return "available"
        if self.is_authenticated:
            return "plan_required"
        return "login_required" if selected <= self.member_available_through else "plan_required"

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


def effective_plan(request, policy: ForecastAccessPolicy) -> ForecastPlan | None:
    if not getattr(request.user, "is_authenticated", False):
        return None
    profile = AccountProfile.objects.filter(user=request.user).first()
    if profile:
        now = now_tehran()
        membership = (
            Membership.objects.select_related("plan")
            .filter(profile=profile, is_active=True, starts_at__lte=now)
            .filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now))
            .filter(plan__is_active=True)
            .order_by("-plan__visible_days_from_yesterday", "-starts_at", "-id")
            .first()
        )
        if membership:
            return membership.plan
    return policy.default_authenticated_plan


def resolve_forecast_access(request, *, today: date | None = None) -> ForecastAccess:
    policy = active_policy()
    today = today or now_tehran().date()
    plan = effective_plan(request, policy)
    visible = plan.visible_days_from_yesterday if plan else policy.anonymous_visible_days_from_yesterday
    visible = min(visible, policy.display_day_count - 1)
    member_visible = min(policy.default_authenticated_plan.visible_days_from_yesterday, policy.display_day_count - 1)
    return ForecastAccess(
        viewer="member" if plan else "anonymous",
        plan=plan,
        display_days=policy.display_day_count,
        visible_days_from_yesterday=visible,
        available_through=today + timedelta(days=visible - 1),
        member_available_through=today + timedelta(days=member_visible - 1),
        today=today,
    )


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
