# معماری backend هواچ

## تصمیم‌های پایه

- Django 5.2 LTS (پشتیبانی Python 3.14 از 5.2.8)
- Django REST Framework 3.17.x (اعلام پشتیبانی Python 3.14)
- Python 3.14 و مدیریت dependency با uv
- PostgreSQL 16 + PostGIS 3.5
- psycopg 3
- Redis و Kafka در این milestone اجرا نمی‌شوند

## ماژول‌ها

- `catalog`: بارگذاری fixture و seed دمو
- `destinations`: مدل Destination
- `routes`: مدل Route و RoutePoint
- `forecasts`: WeatherPoint و ForecastRecord
- `integrations.weather`: `WeatherProvider` و generator دمو
- `jobs`: management command `seed_demo_data`

## تنظیمات

محیط از متغیرها خوانده می‌شود. host دیتابیس hard-code نیست. CORS فقط برای originهای توسعهٔ محلی.

Health:

- `GET /api/v1/health/live/`
- `GET /api/v1/health/ready/` — اتصال DB و PostGIS
