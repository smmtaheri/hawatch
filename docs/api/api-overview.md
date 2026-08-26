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

`period`: `morning` | `afternoon`  
`speed`: `آرام` | `متوسط` | `سریع` یا معادل `slow` | `medium` | `fast`

پاسخ‌ها `schema_version`، timezone تهران، freshness و data_mode دارند.
