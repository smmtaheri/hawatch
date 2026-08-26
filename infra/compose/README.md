# Compose محلی هواچ

فایل اجرایی: `infra/compose/compose.yaml`

## سرویس‌های پیش‌فرض

- `postgres` — `postgis/postgis:16-3.5` با volume نام‌دار `hawatch_pgdata`
- `api` — Django/DRF روی `:8000`
- `web` — Vite dev server روی `:5173`

Redis با profile `cache` تعریف شده و در `up` عادی بالا نمی‌آید:

```bash
docker compose -f infra/compose/compose.yaml --profile cache up -d redis
```

Kafka در این milestone اضافه نشده است.

## دستورها

```bash
docker compose -f infra/compose/compose.yaml up -d --build
docker compose -f infra/compose/compose.yaml up -d
docker compose -f infra/compose/compose.yaml ps
docker compose -f infra/compose/compose.yaml logs -f api
docker compose -f infra/compose/compose.yaml down
```

## متغیرها

نام‌ها در `.env.example` هستند. داخل کد backend مقدار localhost برای دیتابیس hard-code نشده؛ `POSTGRES_HOST` در Compose برابر `postgres` است.

پورت منتشرشدهٔ Postgres روی میزبان پیش‌فرض `5432` است. اگر این پورت اشغال باشد:

```bash
POSTGRES_PUBLISH_PORT=5433 docker compose -f infra/compose/compose.yaml up -d
```

داخل شبکهٔ Compose، API همیشه به `postgres:5432` وصل می‌شود.
