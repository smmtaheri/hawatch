from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("destinations", "0005_destination_popular_default"),
        ("forecasts", "0016_unify_point_profile"),
        ("routes", "0020_unify_point_route_links"),
    ]

    operations = [migrations.DeleteModel(name="Destination")]
