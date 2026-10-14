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

قواعد جست‌وجوی فارسی در [forecast-contract.md](./forecast-contract.md) مرجع
است و در مرورگر، API پیشنهادها و فهرست مقصدها/مسیرها یکسان اجرا می‌شود. کلیدهای
مرورگر برای هر payload یک‌بار آماده می‌شوند؛ تایپ فقط query را normalize می‌کند.
فایل `apps/api/fixtures/search-normalization.json` قرارداد مشترک تست Python و
TypeScript است. migration کاتالوگ `0004` فقط جدول مشتق‌شدهٔ جست‌وجو را برای
داده‌های موجود بازسازی می‌کند؛ import دوبارهٔ مقصدها لازم نیست. کلید کش payload
به `catalog:search-index:v2` ارتقا یافته است. نام، slug و تنظیمات SEO تغییر نمی‌کنند.

`period`: `midnight` | `morning` | `noon` | `night` (`afternoon` فقط alias ورودی قدیمی است)
`speed`: `آرام` | `متوسط` | `سریع` یا معادل `slow` | `medium` | `fast`

صفحهٔ forecast هر نقطه از قرارداد مشترک Point Forecast (`subject` / `hero` / `metrics` / `decision` / `related_routes`) استفاده می‌کند؛ alias ریشهٔ `point` فقط برای سازگاری حفظ شده است.

پاسخ‌ها `schema_version`، timezone تهران، freshness و data_mode دارند. جزئیات بازه‌ها و انتخاب پیش‌فرض در [forecast-contract.md](./forecast-contract.md) است.
