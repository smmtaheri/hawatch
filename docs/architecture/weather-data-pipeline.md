# pipeline آیندهٔ دادهٔ هوا

## مسیر داده

```text
provider weather API
  → سرویس دریافت دادهٔ خام
  → ذخیرهٔ raw response با metadata
  → سرویس normalize و validate
  → ثبت دادهٔ قابل‌مصرف در PostgreSQL
  → API و cache
  → سرویس retention و پاک‌سازی
```

## raw و forecast metadata

برای raw و forecast این metadata الزامی آینده است:

- provider
- coordinates
- elevation
- fetched_at
- valid_from
- valid_to
- model
- request_id
- ingestion_run_id
- schema_version
- content_hash
- status
- error information

## retention

- داده‌های خام و پیش‌بینی‌های زمانی حداکثر یک هفته نگه داشته شوند.
- job پاک‌سازی باید idempotent و قابل مشاهده باشد.
- catalog مقصدها، نقاط مسیر، مختصات تأییدشده و تعریف routeها با این retention پاک نشوند.
- حذف باید بر اساس valid/fetched policy مستند باشد و امکان audit حداقلی داشته باشد.

## تاب‌آوری و هماهنگی

نیازهای آینده شامل retry، backoff، ادامه بعد از خطا، heartbeat، checkpoint اتمیک و جلوگیری از اجرای هم‌زمان است. failure provider نباید دادهٔ سالم قبلی را بدون علامت overwrite کند.

## تصمیم باز دربارهٔ اجرا

فعلاً بین Celery/Redis، job runner ساده، Kafka و data lake تصمیم نهایی گرفته نمی‌شود. trade-off در ADR 0002 آمده است. Open-Meteo می‌تواند یک provider اولیه/آزمایشی باشد، اما انتخاب نهایی provider و policy fallback هنوز تصویب نشده است.

