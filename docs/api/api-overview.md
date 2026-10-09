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
- `GET /api/v1/catalog/search-index/`
- `GET /api/v1/search/suggestions/?q=`

فهرست جست‌وجو شامل termهای عمومی مقصدها و مسیرهای فعال است؛ دادهٔ هوا در آن
نیست و جست‌وجوی Home بعد از دریافت فهرست در مرورگر انجام می‌شود. پاسخ در Redis
به مدت ۵ دقیقه نگه داشته می‌شود، با تغییرات منتشرشدهٔ کاتالوگ invalid می‌شود و
هدر `Cache-Control` آن برای مرورگر ۶۰ ثانیه و CDN پنج دقیقه است. برای CDN فقط
مسیر همین endpoint را cache کنید؛ endpoint پیشنهادهای queryدار همچنان برای
سازگاری و مسیر جایگزین باقی است.

`period`: `midnight` | `morning` | `noon` | `night` (`afternoon` فقط alias ورودی قدیمی است)
`speed`: `آرام` | `متوسط` | `سریع` یا معادل `slow` | `medium` | `fast`

صفحهٔ forecast هر نقطه از قرارداد مشترک Point Forecast (`subject` / `hero` / `metrics` / `decision` / `related_routes`) استفاده می‌کند؛ alias ریشهٔ `point` فقط برای سازگاری حفظ شده است.

پاسخ‌ها `schema_version`، timezone تهران، freshness و data_mode دارند. جزئیات بازه‌ها و انتخاب پیش‌فرض در [forecast-contract.md](./forecast-contract.md) است.
