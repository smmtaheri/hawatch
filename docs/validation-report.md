# گزارش validation و بازبینی repository

تاریخ به‌روزرسانی: 2026-09-04

## نتیجهٔ فعلی

repository از handoff اولیه عبور کرده و اکنون یک monorepo اجرایی برای pilot است. پیاده‌سازی شامل Home، Point، Route، API داخلی Django/DRF، catalog/search و Compose سبک است. مدل عمومی فقط WeatherPoint و Route/RoutePoint است و پروفایل قدیمی Destination با migration بازنشسته می‌شود. Login به‌صورت UI route-backed (overlay در ورود عادی و صفحهٔ کامل در URL مستقیم) وجود دارد؛ OTP واقعی همچنان خارج از milestone فعلی است.

## منابع

| منبع | وضعیت | توضیح |
| --- | --- | --- |
| `references/Hawatch.docx` | PASS | خوانده شده و اصول RTL، Estedad، palette و hierarchy با design system تطبیق داده شده‌اند. |
| `design/tokens/visual-tokens.json` | PASS | تنها منبع canonical مقدارهای token؛ markdownها توضیح‌دهنده‌اند. |
| `design/source-screens/` و `design/screens/` | PASS | ۱۶ asset منطقی در چهار صفحه، دو theme و دو device؛ sourceها بدون تغییر. |
| live reference URLs | PASS | برای ثبت رفتار و ظاهر reference استفاده شده‌اند؛ رفتار اجرای فعلی از source محلی می‌آید. |
| `/workspace/sites/hawatch-weather` | BLOCKED (non-gating) | در این محیط موجود نیست؛ طبق تصمیم محصول reference unavailable است و اجرای این repository را متوقف نمی‌کند. |

## دارایی‌های تصویری

- چهار صفحهٔ دارای screenshot: Home، Login، Point و Route.
- برای هر صفحه light/dark و mobile/web وجود دارد؛ در مجموع ۱۶ asset منطقی و ۳۲ PNG فیزیکی source/organized وجود دارد.
- manifest نام، مسیر، width، height و SHA-256 را ثبت می‌کند.
- هیچ تصویر جدیدی برای Point ساخته نشده؛ Point به‌صراحت extension سیستم Point است، چون screenshot مرجع مستقل ندارد.

## implementation فعلی

### Frontend

- React + TypeScript + Vite + React Router در `apps/web`.
- Home با جست‌وجوی unified نقطه از مسیر `/api/v1/search/suggestions/?q=`؛ حداقل دو کاراکتر، normalize، تطبیق داخل نام/alias، debounce حدود ۲۰۰ms، keyboard navigation و retry؛ مسیرها در ایندکس نیستند.
- هر WeatherPoint در `/points/{slug}` و هر Route در `/routes/{slug}` صفحهٔ canonical دارد.
- لینک Route → Point تمیز است و `date`، `period`، `start_time` و `speed` در `location.state.fromRoute` برای back context حفظ می‌شوند.
- RTL، Estedad، light/dark، period toggle چهارگانه و سه کارت دوساعته در هر بازه مستند و در source فعلی پشتیبانی می‌شوند.
- Login از هر صفحه با `returnTo` باز می‌شود؛ mobile تمام‌صفحه و desktop dialog است، ولی CTA ارسال OTP تا آماده‌شدن backend غیرفعال می‌ماند.

### Backend و داده

- Django REST با endpointهای health، points، point forecast، route forecast و search suggestions.
- PostgreSQL/PostGIS و migrationهای موجود؛ seed دمو idempotent و catalog جدا از forecast.
- زمان و default selection با `Asia/Tehran`؛ بازه‌ها نیمه‌شب ۰۰/۰۲/۰۴، صبح ۰۶/۰۸/۱۰، ظهر ۱۲/۱۴/۱۶ و شب ۱۸/۲۰/۲۲.
- loading/empty/error/stale/partial در قرارداد UI/API تفکیک شده‌اند؛ stale دادهٔ قبلی و زمان update را نگه می‌دارد و error retry دارد.

### Runtime و مسیر توسعه

- Compose سبک: PostgreSQL/PostGIS، API، frontend production، ingest one-shot، scheduler شش‌ساعته و maintenance.
- Redis و observability سنگین profile اختیاری‌اند؛ Kafka، data lake، Kubernetes و share server-side در runtime فعلی نیستند.
- provider واقعی و Open-Meteo فقط از مسیر ingest صریح یا scheduler داخلی قابل فعال‌سازی‌اند؛ API و startup نباید بی‌اجازه provider را صدا بزنند.

## وضعیت الزامات

جزئیات ۱۶ مورد در [requirements-checklist.md](requirements-checklist.md) ثبت شده است. موارد فنی P0 قابل بررسی PASS هستند؛ reference محلی `/workspace/sites/hawatch-weather` همچنان BLOCKED و non-gating است. گیت provider برای یک ارتفاع آزادکوه در بخش محدودیت‌ها ثبت شده است.

## validation اجرایی

آخرین validation اجرایی این وضعیت:

- frontend Vitest: ۶۷ passed در ۶ فایل
- frontend TypeScript و Vite build: passed
- validator کاتالوگ: ۱۳ فایل، بدون خطا/هشدار
- تست اسکریپت‌های provider/publish: ۸ passed
- Docker Django `check` و `makemigrations --check --dry-run`: بدون تغییر migration و بدون خطای system check
- `compileall` و `git diff --check`: passed
- تست کامل backend عمداً اجرا نشد؛ طبق تصمیم محصول اجرای آن به Compose/PostGIS موکول است. تست‌های فعلی با قرارداد point/route هم‌راستا شده‌اند و اجرای کامل‌شان باید در محیط Compose انجام شود.

## محدودیت‌ها و ابهام‌ها

1. OTP، session و API ورود پیاده نشده‌اند؛ UI ورود فقط این وضعیت را شفاف نشان می‌دهد.
2. Point screenshot مستقل ندارد؛ تطبیق آن pixel-perfect ادعا نمی‌شود.
3. دادهٔ forecast در demo mode واقعی نیست؛ provider واقعی باید صریحاً ingest شود.
4. source قدیمی `/workspace/sites/hawatch-weather` و بعضی reference pathهای `/workspace/scratch` در محیط فعلی قابل‌خواندن نیستند و در `docs/open-questions.md` ثبت شده‌اند.
5. validator Open-Meteo برای آزادکوه: ۱۱ نقطه پاسخ hourly و grid معتبر دارند. ارتفاع canonical قلهٔ `azadkouh` با اتکا به منابع منتشرشده و گزارش تابلوی قله روی ۴۳۵۵ متر تثبیت شده است؛ GLO-90 مقدار ۴۲۶۱ متر برمی‌گرداند و اختلاف ۹۴ متر، داخل سقف ۱۰۰ متر، است. مقدار ۴۳۹۰ متر که در برخی نقشه/پایگاه‌ها آمده به‌عنوان اختلاف منبع ثبت شده، نه مقدار catalog.
6. جزئیات domain زمان‌بندی route، share server-side و provider/fallback نهایی هنوز open هستند.
7. چهار fixture بازگردانده‌شدهٔ علم‌کوه، دماوند، دشت دریاسر و آبشار اسکلیم با
   Open-Meteo GLO-90 DEM و پاسخ hourly اعتبارسنجی شده‌اند. نقطه‌های دارای
   elevation/provenance موقت از nearest cell استفاده می‌کنند تا grid دورتر از
   ۵ کیلومتر انتخاب نشود.
