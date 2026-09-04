# checklist الزامات validation و implementation

تاریخ به‌روزرسانی: 2026-08-28

| # | الزام | وضعیت | evidence |
| --- | --- | --- | --- |
| 1 | دقیقاً ۱۶ تصویر منطقی | PASS | `design/manifest.json` و دو درخت `design/source-screens/` و `design/screens/` |
| 2 | source screenshots بدون تغییر | PASS | SHA-256 و policy byte-for-byte در manifest؛ فایل‌های PNG تغییر نکرده‌اند |
| 3 | مسیر page/theme/device | PASS | `design/screens/{page}/{theme}/{device}.png` |
| 4 | تطبیق manifest با فایل واقعی | PASS | نام، ابعاد و hash ثبت‌شده در `design/manifest.json` |
| 5 | نبود duplicate/missing/misnamed ناخواسته | PASS | source و organized pairهای عمدی‌اند؛ Point screenshot مستقل ندارد |
| 6 | خواندن DOCX و تطبیق design system | PASS | `references/Hawatch.docx` و `design/tokens/visual-tokens.json` |
| 7 | مستندات صفحات فعلی | PASS | Home، Point، Route، Point و Login route-backed؛ OTP به‌عنوان مرحلهٔ بعد |
| 8 | layout، متن، interaction، navigation و state | PASS | `design/pages/*` و `docs/page-specs/*` |
| 9 | light/dark و mobile/desktop | PASS | screenshotهای ۱۶گانه، tokens و page specs؛ Point به‌عنوان extension مستند شده |
| 10 | Home → Point → Route و back | PASS | `docs/user-flows/*` و context بازگشت Point در React Router state |
| 11 | API contract و endpoint اجرایی | PASS | `docs/api/*` و endpointهای catalog/search/points/route/point |
| 12 | Django/DRF/PostGIS/Python 3.14/uv | PASS | `apps/api/pyproject.toml`، settings و Compose |
| 13 | scope سرویس‌های آینده | PASS | Redis اختیاری؛ observability profile؛ Kafka و data lake خارج از runtime فعلی |
| 14 | retention/retry/checkpoint | PASS | `docs/architecture/weather-data-pipeline.md` و ingest/maintenance فعلی |
| 15 | implementation فعلی | PASS | `apps/web`، `apps/api` و `infra/compose` اجرایی‌اند؛ ادعای placeholder منسوخ شد |
| 16 | Login و assetها بدون تغییر بی‌منبع | PASS | overlay Login مستند است؛ PNGهای canonical دست‌نخورده، دو reference محصول ثبت‌شده و Point بدون screenshot جعلی |

## موارد خارج از scope یا محدودیت

- `/workspace/sites/hawatch-weather` در این محیط در دسترس نیست و در `docs/open-questions.md` به‌عنوان reference unavailable ثبت شده است.
- دادهٔ forecast فعلی بسته به mode می‌تواند demo باشد؛ provider واقعی فقط از مسیر صریح ingest استفاده می‌شود.
- pixel-perfect بودن Point قابل ادعا نیست، چون screenshot مرجع مستقل برای آن وجود ندارد.
