# نمای کلی API

Frontend فقط API داخلی هواچ را مصرف می‌کند.

## endpointهای این milestone

- `GET /api/v1/health/live/`
- `GET /api/v1/health/ready/`
- `GET /api/v1/points/?query=`
- `GET /api/v1/points/{slug}/`
- `GET /api/v1/points/{slug}/forecast/?date=&period=`
- `GET /api/v1/routes/{slug}/`
- `GET /api/v1/routes/{slug}/forecast/?date=&period=&start_time=&speed=`
- `GET /api/v1/search/suggestions/?q=`

`period`: `midnight` | `morning` | `noon` | `night` (`afternoon` فقط alias ورودی قدیمی است)
`speed`: `آرام` | `متوسط` | `سریع` یا معادل `slow` | `medium` | `fast`

صفحهٔ forecast هر نقطه از قرارداد مشترک Point Forecast (`subject` / `hero` / `metrics` / `decision` / `related_routes`) استفاده می‌کند؛ alias ریشهٔ `point` فقط برای سازگاری حفظ شده است.

پاسخ‌ها `schema_version`، timezone تهران، freshness و data_mode دارند. جزئیات بازه‌ها و انتخاب پیش‌فرض در [forecast-contract.md](./forecast-contract.md) است.
