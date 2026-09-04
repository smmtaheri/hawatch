from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("analytics", "0001_initial")]
    operations = [
        migrations.CreateModel(
            name="MonthlyPageViewAggregate",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("page_type", models.CharField(choices=[("point", "Point"), ("route", "Route")], max_length=8)),
                ("page_slug", models.SlugField(max_length=96)),
                ("month_start", models.DateField()),
                ("page_views", models.PositiveBigIntegerField(default=0)),
                ("unique_visitors", models.PositiveBigIntegerField(default=0)),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(
                        fields=("page_type", "page_slug", "month_start"),
                        name="uniq_analytics_monthly_page",
                    )
                ],
                "indexes": [
                    models.Index(fields=["month_start", "page_type", "page_slug"], name="analytics_month_page_idx"),
                ],
            },
        )
    ]
