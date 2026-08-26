# معماری آیندهٔ backend

این سند تصمیم آینده را ثبت می‌کند؛ backend در این milestone ساخته نمی‌شود.

## تصمیم‌های پایه

- API با Django REST Framework ساخته خواهد شد.
- PostgreSQL دیتابیس اصلی خواهد بود.
- Python نسخهٔ 3.14 هدف معماری است.
- مدیریت محیط و dependency با `uv` انجام خواهد شد.
- Redis فعلاً optional است و در صورت نیاز برای cache، lock، queue یا coordination اضافه می‌شود.
- Kafka یا data lake فعلاً انتخاب قطعی نیستند.

## مرزهای پیشنهادی

- catalog مقصد و route مستقل از retention forecast نگه‌داری شوند.
- ingestion provider از normalize/validate و API read model جدا باشد.
- raw response با metadata قابل ردیابی ذخیره شود.
- API فقط normalized/read model را در اختیار frontend قرار دهد.
- jobها request id، ingestion run id، heartbeat و status قابل مشاهده داشته باشند.

## قبل از implementation

- compatibility نسخه‌های Django و DRF با Python 3.14 بررسی شود.
- policy timezone، auth، error envelope، migration و backup مشخص شود.
- ظرفیت، rate limit و provider terms بررسی شود.

