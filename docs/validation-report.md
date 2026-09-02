# گزارش validation و بازبینی repository

تاریخ به‌روزرسانی: 2026-08-28

## نتیجهٔ فعلی

repository از handoff اولیه عبور کرده و اکنون یک monorepo اجرایی برای pilot است. پیاده‌سازی شامل Home، Destination، Route و Point مستقل، API داخلی Django/DRF، catalog/search و Compose سبک است. Login به‌صورت UI route-backed (overlay در ورود عادی و صفحهٔ کامل در URL مستقیم) وجود دارد؛ OTP واقعی همچنان خارج از milestone فعلی است.

## منابع

| منبع | وضعیت | توضیح |
| --- | --- | --- |
| `references/Hawatch.docx` | PASS | خوانده شده و اصول RTL، Vazirmatn، palette و hierarchy با design system تطبیق داده شده‌اند. |
| `design/tokens/visual-tokens.json` | PASS | تنها منبع canonical مقدارهای token؛ markdownها توضیح‌دهنده‌اند. |
| `design/source-screens/` و `design/screens/` | PASS | ۱۶ asset منطقی در چهار صفحه، دو theme و دو device؛ sourceها بدون تغییر. |
| live reference URLs | PASS | برای ثبت رفتار و ظاهر reference استفاده شده‌اند؛ رفتار اجرای فعلی از source محلی می‌آید. |
| `/workspace/sites/hawatch-weather` | BLOCKED (non-gating) | در این محیط موجود نیست؛ طبق تصمیم محصول reference unavailable است و اجرای این repository را متوقف نمی‌کند. |

## دارایی‌های تصویری

- چهار صفحهٔ دارای screenshot: Home، Login، Destination و Route.
- برای هر صفحه light/dark و mobile/web وجود دارد؛ در مجموع ۱۶ asset منطقی و ۳۲ PNG فیزیکی source/organized وجود دارد.
- manifest نام، مسیر، width، height و SHA-256 را ثبت می‌کند.
- هیچ تصویر جدیدی برای Point ساخته نشده؛ Point به‌صراحت extension سیستم Destination است، چون screenshot مرجع مستقل ندارد.

## implementation فعلی

### Frontend

- React + TypeScript + Vite + React Router در `apps/web`.
- Home با جست‌وجوی unified مقصد/نقطه از مسیر `/api/v1/search/suggestions/?q=`؛ حداقل دو کاراکتر، normalize، تطبیق داخل نام/alias، debounce حدود ۲۰۰ms، keyboard navigation و retry؛ مسیرها در ایندکس نیستند.
- Destination در `/destination/{slug}`، Route در `/routes/{slug}` و Point مستقل در `/points/{weatherPointSlug}`.
- لینک Route → Point تمیز است و `date`، `period`، `start_time` و `speed` در `location.state.fromRoute` برای back context حفظ می‌شوند.
- RTL، Vazirmatn، light/dark، period toggle سه‌گانه و چهار کارت دوساعته در هر بازه مستند و در source فعلی پشتیبانی می‌شوند.
- Login از هر صفحه با `returnTo` باز می‌شود؛ mobile تمام‌صفحه و desktop dialog است، ولی CTA ارسال OTP تا آماده‌شدن backend غیرفعال می‌ماند.

### Backend و داده

- Django REST با endpointهای health، destinations، destination forecast، route forecast، point forecast و search suggestions.
- PostgreSQL/PostGIS و migrationهای موجود؛ seed دمو idempotent و catalog جدا از forecast.
- زمان و default selection با `Asia/Tehran`؛ بازه‌ها صبح ۰۳/۰۵/۰۷/۰۹، بعدازظهر ۱۱/۱۳/۱۵/۱۷ و شب ۱۹/۲۱/۲۳/۰۱.
- loading/empty/error/stale/partial در قرارداد UI/API تفکیک شده‌اند؛ stale دادهٔ قبلی و زمان update را نگه می‌دارد و error retry دارد.

### Runtime و مسیر توسعه

- Compose سبک: PostgreSQL/PostGIS، API، frontend production، ingest one-shot، scheduler شش‌ساعته و maintenance.
- Redis و observability سنگین profile اختیاری‌اند؛ Kafka، data lake، Kubernetes و share server-side در runtime فعلی نیستند.
- provider واقعی و Open-Meteo فقط از مسیر ingest صریح یا scheduler داخلی قابل فعال‌سازی‌اند؛ API و startup نباید بی‌اجازه provider را صدا بزنند.

## وضعیت الزامات

جزئیات ۱۶ مورد در [requirements-checklist.md](requirements-checklist.md) ثبت شده است. وضعیت کلی موارد قابل بررسی PASS است؛ تنها BLOCKED ثبت‌شده، نبود reference محلی `/workspace/sites/hawatch-weather` است و non-gating محسوب می‌شود.

## validation اجرایی

آخرین validation کد قبل از این به‌روزرسانی مستندات:

- frontend tests: ۲۶ passed
- backend pytest: ۵۷ passed، ۱ skipped
- TypeScript check: passed
- `git diff --check`: passed

این بازبینی هم مستندات/manifest و هم تغییرات runtime مرتبط با period و same-origin gateway را در نظر می‌گیرد؛ تست‌های نرم‌افزار و `git diff --check` باید روی همین وضعیت نهایی اجرا شوند.

## محدودیت‌ها و ابهام‌ها

1. OTP، session و API ورود پیاده نشده‌اند؛ UI ورود فقط این وضعیت را شفاف نشان می‌دهد.
2. Point screenshot مستقل ندارد؛ تطبیق آن pixel-perfect ادعا نمی‌شود.
3. دادهٔ forecast در demo mode واقعی نیست؛ provider واقعی باید صریحاً ingest شود.
4. source قدیمی `/workspace/sites/hawatch-weather` و بعضی reference pathهای `/workspace/scratch` در محیط فعلی قابل‌خواندن نیستند و در `docs/open-questions.md` ثبت شده‌اند.
5. جزئیات domain زمان‌بندی route، share server-side و provider/fallback نهایی هنوز open هستند.
