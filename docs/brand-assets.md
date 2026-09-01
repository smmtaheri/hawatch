# دارایی‌های برند هواچ

دارایی‌های مورد استفادهٔ runtime فقط در `apps/web/public/brand/` نگهداری می‌شوند تا لوگو و favicon در چند مسیر تکرار نشوند.

## هدر

- `hawatch-logo-light.svg`: لوگوی روشن برای پس‌زمینهٔ dark.
- `hawatch-logo-dark.svg`: لوگوی تیره برای پس‌زمینهٔ light.
- `hawatch-mark-light.svg` و `hawatch-mark-dark.svg`: mark مستقل برای استفاده‌های آینده.

`Logo` با `html[data-theme]` نسخهٔ مناسب را نمایش می‌دهد؛ متن یا SVG قدیمیِ inline منبع دیگری برای لوگوی هدر نیست.

## تب و PWA

favicon و آیکون‌های PWA از `hawatch-tab-icon-pack` انتخاب شده‌اند، چون mark مربعی و سادهٔ آن در اندازهٔ ۱۶ پیکسل خواناتر است:

- `favicon.svg` برای مرورگرهای جدید.
- `favicon.ico` و PNGهای ۱۶/۳۲/۴۸ برای fallback.
- `apple-touch-icon.png` و `pwa-192.png` / `pwa-512.png` برای نصب و میانبر.
- `site.webmanifest` با مسیرهای `/brand/...`.

favicon عمداً یک mark مستقل و ثابت است؛ لوگوی کاملِ هدر بر اساس تم light/dark تغییر می‌کند.

## آیکون‌های تخصصی هوا

هشت آیکون تخصصی weather در `apps/web/public/icons/specialist/` نگهداری می‌شوند. فایل canonical برای UI، `hawatch-specialist-icons.svg` است و `SpecialistMetricIcon` از symbolهای آن با `currentColor` استفاده می‌کند؛ SVGهای تک‌آیکون فقط fallback یا استفادهٔ مستقیم‌اند. اندازهٔ پایه ۲۴px و اندازهٔ کارت متریک ۲۸px است. source pack موقت یا preview آن نباید در ریشهٔ پروژه نگهداری یا به runtime اضافه شود.

## آیکون نوع مقصد

`Destination.category_key` کلید معنایی آیکون مقصد است و از دیتابیس/کاتالوگ
خوانده می‌شود؛ بنابراین برای ثبت مقصد جدید، آیکون را با همین فیلد انتخاب کنید
و نیازی به تغییر کد یا deploy برای هر رکورد جدید نیست. کلیدهای فعلی عبارت‌اند
از `mountain`، `volcano`، `waterfall`، `meadow`، `forest`، `desert` و `lake`.

برای نمونه، مقصد آبشار باید `category_key: "waterfall"` داشته باشد. اگر کلیدی
خارج از فهرست ثبت شود، UI عمداً یک نشان خنثی نمایش می‌دهد و آن را به‌اشتباه
کوه نشان نمی‌دهد. افزودن یک شکل کاملاً جدید به این مجموعه یک تغییر محصولی است
و فقط برای خودِ آیکون جدید به deploy نیاز دارد؛ انتخاب آیکون‌های موجود همچنان
کاملاً database-first است.
