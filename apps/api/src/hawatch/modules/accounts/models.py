from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from hawatch.common.time import FORECAST_DAY_COUNT


class ForecastPlan(models.Model):
    class Tier(models.TextChoices):
        FREE = "free", "رایگان"
        PAID = "paid", "پولی"

    code = models.SlugField(max_length=32, unique=True)
    title = models.CharField(max_length=80)
    tier = models.CharField(max_length=12, choices=Tier.choices, default=Tier.FREE)
    # 0 = only yesterday, 1 = through today, 2 = through tomorrow, …
    visible_days_from_yesterday = models.PositiveSmallIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ("sort_order", "id")
        verbose_name = "طرح دسترسی"
        verbose_name_plural = "طرح‌های دسترسی"

    def clean(self):
        if self.visible_days_from_yesterday > FORECAST_DAY_COUNT - 1:
            raise ValidationError({"visible_days_from_yesterday": "از سقف روزهای قابل‌نمایش بیشتر است."})

    def __str__(self) -> str:
        return self.title


class ForecastAccessPolicy(models.Model):
    """A single operator-editable policy. It never belongs in deploy env vars."""

    singleton = models.PositiveSmallIntegerField(default=1, unique=True, editable=False)
    display_day_count = models.PositiveSmallIntegerField(default=FORECAST_DAY_COUNT)
    anonymous_visible_days_from_yesterday = models.PositiveSmallIntegerField(default=1)
    default_authenticated_plan = models.ForeignKey(
        ForecastPlan,
        on_delete=models.PROTECT,
        related_name="default_for_policies",
    )

    class Meta:
        verbose_name = "سیاست دسترسی پیش‌بینی"
        verbose_name_plural = "سیاست دسترسی پیش‌بینی"

    def clean(self):
        if not 1 <= self.display_day_count <= FORECAST_DAY_COUNT:
            raise ValidationError({"display_day_count": f"بین ۱ تا {FORECAST_DAY_COUNT} انتخاب شود."})
        maximum = self.display_day_count - 1
        if self.anonymous_visible_days_from_yesterday > maximum:
            raise ValidationError({"anonymous_visible_days_from_yesterday": "از سقف نمایش بیشتر است."})
        if self.default_authenticated_plan_id and self.default_authenticated_plan.visible_days_from_yesterday < self.anonymous_visible_days_from_yesterday:
            raise ValidationError({"default_authenticated_plan": "طرح رایگان نمی‌تواند از دسترسی مهمان کمتر باشد."})

    def __str__(self) -> str:
        return "سیاست فعال پیش‌بینی"


class AccountProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="hawatch_profile")
    phone_e164 = models.CharField(max_length=16, unique=True)

    class Meta:
        verbose_name = "حساب کاربر"
        verbose_name_plural = "حساب‌های کاربر"

    def __str__(self) -> str:
        return self.phone_e164


class Membership(models.Model):
    profile = models.ForeignKey(AccountProfile, on_delete=models.CASCADE, related_name="memberships")
    plan = models.ForeignKey(ForecastPlan, on_delete=models.PROTECT, related_name="memberships")
    is_active = models.BooleanField(default=True)
    starts_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(null=True, blank=True)
    source = models.CharField(max_length=32, default="manual")

    class Meta:
        ordering = ("-starts_at", "-id")
        verbose_name = "عضویت"
        verbose_name_plural = "عضویت‌ها"

    @property
    def currently_active(self) -> bool:
        now = timezone.now()
        return self.is_active and self.starts_at <= now and (self.expires_at is None or self.expires_at > now)

    def __str__(self) -> str:
        return f"{self.profile} · {self.plan}"
