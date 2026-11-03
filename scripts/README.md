# pnpm helper scripts live in the root package.json.

## Catalog workflow

`publish_catalog.py` یک catalog محلی را بدون کپی‌کردن فایل روی سرور، ابتدا با
Open-Meteo/DEM و سپس با `seed_catalog --check-only` بررسی می‌کند. با `--apply`
به‌صورت اتمیک import، ingest هدفمند و preflight نهایی را اجرا می‌کند. GPX و
`tracks/` هیچ‌وقت توسط این workflow به سرور ارسال نمی‌شوند.

راهنمای کامل: [`../docs/catalog-onboarding.md`](../docs/catalog-onboarding.md)

## صف مقصدهای هواکوه و هواگشت

`catalog_queue.py` فقط صف تحریریه‌ای `docs/catalog-queue.json` و نماهای مستندات
آن را مدیریت می‌کند و دادهٔ برنامه را تغییر نمی‌دهد:

```bash
python3 scripts/catalog_queue.py --next 10
python3 scripts/catalog_queue.py --next 10 --source havakouh
python3 scripts/catalog_queue.py --render
python3 scripts/catalog_queue.py --check
python3 scripts/test_catalog_queue.py
```

`--snapshot-live hawatch` فیلدهای عمومی کاتالوگ را با اتصال read-only دیتابیس از
SSH به stdout می‌فرستد. `--complete <queue-id> --slug <slug> --live-snapshot <file>`
فقط با شاهد رکورد فعال، ردیف صف را موجود می‌کند و نماها را دوباره می‌سازد.
راهنمای وضعیت‌ها و بستن کار در [صف یکپارچه](../docs/catalog-queue.md) است.
