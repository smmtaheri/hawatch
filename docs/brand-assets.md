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
