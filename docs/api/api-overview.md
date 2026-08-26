# نمای کلی API آینده

این سند قرارداد آینده را ثبت می‌کند؛ در این milestone هیچ API واقعی ساخته نمی‌شود.

## مرزها

```text
Frontend
  → Hawatch internal API
  → normalized forecast / destination / route services
  → PostgreSQL و cache آینده
  → weather providerها
```

frontend نباید مستقیماً به provider هواشناسی، PostgreSQL یا Redis وصل شود.

## resourceهای اصلی آینده

- `destinations`: catalog مقصد، category، مختصات و elevation.
- `forecasts`: وضعیت فعلی، daily/hourly forecast و freshness.
- `routes`: مسیر، نقاط، ترتیب، ارتفاع و metadata.
- `route-plans`: محاسبهٔ زمان عبور از نقاط بر اساس روز، ساعت و سرعت.
- `share`: payload قابل بازسازی برای اشتراک plan.

## endpointهای مفهومی

- `GET /api/v1/destinations/popular`
- `GET /api/v1/destinations?query=...`
- `GET /api/v1/destinations/{slug}`
- `GET /api/v1/destinations/{slug}/forecast`
- `GET /api/v1/destinations/{slug}/routes`
- `GET /api/v1/routes/{slug}`
- `GET /api/v1/routes/{slug}/plan`

## اصول پاسخ

- response دارای `schema_version`، `fetched_at`، `valid_from` و `valid_to` باشد.
- unitها صریح و ثابت باشند.
- زمان‌ها timezone-aware و قابل نمایش در Asia/Tehran باشند.
- severity علاوه بر color token با value متنی ارائه شود.
- خطا دارای code، message قابل مصرف UI، retryability و request id باشد.
- partial response از failure کامل جدا باشد.

## versioning و خطا

API با namespace `/api/v1` آغاز می‌شود. تغییر breaking باید version جدید یا migration contract داشته باشد. کدهای خطا و auth هنوز نیازمند تصمیم نهایی‌اند.

