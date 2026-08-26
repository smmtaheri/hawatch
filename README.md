# هواچ (Hawatch)

هواچ محصولی فارسی و تصمیم‌محور برای دیدن هوای مقصد و برنامه‌ریزی مسیر است. کاربر به‌جای دیدن یک دمای منفرد، شرایط مقصد و تغییرات آب‌وهوا را در طول مسیر می‌بیند تا بتواند زمان حرکت، مسیر و امکان ادامه‌دادن یا برگشتن را آگاهانه‌تر انتخاب کند.

## وضعیت این repository

این repository فعلاً فقط یک design handoff و محل نگهداری مستندات محصول است. تصاویر اصلی بدون تغییر کیفیت در `design/source-screens/` نگهداری شده‌اند و نسخه‌های مرتب‌شدهٔ قابل ارجاع در `design/screens/` قرار دارند.

هیچ application code، frontend، backend، dependency یا زیرساخت اجرایی در این milestone وجود ندارد. Login فعلاً فقط به‌عنوان reference و بخشی از design system مستند شده و در milestone اول پیاده‌سازی نمی‌شود.

## صفحات اصلی

- **Home**: جست‌وجوی مقصد و انتخاب از مقصدهای محبوب.
- **Destination**: پیش‌بینی مقصد، هشدارها، مسیرهای موجود و جزئیات تخصصی.
- **Route**: برنامه‌ریزی حرکت روی یک مسیر، آب‌وهوای نقاط مهم و کارت تصمیم.
- **Login**: reference طراحی؛ خارج از milestone اول.

## stack آینده

- frontend: React + TypeScript
- bundler پیشنهادی frontend: Vite
- backend: Django + Django REST Framework
- Python: 3.14
- مدیریت محیط و dependency backend: uv
- database اصلی: PostgreSQL
- Redis: optional برای cache، distributed lock، queue یا job coordination
- Kafka و data lake: مسیرهای رشد احتمالی، بدون تصمیم نهایی

## ساختار repository

```text
design/       تصاویر، tokenها، سیستم طراحی و مشخصات صفحه‌ها
docs/         brief، flow، رفتار صفحه، API آینده، معماری، ADR و QA
apps/         محل آیندهٔ web و api؛ فعلاً فقط placeholder
infra/        محل آیندهٔ infrastructure؛ فعلاً فقط placeholder
scripts/      محل آیندهٔ ابزارهای کمکی؛ فعلاً فقط placeholder
AGENTS.md     قوانین ثابت همکاری روی محصول
```

## مراحل بعدی پیشنهادی

1. تأیید design handoff، tokenها و ابهام‌های ثبت‌شده.
2. تبدیل acceptance criteria به تست‌های قابل مشاهدهٔ UI.
3. ساخت milestone محدود frontend با مقایسهٔ screenshot به screenshot.
4. تثبیت قرارداد forecast و سپس طراحی API داخلی.
5. بررسی compatibility نسخه‌های Django/DRF با Python 3.14 پیش از شروع backend.

فعلاً هیچ command اجرایی برای frontend یا backend در این repository وجود ندارد.

