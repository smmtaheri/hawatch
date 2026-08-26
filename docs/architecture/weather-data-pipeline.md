# pipeline دادهٔ هوا

## وضعیت فعلی

این milestone ingestion واقعی ندارد. API از forecastهای دمو در PostgreSQL می‌خواند. frontend منبع داده را نمی‌بیند؛ فقط contract داخلی را مصرف می‌کند.

غیرفعال‌کردن دمو: `DEMO_DATA_ENABLED=false`.

## مسیر آینده

```text
provider
  → raw weather ingestion
  → raw storage
  → normalization and validation
  → PostgreSQL forecast records
  → API
  → optional Redis cache
  → retention cleanup
```

Interfaceهای آماده‌شده:

- `WeatherProvider`
- `RawWeatherStore`
- `ForecastNormalizer`
- `ForecastRepository`
- `RetentionPolicy`
- `JobLock`

## الزامات آینده

- نگهداری raw حداکثر یک هفته
- نگهداری forecast record حداکثر یک هفته
- catalog و تعریف route با retention هوا حذف نشوند
- retry و backoff
- رسیدگی به Retry-After
- checkpoint/resume
- آخرین دادهٔ سالم به‌صورت atomic
- لاگ JSONL یا structured
- heartbeat
- جلوگیری از اجرای هم‌زمان ingestion
- adapter برای provider
- تنظیم optional proxy (`WEATHER_PROXY_URL`)
- lock/cache اختیاری Redis
- تصمیم بعدی Kafka یا صف ساده‌تر

Open-Meteo می‌تواند provider آزمایشی باشد؛ انتخاب نهایی هنوز باز است.
