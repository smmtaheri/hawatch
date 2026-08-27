# Compose محلی و observability هواچ

فایل اجرایی: `infra/compose/compose.yaml`

## سرویس‌های پیش‌فرض

- `postgres` — `postgis/postgis:16-3.5` با volume نام‌دار `hawatch_pgdata`
- `api` — Django/DRF روی `:8000`
- `web` — Vite dev server روی `:5173`
- `opensearch` — index داخلی log؛ بدون host port و با password اجباری
- `opensearch-dashboards` — UI لاگ با port قابل‌تنظیم `5601` و service user/password از env
- `opensearch-auth-init` — ساخت/به‌روزرسانی idempotent service user داخلی با password از env و سپس خروج
- `opensearch-provisioner` — import idempotent dashboardهای log و سپس خروج
- `vector` — فقط `hawatch_logs` را tail می‌کند و به OpenSearch می‌فرستد
- `prometheus` — scrape داخلی API، retention برابر ۷ روز و بدون host port
- `grafana` — dashboard provisioned متریک با login اجباری و port قابل‌تنظیم `3000`
- `maintenance` — cleanup دوره‌ای forecast، rotated log و indexهای Hawatch

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
docker compose --env-file .env -f infra/compose/compose.yaml ps
docker compose --env-file .env -f infra/compose/compose.yaml logs -f api
docker compose --env-file .env -f infra/compose/compose.yaml down
```

## متغیرها و پورت‌های میزبان

نام‌ها در `.env.example` هستند. داخل شبکهٔ Compose:

- API به `postgres:5432` وصل می‌شود
- Redis داخلی روی `redis:6379` می‌ماند

فقط portهای UI observability publish می‌شوند:

```bash
OPENSEARCH_DASHBOARDS_PUBLISH_PORT=5601
GRAFANA_PUBLISH_PORT=3000
```

PostgreSQL، Redis، OpenSearch، Prometheus و Vector host port ندارند. جزئیات token، metricها و retention در `docs/observability.md` است.
