# اجرای محلی هواچ

## پیش‌نیاز

- Docker Engine و Docker Compose v2
- برای توسعهٔ خارج از Compose: Node 22، pnpm 9.15.9، Python 3.14، uv، PostgreSQL/PostGIS

## شروع

```bash
cp .env.example .env
# secretهای observability را طبق `docs/observability.md` در `.env` تنظیم کن.
docker compose --env-file .env -f infra/compose/compose.yaml up -d --build
```

`.env.example` فقط مستندات است؛ Compose از `.env` واقعی برای runtime استفاده می‌کند.

API هنگام start:

1. منتظر health PostgreSQL می‌ماند
2. migration اجرا می‌کند
3. اگر `DEMO_DATA_ENABLED=true` باشد، `seed_demo_data` را idempotent اجرا می‌کند
4. اگر `DEMO_DATA_ENABLED=false` باشد، فقط `seed_tochal_catalog` را اجرا می‌کند (بدون فراخوانی Open-Meteo)
5. gunicorn را روی `:8000` بالا می‌آورد

## آدرس‌ها و پورت‌ها

| سرویس | آدرس |
| --- | --- |
| web | http://localhost:5173 |
| api | http://localhost:8000/api/v1/ |
| postgres | فقط داخل شبکهٔ Compose روی `postgres:5432` |
| redis (optional) | فقط داخل شبکهٔ Compose روی `redis:6379`؛ profile `cache` |
| Grafana | localhost:`GRAFANA_PUBLISH_PORT` (پیش‌فرض 3000) |
| OpenSearch Dashboards | localhost:`OPENSEARCH_DASHBOARDS_PUBLISH_PORT` (پیش‌فرض 5601) |

## توقف و لاگ

```bash
docker compose -f infra/compose/compose.yaml logs -f
docker compose -f infra/compose/compose.yaml down
```

حذف volume دیتابیس:

```bash
docker compose -f infra/compose/compose.yaml down -v
```

## دادهٔ دمو

دادهٔ هوا از generator قطعی با timezone `Asia/Tehran` ساخته می‌شود. seed version پیش‌فرض `hawatch-demo-v1` است. همان صفحه در همان تاریخ/ساعت محلی مقدار یکسان می‌دهد و با تغییر date/hour عوض می‌شود.

غیرفعال‌کردن دمو برای مسیر live:

```bash
DEMO_DATA_ENABLED=false
```

Bootstrap کاتالوگ توچال بدون ingestion:

```bash
cd apps/api
uv run python manage.py seed_tochal_catalog
```

Ingestion جدا و فقط از طریق management command (هرگز از handlerهای API):

```bash
uv run python manage.py ingest_open_meteo
```

Retention: snapshotهای خام قدیمی‌تر از ۷ روز پاک می‌شوند؛ آخرین snapshot قابل‌استفاده قبل از جایگزین موفق حذف نمی‌شود. Ingest هم‌زمان با advisory lock مسدود می‌شود.

## توسعهٔ frontend بدون Docker web

```bash
pnpm install
pnpm dev
```

`VITE_API_BASE_URL` باید به API منتشرشده در مرورگر اشاره کند، معمولاً `http://localhost:8000/api/v1`.

## توسعهٔ API بدون Docker api

با یک Postgres/PostGIS در حال اجرا:

```bash
cd apps/api
uv sync --group dev
export DJANGO_SETTINGS_MODULE=hawatch.config.settings.local
# از .env محلی برای OPEN_METEO_* و DEMO_DATA_ENABLED استفاده کنید
uv run python manage.py migrate
uv run python manage.py seed_demo_data   # یا seed_tochal_catalog وقتی DEMO_DATA_ENABLED=false
uv run python manage.py runserver 0.0.0.0:8000
```

## تست

```bash
pnpm test
docker compose -f infra/compose/compose.yaml exec api pytest
docker compose -f infra/compose/compose.yaml config
```

pytest روی میزبان بدون GDAL/PostGIS معمولاً fail می‌شود؛ تست backend را داخل container اجرا کنید.

## خارج از scope این milestone

- Login / OTP
- فراخوانی live Open-Meteo از handlerهای API یا از CI بدون mock
- Redis اجباری، Celery، Kafka، data lake
- Kubernetes manifests
- صفحهٔ destination-point و share server-side
