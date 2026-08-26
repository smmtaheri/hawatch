# ADR 0003: Compose محلی و دادهٔ دمو

- وضعیت: پذیرفته‌شده
- تاریخ: 2026-08-26

## زمینه

اولین نسخهٔ اجرایی باید بدون provider خارجی و بدون Redis/Kafka کار کند، اما برای مهاجرت بعدی به Kubernetes و ingestion واقعی آماده بماند.

## تصمیم

- pnpm workspace در ریشه برای frontend؛ uv و `pyproject.toml` جدا برای API
- Docker Compose با postgres (PostGIS پین‌شده)، api و web
- Redis فقط با Compose profile `cache`
- دادهٔ هوا در milestone اول دمو، قطعی نسبت به clock تهران، با command idempotent `seed_demo_data`
- API هنگام start خودش migrate و seed می‌کند

## پیامدها

- توسعه‌دهنده با یک `compose up` به سه صفحه می‌رسد
- frontend به API داخلی وابسته است نه به fixture داخل component
- ورود دادهٔ واقعی بعداً با `DEMO_DATA_ENABLED=false` و پیاده‌سازی `WeatherProvider` ممکن است
