from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


def create_default_access_policy(apps, schema_editor):
    ForecastPlan = apps.get_model("accounts", "ForecastPlan")
    ForecastAccessPolicy = apps.get_model("accounts", "ForecastAccessPolicy")
    plan, _ = ForecastPlan.objects.get_or_create(
        code="free",
        defaults={
            "title": "عضویت رایگان",
            "tier": "free",
            # 0=دیروز, 1=امروز, 2=فردا
            "visible_days_from_yesterday": 2,
            "is_active": True,
            "sort_order": 0,
        },
    )
    ForecastAccessPolicy.objects.get_or_create(
        singleton=1,
        defaults={
            "display_day_count": 7,
            "anonymous_visible_days_from_yesterday": 1,
            "default_authenticated_plan": plan,
        },
    )


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ForecastPlan",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.SlugField(max_length=32, unique=True)),
                ("title", models.CharField(max_length=80)),
                ("tier", models.CharField(choices=[("free", "رایگان"), ("paid", "پولی")], default="free", max_length=12)),
                ("visible_days_from_yesterday", models.PositiveSmallIntegerField(default=1)),
                ("is_active", models.BooleanField(default=True)),
                ("sort_order", models.PositiveSmallIntegerField(default=0)),
            ],
            options={"ordering": ("sort_order", "id"), "verbose_name": "طرح دسترسی", "verbose_name_plural": "طرح‌های دسترسی"},
        ),
        migrations.CreateModel(
            name="AccountProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("phone_e164", models.CharField(max_length=16, unique=True)),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="hawatch_profile", to=settings.AUTH_USER_MODEL)),
            ],
            options={"verbose_name": "حساب کاربر", "verbose_name_plural": "حساب‌های کاربر"},
        ),
        migrations.CreateModel(
            name="ForecastAccessPolicy",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("singleton", models.PositiveSmallIntegerField(default=1, editable=False, unique=True)),
                ("display_day_count", models.PositiveSmallIntegerField(default=7)),
                ("anonymous_visible_days_from_yesterday", models.PositiveSmallIntegerField(default=1)),
                ("default_authenticated_plan", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="default_for_policies", to="accounts.forecastplan")),
            ],
            options={"verbose_name": "سیاست دسترسی پیش‌بینی", "verbose_name_plural": "سیاست دسترسی پیش‌بینی"},
        ),
        migrations.CreateModel(
            name="Membership",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("is_active", models.BooleanField(default=True)),
                ("starts_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                ("source", models.CharField(default="manual", max_length=32)),
                ("plan", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="memberships", to="accounts.forecastplan")),
                ("profile", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="memberships", to="accounts.accountprofile")),
            ],
            options={"ordering": ("-starts_at", "-id"), "verbose_name": "عضویت", "verbose_name_plural": "عضویت‌ها"},
        ),
        migrations.RunPython(create_default_access_policy, migrations.RunPython.noop),
    ]
