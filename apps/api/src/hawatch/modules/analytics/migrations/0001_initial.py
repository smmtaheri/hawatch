from django.db import migrations, models
from django.utils import timezone


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        ("forecasts", "0016_unify_point_profile"),
        ("routes", "0020_unify_point_route_links"),
    ]
    operations = [
        migrations.CreateModel(
            name="PageViewEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("page_type", models.CharField(choices=[("point", "Point"), ("route", "Route")], max_length=8)),
                ("page_slug", models.SlugField(max_length=96)),
                ("visitor_hash", models.CharField(max_length=64)),
                ("navigation_id", models.CharField(max_length=64)),
                ("occurred_at", models.DateTimeField(db_index=True, default=timezone.now)),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(
                        fields=("page_type", "page_slug", "visitor_hash", "navigation_id"),
                        name="uniq_analytics_navigation",
                    )
                ],
                "indexes": [
                    models.Index(fields=["page_type", "page_slug", "occurred_at"], name="analytics_page_period_idx"),
                    models.Index(fields=["visitor_hash", "occurred_at"], name="analytics_visitor_time_idx"),
                ],
            },
        )
    ]
