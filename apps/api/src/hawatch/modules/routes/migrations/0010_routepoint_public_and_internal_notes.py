from django.db import migrations, models
from django.db.models import F


def preserve_demo_public_notes(apps, schema_editor):
    """Keep legacy demo copy visible while treating live notes as untrusted evidence."""
    RoutePoint = apps.get_model("routes", "RoutePoint")
    RoutePoint.objects.filter(data_mode="demo", public_note="").update(public_note=F("internal_note"))


class Migration(migrations.Migration):
    dependencies = [
        ("routes", "0009_routepoint_fixture_managed"),
    ]

    operations = [
        migrations.RenameField(
            model_name="routepoint",
            old_name="note",
            new_name="internal_note",
        ),
        migrations.AddField(
            model_name="routepoint",
            name="public_note",
            field=models.CharField(
                blank=True,
                help_text="Short operator-approved copy allowed in the public route API.",
                max_length=255,
            ),
        ),
        migrations.RunPython(preserve_demo_public_notes, migrations.RunPython.noop),
    ]
