# هواچ (Hawatch)

هواچ محصولی فارسی و تصمیم‌محور برای دیدن هوای مقصد و برنامه‌ریزی مسیر است. کاربر به‌جای دیدن یک دمای منفرد، شرایط مقصد و تغییرات آب‌وهوا را در طول مسیر می‌بیند تا بتواند زمان حرکت، مسیر و امکان ادامه‌دادن یا برگشتن را آگاهانه‌تر انتخاب کند.

## وضعیت این repository

این repository شامل design handoff، مستندات محصول، و اولین نسخهٔ محلی اجرایی است:

- frontend: `apps/web` — React + TypeScript + Vite
- backend: `apps/api` — Django + Django REST Framework + PostGIS
- local/pilot stack: `infra/compose/compose.yaml` — web production، api، postgres، ingest one-shot و maintenance سبک
- gateway: Nginx روی port قابل‌تنظیم `NGINX_PUBLISH_PORT` (پیش‌فرض `80`) برای health check و proxy وب/API

Login هنوز فقط reference طراحی است و در این milestone پیاده نشده است.

## صفحات این نسخه

- **Home** `/`
- **Destination** `/destination/touchal` (و سایر slugهای catalog)
- **Route** `/routes/touchal-darband` (و سایر مسیرهای مستند)

## اجرای محلی

پیش‌نیاز: Docker و Docker Compose.

```bash
cp .env.example .env
docker compose --env-file .env -f infra/compose/compose.yaml up -d --build
```

پس از ساخته‌شدن imageها:

```bash
docker compose --env-file .env -f infra/compose/compose.yaml up -d
```

- frontend: http://localhost:5173
- API: http://localhost:8000/api/v1/
- gateway: http://localhost (وب و API از یک ورودی)
- health live: http://localhost:8000/api/v1/health/live/
- health ready: http://localhost:8000/api/v1/health/ready/
- وضعیت عملیاتی: http://localhost:8000/api/v1/health/status/ (با Bearer token)

Ingest در Compose یک‌باره است. برای اجرای دوره‌ای، آن را از timer خارجی هر ۶ ساعت صدا بزن:

```bash
docker compose --env-file .env -f infra/compose/compose.yaml run --rm ingest
```

Observability سنگین پیش‌فرض خاموش است و فقط در صورت نیاز فعال می‌شود:

```bash
docker compose --env-file .env -f infra/compose/compose.yaml --profile observability up -d
```

توقف:

```bash
docker compose --env-file .env -f infra/compose/compose.yaml down
```

لاگ‌ها:

```bash
docker compose -f infra/compose/compose.yaml logs -f api web postgres
```

جزئیات بیشتر در `docs/local-development.md` و `infra/compose/README.md`.

## استقرار سریع روی سرور

برای نصب پیش‌نیازها، clone، ساخت امن `.env`، اجرای Compose سبک و health check از اسکریپت زیر استفاده کنید:

```bash
apt-get update && apt-get install -y ca-certificates curl
curl -fsSL https://raw.githubusercontent.com/smmtaheri/hawatch/main/scripts/deploy.sh -o /root/hawatch-deploy.sh
chmod 700 /root/hawatch-deploy.sh
PUBLIC_HOST=SERVER_IP /root/hawatch-deploy.sh
```

راهنمای کامل، گزینه‌های اسکریپت و دستور توقف در `docs/deployment.md` است. این اسکریپت به‌صورت پیش‌فرض Redis و observability سنگین را اجرا نمی‌کند.

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
- Observability اختیاری: OpenSearch + Dashboards، Vector، Prometheus و Grafana با profile `observability`؛ جزئیات در `docs/observability.md`

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
