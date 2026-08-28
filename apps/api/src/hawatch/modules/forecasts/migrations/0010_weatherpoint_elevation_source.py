from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("forecasts", "0009_search_aliases"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql=(
                        'ALTER TABLE "forecasts_weatherpoint" '
                        'ADD COLUMN IF NOT EXISTS "elevation_source" varchar(255) '
                        "DEFAULT '' NOT NULL;"
                    ),
                    reverse_sql=(
                        'ALTER TABLE "forecasts_weatherpoint" '
                        'DROP COLUMN IF EXISTS "elevation_source";'
                    ),
                ),
            ],
            state_operations=[
                migrations.AddField(
                    model_name="weatherpoint",
                    name="elevation_source",
                    field=models.CharField(blank=True, default="", max_length=255),
                ),
            ],
        ),
    ]
