# Compose سبک پایلوت هواچ

فایل اجرایی: `infra/compose/compose.yaml`

## سرویس‌های پیش‌فرض

- `postgres` — `postgis/postgis:16-3.5` با volume نام‌دار `hawatch_pgdata`
- `api` — Django/DRF با یک worker روی `:8000`
- `web` — build استاتیک Nginx روی `:5173`
- `nginx` — gateway سبک روی port قابل‌تنظیم (پیش‌فرض `:80`)؛ proxy وب/API و endpoint داخلی `healthz`
- `ingest` — management command یک‌باره برای اجرای دستی یا ingest اولیه؛ deploy script قبل از ingest اولیه image آن را جداگانه build می‌کند چون این سرویس detached بالا نمی‌آید
- `ingest-scheduler` — scheduler سبک داخلی؛ ingest را هر روز ساعت ۰۰، ۰۶، ۱۲ و ۱۸ به وقت تهران اجرا می‌کند
- `maintenance` — cleanup سبک forecast و log، بدون وابستگی به OpenSearch

سرویس‌های سنگین observability در profile `observability` هستند و در `up` عادی بالا نمی‌آیند:

- `opensearch`، `opensearch-dashboards`، `opensearch-auth-init`، `opensearch-provisioner`
- `vector`، `prometheus` و `grafana`

Redis با profile `cache` تعریف شده و در `up` عادی بالا نمی‌آید:

```bash
docker compose --env-file .env -f infra/compose/compose.yaml --profile cache up -d redis
```

Kafka در این milestone اضافه نشده است.

## دستورها

```bash
cp .env.example .env   # secretهای قوی را فقط در .env وارد کن
docker compose --env-file .env -f infra/compose/compose.yaml up -d --build
docker compose --env-file .env -f infra/compose/compose.yaml up -d
docker compose --env-file .env -f infra/compose/compose.yaml run --rm ingest
docker compose --env-file .env -f infra/compose/compose.yaml ps
docker compose --env-file .env -f infra/compose/compose.yaml logs -f api
docker compose --env-file .env -f infra/compose/compose.yaml logs -f ingest-scheduler
docker compose --env-file .env -f infra/compose/compose.yaml down
```

## متغیرها و پورت‌های میزبان

نام‌ها در `.env.example` هستند. داخل شبکهٔ Compose:

- API به `postgres:5432` وصل می‌شود
- Redis داخلی روی `redis:6379` می‌ماند

در حالت pilot، web، API و gateway port میزبان دارند. UIهای observability فقط با profile مربوط publish می‌شوند:

```bash
OPENSEARCH_DASHBOARDS_PUBLISH_PORT=5601
GRAFANA_PUBLISH_PORT=3000
```

PostgreSQL، Redis، OpenSearch، Prometheus و Vector host port ندارند. برای فعال‌کردن observability کامل:

```bash
docker compose --env-file .env -f infra/compose/compose.yaml --profile observability up -d
```

جزئیات token، metricها و retention در `docs/observability.md` است.
