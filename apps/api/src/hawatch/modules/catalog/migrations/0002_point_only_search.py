from django.db import migrations, models


def normalize_search_rows(apps, schema_editor):
    SearchIndexEntry = apps.get_model("catalog", "SearchIndexEntry")
    SearchIndexEntry.objects.exclude(kind="point").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0001_search_index"),
        ("forecasts", "0016_unify_point_profile"),
        ("routes", "0020_unify_point_route_links"),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name="searchindexentry",
            name="search_kind_dest_idx",
        ),
        migrations.RemoveField(model_name="searchindexentry", name="destination_slug"),
        migrations.AlterField(
            model_name="searchindexentry",
            name="kind",
            field=models.CharField(choices=[("point", "point")], max_length=16),
        ),
        migrations.RunPython(normalize_search_rows, migrations.RunPython.noop),
    ]
