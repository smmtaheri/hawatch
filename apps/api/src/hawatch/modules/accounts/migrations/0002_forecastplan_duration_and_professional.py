from django.db import migrations, models


def create_professional_plan(apps, schema_editor):
    ForecastPlan = apps.get_model("accounts", "ForecastPlan")
    plan, _ = ForecastPlan.objects.get_or_create(
        code="professional",
        defaults={
            "title": "طرح حرفه‌ای",
            "tier": "paid",
            "visible_days_from_yesterday": 6,
            "duration_months": 3,
            "is_active": True,
            "sort_order": 1,
        },
    )
    # If an operator created this canonical code before this migration,
    # preserve their title/visibility but still make the duration explicit.
    if plan.duration_months != 3:
        plan.duration_months = 3
        plan.save(update_fields=["duration_months"])


class Migration(migrations.Migration):
    dependencies = [("accounts", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="forecastplan",
            name="duration_months",
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
        migrations.RunPython(create_professional_plan, migrations.RunPython.noop),
    ]
