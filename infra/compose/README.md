# Compose محلی هواچ

فایل اجرایی: `infra/compose/compose.yaml`

## سرویس‌های پیش‌فرض

- `postgres` — `postgis/postgis:16-3.5` با volume نام‌دار `hawatch_pgdata`
- `api` — Django/DRF روی `:8000`
- `web` — Vite dev server روی `:5173`

Redis با profile `cache` تعریف شده و در `up` عادی بالا نمی‌آید:

```bash
docker compose --env-file .env -f infra/compose/compose.yaml --profile cache up -d redis
```

Kafka در این milestone اضافه نشده است.

## دستورها

```bash
cp .env.example .env   # سپس پورت‌ها را در صورت نیاز تنظیم کن
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

اگر پورت میزبان اشغال باشد، فقط publish port را در `.env` محلی تغییر بده:

```bash
POSTGRES_PUBLISH_PORT=5433
REDIS_PUBLISH_PORT=6380
```
