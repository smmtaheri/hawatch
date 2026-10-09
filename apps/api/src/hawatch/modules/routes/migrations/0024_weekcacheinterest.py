from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("routes", "0023_route_descent_evidence_route_descent_m_and_more")]
    operations = [migrations.CreateModel(
        name="WeekCacheInterest",
        fields=[("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("kind", models.CharField(choices=[("point", "point"), ("route", "route")], max_length=5)),
                ("slug", models.SlugField(max_length=80)),
                ("expires_at", models.DateTimeField(db_index=True))],
        options={"constraints": [models.UniqueConstraint(fields=("kind", "slug"), name="unique_week_cache_interest")]},
    )]
