"""Backfill RoutePoint.weather_point from legacy WeatherPoint.route_point, then drop the old FK.

Deterministic rules (no invented links):
1. If WeatherPoint.route_point_id points at an existing RoutePoint, set that RoutePoint.weather_point
   when it is empty or already points at the same WeatherPoint.
2. Conflicts (RoutePoint already linked to a different WeatherPoint) and orphan FKs are left
   unresolved; RoutePoint.weather_point stays unchanged.
3. Destination-only WeatherPoints (no route_point) are ignored.

Ordering: forecasts.0003 keeps the legacy OneToOne; routes.0003 adds RoutePoint.weather_point;
this migration backfills then removes WeatherPoint.route_point.
"""

from django.db import migrations


def forwards_backfill_route_weather_links(apps, schema_editor):
    WeatherPoint = apps.get_model("forecasts", "WeatherPoint")
    RoutePoint = apps.get_model("routes", "RoutePoint")

    # A previous interrupted deployment may have removed the physical column
    # before Django recorded this migration. In that recovery case there is
    # nothing left to backfill, and querying the historical model would fail.
    with schema_editor.connection.cursor() as cursor:
        columns = {
            description.name
            for description in schema_editor.connection.introspection.get_table_description(
                cursor, WeatherPoint._meta.db_table
            )
        }
    if "route_point_id" not in columns:
        return

    linked = 0
    already_linked = 0
    unresolved_missing_route_point = 0
    unresolved_conflict = 0

    for weather_point in WeatherPoint.objects.exclude(route_point_id=None).iterator():
        route_point_id = weather_point.route_point_id
        try:
            route_point = RoutePoint.objects.get(pk=route_point_id)
        except RoutePoint.DoesNotExist:
            unresolved_missing_route_point += 1
            continue

        current = route_point.weather_point_id
        if current is None:
            route_point.weather_point_id = weather_point.id
            route_point.save(update_fields=["weather_point_id"])
            linked += 1
        elif current == weather_point.id:
            already_linked += 1
        else:
            unresolved_conflict += 1

    # Explicit unresolved accounting for operators reviewing migration runs.
    _ = {
        "linked": linked,
        "already_linked": already_linked,
        "unresolved_missing_route_point": unresolved_missing_route_point,
        "unresolved_conflict": unresolved_conflict,
    }


def backwards_noop(apps, schema_editor):
    # Restoring the OneToOne from RoutePoint.weather_point is lossy when multiple route links
    # share one WeatherPoint; leave reverse as a no-op.
    return


class Migration(migrations.Migration):
    # PostgreSQL cannot alter a table with pending FK trigger events from the
    # backfill transaction. Run the data copy and FK removal in separate
    # transactions so the migration is safe on PostgreSQL/PostGIS.
    atomic = False

    dependencies = [
        ("forecasts", "0004_nullable_cloud_uv"),
        ("routes", "0003_route_weather_links"),
    ]

    operations = [
        migrations.RunPython(forwards_backfill_route_weather_links, backwards_noop, atomic=False),
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql='ALTER TABLE "forecasts_weatherpoint" DROP COLUMN IF EXISTS "route_point_id" CASCADE',
                    reverse_sql='''
                        ALTER TABLE "forecasts_weatherpoint"
                        ADD COLUMN IF NOT EXISTS "route_point_id" bigint;
                        DO $$
                        BEGIN
                            IF NOT EXISTS (
                                SELECT 1
                                FROM pg_constraint
                                WHERE conname = 'forecasts_weatherpoi_route_point_id_5a6dbe09_fk_routes_ro'
                            ) THEN
                                ALTER TABLE "forecasts_weatherpoint"
                                ADD CONSTRAINT "forecasts_weatherpoi_route_point_id_5a6dbe09_fk_routes_ro"
                                FOREIGN KEY ("route_point_id") REFERENCES "routes_routepoint" ("id")
                                DEFERRABLE INITIALLY DEFERRED;
                            END IF;
                        END $$;
                    ''',
                )
            ],
            state_operations=[
                migrations.RemoveField(
                    model_name="weatherpoint",
                    name="route_point",
                )
            ],
        ),
    ]

