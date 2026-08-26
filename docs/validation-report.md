# گزارش validation و بازبینی repository

تاریخ بررسی: ۱۴۰۵/۰۶/۰۴ برابر با 2026-08-26

## دامنه و نتیجه

بررسی منابع، سایت و repository به‌صورت read-only انجام شد. تنها تغییر محتوایی این اجرا به‌روزرسانی چهار سند validation بود؛ هیچ implementation، dependency installation، migration، build، deploy یا تغییر معماری انجام نشد. سپس baseline اولیهٔ Git طبق درخواست کاربر commit شد.

وضعیت validation این milestone: **PASS**. تصمیم‌های قطعی کاربر اعمال شد، baseline Git ساخته شد و implementation همچنان خارج از scope این milestone است.

منابع live:

- Home: `https://hawatch-weather.admirer135.chatgpt.site/`
- Destination: `https://hawatch-weather.admirer135.chatgpt.site/destination/touchal`
- Route: `https://hawatch-weather.admirer135.chatgpt.site/routes/touchal-darband`

ابزار web داخلی این دامنهٔ preview را با خطای policy ایمنی باز نکرد؛ همان سه URL با `curl` در حالت read-only با HTTP 200 و با Chrome headless/CDP بررسی شدند. این محدودیت ابزار، مانع مشاهدهٔ سایت از مسیر HTTPS جایگزین نشد.

## وضعیت منابع

| منبع | وضعیت | evidence |
| --- | --- | --- |
| `references/Hawatch.docx` | PASS | فایل Microsoft Word معتبر است؛ `word/document.xml` با ۸۱ پاراگراف متنی خوانده شد. |
| `/workspace/sites/hawatch-weather` | BLOCKED (non-gating) | مسیر وجود ندارد؛ طبق تصمیم کاربر به‌عنوان reference unavailable ثبت شده و هیچ claimی به source محلی نسبت داده نشده است. |
| `design/source-screens/` | PASS | ۱۶ PNG با نام‌گذاری شماره‌دار، بدون فایل اضافی. |
| `design/screens/` | PASS | ۱۶ PNG سازمان‌دهی‌شده در مسیر page/theme/device. |
| live site | PASS با محدودیت ابزار | هر سه URL HTTP 200؛ ۱۲ ترکیب light/dark و mobile/desktop با Chrome بررسی شد. |
| Git baseline | PASS | baseline اولیه در همین اجرا با پیام `chore: add Hawatch design handoff` ساخته شد و پس از commit working tree clean کنترل شد. |

## ۱۶ الزام validation

| # | الزام | وضعیت | evidence و دلیل |
| --- | --- | --- | --- |
| 1 | دقیقاً ۱۶ تصویر وجود دارد | PASS | ۱۶ asset منطقی برابر است با ۴ صفحه × ۲ تم × ۲ دستگاه. برای حفظ source و organized، ۱۶ کپی byte-identical نیز وجود دارد؛ مجموع فیزیکی ۳۲ فایل است و این ساختار طبق تصمیم کاربر صحیح است. |
| 2 | تصاویر اصلی در `design/source-screens` بدون تغییر باقی مانده‌اند | PASS | hash هر source با hash ثبت‌شده در `design/manifest.json` و با organized pair متناظر برابر است؛ هر دو مجموعه PNG و ابعاد خود را حفظ کرده‌اند. baseline بیرونی برای اثبات تاریخچه در Git موجود نیست. |
| 3 | تصاویر در مسیر درست page/theme/device قرار دارند | PASS | هر ۱۶ ورودی manifest به مسیر واقعی `design/screens/{home,login,destination,route}/{light,dark}/{mobile,web}.png` resolve می‌شود. |
| 4 | manifest با فایل واقعی، نام و ابعاد مطابقت دارد | PASS | ۱۶ asset در `design/manifest.json`، نام‌ها، page/theme/device، width/height و SHA-256 با فایل‌های واقعی match شدند. |
| 5 | duplicate، missing یا اشتباه‌نام‌گذاری‌شده وجود ندارد | PASS | source hashها ۱۶/۱۶ unique و organized hashها ۱۶/۱۶ unique هستند؛ duplicateهای بین دو مجموعه فقط جفت‌های عمدی source/organized هستند و فایل PNG خارج از scope نیست. |
| 6 | `Hawatch.docx` خوانده و با design system تطبیق داده شده است | PASS | DOCX با ۸۱ پاراگراف خوانده شد. طبق تصمیم کاربر، `design/tokens/visual-tokens.json` منبع canonical مقدارهاست و markdownها فقط توضیح‌دهنده‌اند؛ اصول RTL، Vazirmatn، semantic color، radius و hierarchy با آن ثبت شده‌اند. |
| 7 | مستندات Home، Destination، Route و Login وجود دارد | PASS | `design/pages/{home,destination,route,login}.md` و برای سه صفحهٔ live، `docs/live-page-inspection/{home,destination,route}.md` موجود و non-empty هستند. |
| 8 | layout، متن‌ها، interaction، navigation، state و responsive برای هر صفحه مستند شده‌اند | PASS | page docs و live inspection docs بخش‌های مستقل برای ترتیب، copy، controls، navigation، state، API و responsive دارند؛ stateهایی که live expose نشده‌اند حدس زده نشده و در open questions ثبت شده‌اند. |
| 9 | تفاوت light/dark و mobile/desktop مستند شده است | PASS | برای سه صفحه ۱۲ حالت live در viewportهای 576 و 1905 و هر دو theme بررسی شد؛ چهار جفت screenshot برای هر page و Login نیز در manifest موجود است. |
| 10 | flowهای Home → Destination → Route و back navigation وجود دارد | PASS | `docs/user-flows/home-to-destination.md`، `destination-to-route.md` و `navigation-and-back.md`؛ live linkها و breadcrumb/back نیز ثبت شده‌اند. |
| 11 | API contract اولیه وجود دارد و API پیاده‌سازی نشده است | PASS | `docs/api/api-overview.md` و `forecast-contract.md` قرارداد آینده را ثبت کرده‌اند؛ در `apps/web` و `apps/api` فقط `.gitkeep` وجود دارد و هیچ API اجرایی نیست. |
| 12 | معماری آیندهٔ Django REST، PostgreSQL، Python 3.14 و uv ثبت شده است | PASS | `README.md` و `docs/architecture/{backend,frontend}.md` این targetها و الزام بررسی compatibility را ثبت کرده‌اند؛ compatibility اجرایی در این milestone عمداً اجرا نشده است. |
| 13 | Redis، queue، Kafka/data lake و weather ingestion فقط تصمیم آینده هستند | PASS | `docs/architecture/weather-data-pipeline.md` و `docs/decisions/0002-weather-pipeline-options.md` آن‌ها را future/undecided نگه داشته‌اند؛ infrastructure اجرایی وجود ندارد. |
| 14 | retention حداکثر یک هفته، raw/normalized، cleanup، retry، checkpoint و جلوگیری از اجرای هم‌زمان ثبت شده است | PASS | `docs/architecture/weather-data-pipeline.md` و ADR 0002 همهٔ موارد را شامل می‌شوند؛ هیچ pipeline اجرایی ساخته نشده است. |
| 15 | implementation اجرایی در `apps/web` یا `apps/api` شروع نشده است | PASS | بررسی فایل‌ها نشان داد در این دو مسیر فقط `.gitkeep` هست؛ package، Python module، migration، model، API route یا infrastructure config وجود ندارد. |
| 16 | هیچ فایل خارج از scope تغییر نکرده است | PASS | در این اجرا فقط چهار گزارش validation تغییر محتوایی داده شدند؛ baseline اولیهٔ کل handoff با commit صریح ثبت شد و working tree نهایی clean است. |

## کنترل تصاویر

- source PNG: `16`
- organized PNG: `16`
- مجموع فیزیکی PNG در repository: `32`
- manifest assets: `16`
- source/organized hash match: `16/16`
- manifest hash/dimension match: `16/16`
- source unique hash: `16/16`
- organized unique hash: `16/16`
- PNG خارج از دو مسیر مجاز: `0`
- JSON معتبر برای `design/manifest.json` و `design/tokens/visual-tokens.json`: PASS

هیچ تصویر resize، compress، re-encode یا حذف نشده است.

## live و responsive

در هر سه URL و هر چهار ترکیب light/mobile، dark/mobile، light/desktop و dark/desktop این invariants مشاهده شد:

- `lang=fa` و `dir=rtl`
- viewportهای مرجع 576×1077 و 1905×1047
- root/body بدون overflow افقی
- Home دارای search و catalog؛ Destination دارای day/period و route cards؛ Route دارای day/period/start/speed، point cards و share actions

تعامل‌های ثبت‌شده در live inspection و bundle منتشرشده:

- Home: تغییر theme، جست‌وجوی نتیجه‌دار و empty search
- Destination: انتخاب روز، صبح/بعدازظهر، forecast ساعتی و routeهای دیگر
- Route: انتخاب روز، صبح/بعدازظهر، ساعت شروع، سرعت، محاسبهٔ arrival، نقاط حساس، کپی لینک و Telegram share

loading، forecast/API error و stale-data UI در page-specific live bundle expose نشده‌اند؛ Home empty و Route copy failure مشاهده شده‌اند. contract پذیرفته‌شدهٔ این milestone چنین است: loading با skeleton و حفظ layout، error با پیام داخل همان بخش و retry، stale با نمایش دادهٔ قبلی/آخرین زمان به‌روزرسانی و هشدار کهربایی، و نبود داده با empty/error مستقل. این contract در گزارش‌ها ثبت شده و پیاده‌سازی موجود live تلقی نمی‌شود.

## کنترل عدم implementation

در این بازبینی هیچ command مربوط به build/test/deploy یا نصب dependency اجرا نشد. فایل‌های اجرایی project شامل موارد زیر نیستند:

- `package.json`، lockfile، `pyproject.toml`، `uv.lock`، `manage.py`
- Python/JS/TS/TSX source
- migration، model، API route یا infrastructure config

## شمارش وضعیت‌ها

- PASS: `16`
- FAIL: `0`
- BLOCKED: `0`
- NEEDS_USER_DECISION: `0`

این شمارش فقط ۱۶ الزام جدول بالا را شامل می‌شود.

## نتیجه و اقدام لازم

validation این milestone برای handoff **PASS** است؛ این به معنی شروع implementation نیست. موارد زیر فقط reference یا تصمیم‌های آینده‌اند:

1. source محلی `/workspace/sites/hawatch-weather` unavailable است و طبق تصمیم کاربر مانع ادامه نیست.
2. provider/API، جزئیات forecast، route timing، share policy و scoped mobile axis در open questions به‌عنوان تصمیم‌های future باقی مانده‌اند.
3. هیچ frontend، backend، dependency، migration، build یا deploy در این milestone اضافه نشده است.
