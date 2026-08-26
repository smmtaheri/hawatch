# Redis (آینده)

Redis در milestone اول اجباری نیست.

در Compose یک سرویس optional با profile `cache` و image `redis:7.4.2` آماده شده است. کاربردهای آینده:

- cache پاسخ forecast
- distributed lock برای ingestion
- coordination جاب‌ها

متغیر placeholder: `REDIS_URL=redis://localhost:6379/0`
