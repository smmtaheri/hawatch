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
