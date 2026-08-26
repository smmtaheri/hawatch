# checklist الزامات validation

تاریخ: 2026-08-26

این checklist دقیقاً ۱۶ الزام اعلام‌شدهٔ validation را پوشش می‌دهد. وضعیت کلی این milestone **PASS** است؛ implementation همچنان خارج از scope است.

| # | الزام | وضعیت | evidence |
| --- | --- | --- | --- |
| 1 | دقیقاً ۱۶ تصویر وجود دارد | PASS | ۴ صفحه × ۲ تم × ۲ دستگاه = ۱۶ asset منطقی. ۱۶ organized copy نیز برای حفظ ساختار source/organized وجود دارد؛ مجموع فیزیکی ۳۲ و طبق تصمیم کاربر صحیح است. |
| 2 | source screenshots بدون تغییر | PASS | manifest SHA-256 و hash جفت‌های source/organized در `docs/validation-report.md` و `design/manifest.json`. |
| 3 | تصاویر در مسیر page/theme/device درست هستند | PASS | `design/screens/{page}/{light,dark}/{mobile,web}.png` و manifest. |
| 4 | manifest با نام، فایل و ابعاد واقعی match است | PASS | ۱۶/۱۶ asset با filesystem و `identify` match شد. |
| 5 | duplicate/missing/misnamed وجود ندارد | PASS | ۱۶ hash unique در هر مجموعه؛ duplicate بین source/organized فقط pair عمدی است؛ فایل خارج از دو مسیر صفر. |
| 6 | DOCX خوانده و با design system تطبیق داده شده | PASS | `references/Hawatch.docx` با ۸۱ پاراگراف خوانده شد؛ طبق تصمیم کاربر `design/tokens/visual-tokens.json` تنها منبع canonical مقدارهاست و markdownها توضیح‌دهنده‌اند. |
| 7 | مستندات Home/Destination/Route/Login وجود دارد | PASS | `design/pages/{home,destination,route,login}.md` و live inspection سه صفحه. |
| 8 | layout/text/interaction/navigation/state/responsive برای هر صفحه مستند است | PASS | page docs، `docs/live-page-inspection/*` و acceptance/QA docs؛ stateهای مشاهده‌نشده صریحاً ثبت شده‌اند. |
| 9 | light/dark و mobile/desktop مستند است | PASS | ۱۲ حالت live با Chrome در 576 و 1905؛ چهار screenshot برای هر page. |
| 10 | flowهای Home → Destination → Route و back وجود دارد | PASS | `docs/user-flows/home-to-destination.md`، `destination-to-route.md` و `navigation-and-back.md`. |
| 11 | API contract اولیه هست و API پیاده‌سازی نشده | PASS | `docs/api/api-overview.md` و `forecast-contract.md`؛ apps فقط `.gitkeep`. |
| 12 | Django REST/PostgreSQL/Python 3.14/uv ثبت شده | PASS | `README.md` و `docs/architecture/backend.md`؛ compatibility به‌عنوان بررسی آینده ثبت شده. |
| 13 | Redis/queue/Kafka/data lake/ingestion فقط future decision هستند | PASS | `docs/architecture/weather-data-pipeline.md` و ADR 0002؛ runtime ندارند. |
| 14 | retention/raw/normalized/cleanup/retry/checkpoint/no-concurrent ثبت شده | PASS | pipeline doc و ADR 0002. |
| 15 | implementation در `apps/web` یا `apps/api` شروع نشده | PASS | هیچ package/source/migration/model/API اجرایی وجود ندارد؛ فقط `.gitkeep`. |
| 16 | هیچ فایل خارج از scope تغییر نکرده | PASS | فقط چهار سند validation تغییر محتوایی داده شدند؛ baseline اولیه با پیام تعیین‌شده ساخته و working tree نهایی clean کنترل شد. |

## جمع وضعیت‌ها

- PASS: `16`
- FAIL: `0`
- BLOCKED: `0`
- NEEDS_USER_DECISION: `0`

## موارد non-gating و تصمیم‌های آینده

- `/workspace/sites/hawatch-weather` قابل‌دسترسی نیست و به‌عنوان reference unavailable ثبت شده است؛ طبق تصمیم کاربر مانع ادامه نیست.
- provider/API، جزئیات forecast، route timing، share policy و scoped mobile axis در open questions برای implementation آینده باقی مانده‌اند.
- Login برای مرحلهٔ بعد است و در milestone اول پیاده یا live-validated نمی‌شود.

تا تعیین این موارد، implementation، dependency، migration، build، deploy و commit انجام نمی‌شود.
