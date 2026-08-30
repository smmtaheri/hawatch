# رفتار Login reference

مسیر Login در milestone اول با shell بصری در دسترس است؛ این سند رفتار احراز هویت آینده و محدودیت‌های فعلی را مشخص می‌کند.

## قرارداد تعامل آینده

- شمارهٔ موبایل معتبر → request OTP.
- شمارهٔ نامعتبر → inline validation.
- request در حال انجام → CTA disabled و feedback.
- ارسال موفق → مرحلهٔ verify OTP یا مسیر توافق‌شده.
- خطا و rate limit → پیام قابل اقدام و retry با محدودیت.

## محدودیت این milestone

هیچ form handler، auth API، session، dependency یا backend احراز هویت ایجاد نشده است. صفحه فقط برای navigation و نمایش reference در دسترس است.
