# Redis (آینده)

Redis در milestone اول اجباری نیست.

در Compose یک سرویس optional با profile `cache` و image `redis:7.4.2` آماده شده است. کاربردهای آینده:

- cache پاسخ forecast
- distributed lock برای ingestion
- coordination جاب‌ها

داخل شبکهٔ Compose همیشه `redis:6379` است. پورت میزبان با `REDIS_PUBLISH_PORT` تنظیم می‌شود (پیش‌فرض `6379`؛ اگر اشغال بود مثلاً `6380`).

متغیر placeholder: `REDIS_URL=redis://localhost:${REDIS_PUBLISH_PORT:-6379}/0`
