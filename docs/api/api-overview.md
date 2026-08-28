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
- `GET /api/v1/routes/{route_slug}/points/{point_slug}/forecast/?date=&period=` (legacy؛ سازگاری)
- `GET /api/v1/search/suggestions/?q=`

`period`: `morning` | `afternoon` | `night`
`speed`: `آرام` | `متوسط` | `سریع` یا معادل `slow` | `medium` | `fast`

پاسخ‌ها `schema_version`، timezone تهران، freshness و data_mode دارند. جزئیات بازه‌ها و انتخاب پیش‌فرض در [forecast-contract.md](./forecast-contract.md) است.
