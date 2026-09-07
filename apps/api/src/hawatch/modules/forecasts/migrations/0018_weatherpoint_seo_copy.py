from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("forecasts", "0017_weather_proxy")]

    operations = [
        migrations.AddField(
            model_name="weatherpoint",
            name="seo_title",
            field=models.CharField(blank=True, default="", max_length=160),
        ),
        migrations.AddField(
            model_name="weatherpoint",
            name="seo_description",
            field=models.CharField(blank=True, default="", max_length=320),
        ),
        migrations.AddField(
            model_name="weatherpoint",
            name="seo_content",
            field=models.TextField(blank=True, default=""),
        ),
    ]
