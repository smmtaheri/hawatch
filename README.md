# هواچ (Hawatch)

هواچ محصولی فارسی و تصمیم‌محور برای دیدن هوای مقصد و برنامه‌ریزی مسیر است. کاربر به‌جای دیدن یک دمای منفرد، شرایط مقصد و تغییرات آب‌وهوا را در طول مسیر می‌بیند تا بتواند زمان حرکت، مسیر و امکان ادامه‌دادن یا برگشتن را آگاهانه‌تر انتخاب کند.

## وضعیت این repository

این repository شامل design handoff، مستندات محصول، و اولین نسخهٔ محلی اجرایی است:

- frontend: `apps/web` — React + TypeScript + Vite
- backend: `apps/api` — Django + Django REST Framework + PostGIS
- local stack: `infra/compose/compose.yaml` — web، api، postgres و observability داخلی

Login هنوز فقط reference طراحی است و در این milestone پیاده نشده است.

## صفحات این نسخه

- **Home** `/`
- **Destination** `/destination/touchal` (و سایر slugهای catalog)
- **Route** `/routes/touchal-darband` (و سایر مسیرهای مستند)

## اجرای محلی

پیش‌نیاز: Docker و Docker Compose.

```bash
cp .env.example .env
docker compose -f infra/compose/compose.yaml up -d --build
```

پس از ساخته‌شدن imageها:

```bash
docker compose -f infra/compose/compose.yaml up -d
```

- frontend: http://localhost:5173
- API: http://localhost:8000/api/v1/
- health live: http://localhost:8000/api/v1/health/live/
- health ready: http://localhost:8000/api/v1/health/ready/
- Grafana: http://localhost:3000 (port با `GRAFANA_PUBLISH_PORT` قابل تنظیم است)
- OpenSearch Dashboards: http://localhost:5601 (port با `OPENSEARCH_DASHBOARDS_PUBLISH_PORT` قابل تنظیم است)

توقف:

```bash
docker compose -f infra/compose/compose.yaml down
```

لاگ‌ها:

```bash
docker compose -f infra/compose/compose.yaml logs -f api web postgres
```

جزئیات بیشتر در `docs/local-development.md` و `infra/compose/README.md`.

## افزودن مقصد و اعتبارسنجی weather

برای افزودن مقصد بعدی، یک catalog JSON هم‌شکل `apps/api/fixtures/catalog/tochal_v1.json` در `apps/api/fixtures/catalog/` قرار دهید و ابتدا validator read-only را اجرا کنید:

```bash
python3 scripts/validate_open_meteo_catalog.py --catalog apps/api/fixtures/catalog/my_destination_v1.json
```

سپس فقط همان فایل را seed و ingest کنید:

```bash
docker compose -f infra/compose/compose.yaml exec api \
  python manage.py seed_catalog --file catalog/my_destination_v1.json
docker compose -f infra/compose/compose.yaml exec api \
  python manage.py ingest_open_meteo --catalog catalog/my_destination_v1.json --seed-catalog
```

جزئیات قرارداد، تفاوت elevation catalog و DEM، و smoke test در `docs/catalog-and-weather-validation.md` است.

## stack

- frontend: React + TypeScript + Vite + pnpm workspace
- backend: Django 5.2 LTS + DRF + Python 3.14 + uv
- database: PostgreSQL 16 + PostGIS 3.5
- Redis: optional، profile `cache`؛ در این milestone لازم نیست
- Kafka و data lake: خارج از این milestone
- Observability: OpenSearch + Dashboards، Vector، Prometheus و Grafana؛ جزئیات در `docs/observability.md`

## ساختار repository

```text
design/       تصاویر، tokenها، سیستم طراحی و مشخصات صفحه‌ها
docs/         brief، flow، رفتار صفحه، API، معماری، ADR و QA
apps/web      frontend
apps/api      Django API
infra/        Compose و یادداشت Kubernetes آینده
scripts/      ابزارهای کمکی
AGENTS.md     قوانین ثابت همکاری روی محصول
```
