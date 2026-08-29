# معماری backend هواچ

## تصمیم‌های پایه

- Django 5.2 LTS (پشتیبانی Python 3.14 از 5.2.8)
- Django REST Framework 3.17.x (اعلام پشتیبانی Python 3.14)
- Python 3.14 و مدیریت dependency با uv
- PostgreSQL 16 + PostGIS 3.5
- psycopg 3
- Redis و Kafka در این milestone اجرا نمی‌شوند

## ماژول‌ها

- `catalog`: بارگذاری fixture و seed دمو (بدون ساخت synthetic `dest:{slug}`)
- `destinations`: مدل Destination به‌عنوان profile عمومی یک WeatherPoint (`weather_point` OneToOne)
- `routes`: مدل Route (با `origin_weather_point` / `target_weather_point`) و RoutePoint
- `forecasts`: WeatherPoint و ForecastRecord — حقیقت فیزیکی و منبع forecast
- `integrations.weather`: `WeatherProvider` و generator دمو
- `jobs`: management commandهای seed، ingest one-shot و retention

Forecast Place برای destination و point از یک سرویس/serializer مشترک (`build_place_forecast`) ساخته می‌شود.

## تنظیمات

محیط از متغیرها خوانده می‌شود. host دیتابیس hard-code نیست. CORS فقط برای originهای توسعهٔ محلی.

Health:

- `GET /api/v1/health/live/`
- `GET /api/v1/health/ready/` — اتصال DB و PostGIS
- `GET /api/v1/health/status/` — خلاصهٔ authenticated از catalog، آخرین ingest و freshness

## اجرای pilot کم‌هزینه

- API با یک worker gunicorn اجرا می‌شود.
- web به‌صورت build استاتیک Nginx سرو می‌شود؛ Vite dev server فقط برای توسعه است.
- ingest یک management command یک‌باره است و scheduler بیرونی آن را هر ۶ ساعت اجرا می‌کند.
- OpenSearch، Dashboards، Vector، Prometheus و Grafana فقط با Compose profile `observability` فعال می‌شوند.
