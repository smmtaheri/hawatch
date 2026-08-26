# رفتار Login reference

Login در milestone اول اجرا نمی‌شود و این سند فقط قرارداد تجربهٔ آینده است.

## قرارداد تعامل آینده

- شمارهٔ موبایل معتبر → request OTP.
- شمارهٔ نامعتبر → inline validation.
- request در حال انجام → CTA disabled و feedback.
- ارسال موفق → مرحلهٔ verify OTP یا مسیر توافق‌شده.
- خطا و rate limit → پیام قابل اقدام و retry با محدودیت.

## محدودیت این milestone

هیچ form handler، auth API، session، dependency یا backend ایجاد نشود. فقط screenshot و design page reference معتبر است.

