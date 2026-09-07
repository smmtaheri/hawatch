from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("routes", "0020_unify_point_route_links")]

    operations = [
        migrations.AddField(
            model_name="route",
            name="seo_title",
            field=models.CharField(blank=True, default="", max_length=160),
        ),
        migrations.AddField(
            model_name="route",
            name="seo_description",
            field=models.CharField(blank=True, default="", max_length=320),
        ),
        migrations.AddField(
            model_name="route",
            name="seo_content",
            field=models.TextField(blank=True, default=""),
        ),
    ]
