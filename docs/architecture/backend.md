# معماری backend هواچ

## تصمیم‌های پایه

- Django 5.2 LTS (پشتیبانی Python 3.14 از 5.2.8)
- Django REST Framework 3.17.x (اعلام پشتیبانی Python 3.14)
- Python 3.14 و مدیریت dependency با uv
- PostgreSQL 16 + PostGIS 3.5
- psycopg 3
- Redis و Kafka در این milestone اجرا نمی‌شوند

## ماژول‌ها

- `catalog`: بارگذاری fixture، bootstrap خالی، import غیرتخریبی با ownership/`fixture_managed`، جست‌وجوی pointها و publish مشترک مسیر (DB منبع حقیقت runtime؛ بدون ساخت synthetic `dest:{slug}`)
- `routes`: مدل Route (با `origin_weather_point` / `target_weather_point`، `one_way_minutes` و provenance timing) و RoutePoint (`cumulative_minutes` / `segment_minutes`، `public_note` جدا از `internal_note`)
- `forecasts`: WeatherPoint (هویت، پروفایل و مختصات همان رکورد) و ForecastRecord — حقیقت فیزیکی و منبع forecast
- `integrations.weather`: `WeatherProvider` و generator دمو
- `jobs`: management commandهای seed، ingest one-shot، scheduler شش‌ساعته و retention

پیش‌بینی هر point از یک سرویس/serializer مشترک (`build_place_forecast`) ساخته می‌شود. Route forecast زمان رسیدن هر نقطه را از cumulative متوسط catalog × ضریب زمان pace می‌سازد و forecast همان WeatherPoint را نزدیک به `arrival_at` انتخاب می‌کند (بدون fallback قله؛ در تساوی فاصله، `forecast_at` زودتر). `state` نقطه فقط از severity همان forecast است. timing فقط با invariant کامل usable است (`routes.timing.route_timing_complete`). GPX فقط evidence آفلاین در `tracks/` است.

## تنظیمات

محیط از متغیرها خوانده می‌شود. host دیتابیس hard-code نیست. CORS فقط برای originهای توسعهٔ محلی.

Health:

- `GET /api/v1/health/live/`
- `GET /api/v1/health/ready/` — اتصال DB و PostGIS
- `GET /api/v1/health/status/` — خلاصهٔ authenticated از catalog، آخرین ingest و freshness

## اجرای pilot کم‌هزینه

- API با یک worker gunicorn اجرا می‌شود.
- web به‌صورت build استاتیک Nginx سرو می‌شود؛ Vite dev server فقط برای توسعه است.
- ingest یک management command یک‌باره است؛ سرویس سبک `ingest-scheduler` آن را هر روز ساعت ۰۰، ۰۶، ۱۲ و ۱۸ به وقت تهران اجرا می‌کند.
- OpenSearch، Dashboards، Vector، Prometheus و Grafana فقط با Compose profile `observability` فعال می‌شوند.
