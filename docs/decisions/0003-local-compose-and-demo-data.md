# ADR 0003: Compose محلی و دادهٔ دمو

- وضعیت: پذیرفته‌شده
- تاریخ: 2026-08-26

## زمینه

اولین نسخهٔ اجرایی باید بدون provider خارجی و بدون Redis/Kafka کار کند، اما برای مهاجرت بعدی به Kubernetes و ingestion واقعی آماده بماند.

## تصمیم

- pnpm workspace در ریشه برای frontend؛ uv و `pyproject.toml` جدا برای API
- Docker Compose با postgres (PostGIS پین‌شده)، api و web
- Redis فقط با Compose profile `cache`
- دادهٔ هوا در milestone اول دمو، قطعی نسبت به clock تهران، با command idempotent `seed_demo_data`؛ مسیر صریح ingest واقعی و Open-Meteo وجود دارد اما startup/API به‌صورت خودکار provider را صدا نمی‌زنند
- API هنگام start خودش migrate و seed می‌کند

## پیامدها

- توسعه‌دهنده با یک `compose up` به چهار صفحهٔ اجرایی Home، Destination، Route و Point می‌رسد؛ Login همچنان reference است
- frontend به API داخلی وابسته است نه به fixture داخل component
- ورود دادهٔ واقعی با `DEMO_DATA_ENABLED=false` و command/provider موجود قابل اجرای کنترل‌شده است؛ scheduler داخلی با زمان‌های ثابت تهران (`۰۰، ۰۶، ۱۲، ۱۸`) command را اجرا می‌کند.
