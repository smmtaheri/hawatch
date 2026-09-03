# نمای کلی API

Frontend فقط API داخلی هواچ را مصرف می‌کند.

## endpointهای این milestone

- `GET /api/v1/health/live/`
- `GET /api/v1/health/ready/`
- `GET /api/v1/destinations/?query=`
- `GET /api/v1/destinations/{slug}/`
- `GET /api/v1/destinations/{slug}/forecast/?date=&period=`
- `GET /api/v1/routes/{slug}/`
- `GET /api/v1/routes/{slug}/forecast/?date=&period=&start_time=&speed=`
- `GET /api/v1/points/{weather_point_slug}/forecast/?date=&period=`
- `GET /api/v1/search/suggestions/?q=`

`period`: `midnight` | `morning` | `noon` | `night` (`afternoon` فقط alias ورودی قدیمی است)
`speed`: `آرام` | `متوسط` | `سریع` یا معادل `slow` | `medium` | `fast`

Destination و Point forecast هر دو از قرارداد مشترک Forecast Place (`subject` / `hero` / `metrics` / `decision` / `related_routes`) استفاده می‌کنند؛ aliasهای سازگاری `destination` و `point` حفظ شده‌اند.

پاسخ‌ها `schema_version`، timezone تهران، freshness و data_mode دارند. جزئیات بازه‌ها و انتخاب پیش‌فرض در [forecast-contract.md](./forecast-contract.md) است.
