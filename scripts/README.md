# pnpm helper scripts live in the root package.json.

## Catalog workflow

`publish_catalog.py` یک catalog محلی را بدون کپی‌کردن فایل روی سرور، ابتدا با
Open-Meteo/DEM و سپس با `seed_catalog --check-only` بررسی می‌کند. با `--apply`
به‌صورت اتمیک import، ingest هدفمند و preflight نهایی را اجرا می‌کند. GPX و
`tracks/` هیچ‌وقت توسط این workflow به سرور ارسال نمی‌شوند.

راهنمای کامل: [`../docs/catalog-onboarding.md`](../docs/catalog-onboarding.md)
