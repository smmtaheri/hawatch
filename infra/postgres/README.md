# PostgreSQL / PostGIS

دیتابیس اصلی هواچ PostgreSQL با PostGIS است.

- image پین‌شدهٔ Compose: `postgis/postgis:16-3.5`
- SRID نقاط: `4326`
- catalog نقطه و route با retention پیش‌بینی پاک نمی‌شود

Django از backend `django.contrib.gis.db.backends.postgis` و driver `psycopg` استفاده می‌کند.
