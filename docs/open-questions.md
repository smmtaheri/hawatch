# ابهام‌ها و تصمیم‌های باز

تاریخ بررسی: 2026-08-26

این فایل فقط مواردی را ثبت می‌کند که از منابع قابل‌دسترسی قابل اثبات نبودند یا بین منابع اختلاف دارند. هیچ موردی برای پرکردن خلأ evidence حدس زده نشده است.

| ID | وضعیت | سؤال/ابهام | evidence موجود | تصمیم یا ورودی لازم |
| --- | --- | --- | --- | --- |
| OQ-001 | BLOCKED | سورس فعلی `/workspace/sites/hawatch-weather` کجاست و نسخهٔ مرجع آن چیست؟ | مسیر در این محیط وجود ندارد؛ فقط HTML و assetهای منتشرشدهٔ live قابل دریافت‌اند. | طبق تصمیم کاربر reference unavailable ثبت شد و مانع validation/ادامهٔ handoff نیست. |
| OQ-002 | BLOCKED | referenceهای قدیمی در manifest به probe/result و مسیر `/workspace/scratch/...` قابل‌خواندن نیستند. | `design/manifest.json` هنوز مسیرهای قدیمی `visualIdentity`، `openMeteoProbe` و `openMeteoResult` را دارد؛ فایل‌های آن مسیرها در دسترس نیستند. `references/Hawatch.docx` فعلی قابل‌خواندن است. | در این milestone از referenceهای قدیمی استفاده نمی‌شود؛ در صورت نیاز آینده مسیرها اصلاح شوند. |
| OQ-003 | PASS | منظور از «دقیقاً ۱۶ تصویر» ۱۶ asset منطقی است یا ۱۶ فایل فیزیکی؟ | تصمیم قطعی: ۴ صفحه × ۲ تم × ۲ دستگاه = ۱۶ asset. ۱۶ organized copy برای حفظ ساختار تحویل مجاز است؛ مجموع فیزیکی ۳۲ است. | تصمیم ثبت و ابهام رفع شد؛ هیچ تصویری حذف نمی‌شود. |
| OQ-004 | PASS | token canonical کدام است؟ | تصمیم قطعی: `design/tokens/visual-tokens.json` تنها منبع مقدارهاست؛ markdownها فقط توضیح‌دهنده‌اند و مقدار مستقل ندارند. | اختلاف‌های قبلی نسبت به DOCX/live در این validation با canonical بودن JSON حل شد. |
| OQ-005 | PASS | loading در Home، Destination و Route چه UI و timeout/fallback داشته باشد؟ | تصمیم قطعی: skeleton با حفظ layout. | در state contract گزارش‌ها ثبت شد؛ جزئیات timeout آینده است. |
| OQ-006 | PASS | error و retry forecast/API چگونه نمایش داده شود؟ | تصمیم قطعی: پیام خطا داخل همان بخش + retry. | در state contract گزارش‌ها ثبت شد؛ live فعلی این branch را expose نمی‌کند. |
| OQ-007 | PASS | stale/freshness بر چه timestamp، timezone و thresholdی تعیین شود؟ | تصمیم قطعی: دادهٔ قبلی با زمان آخرین بروزرسانی و هشدار کهربایی نمایش داده شود. | در state contract گزارش‌ها ثبت شد؛ threshold/timezone آینده باید با API contract نهایی شود. |
| OQ-008 | NEEDS_USER_DECISION | provider نهایی، fallback و ownership API داخلی چیست؟ | live page-specific bundleها static data دارند و provider/Open-Meteo/API weather call ندارند؛ docs فقط contract آینده‌اند. | provider، backend boundary، fallback و data ownership را تأیید کن. |
| OQ-009 | NEEDS_USER_DECISION | مدل forecast روزها، period دوم و unitها چیست؟ | live UI روزهای گذشته/امروز/آینده و صبح/بعدازظهر دارد؛ contract اجرایی backend موجود نیست. | timezone، horizon، semantics period، unit normalization و missing-data policy را نهایی کن. |
| OQ-010 | NEEDS_USER_DECISION | domain rule محاسبهٔ route plan چیست؟ | bundle از `baseMinutes` و multiplierهای آرام `1.2`، متوسط `1` و سریع `.82` استفاده می‌کند؛ این فقط رفتار deployed sample است. | فرمول timing، توقف، elevation، برگشت و thresholdهای critical را تصویب کن. |
| OQ-011 | NEEDS_USER_DECISION | share link دائمی است یا کوتاه‌عمر و چه داده‌ای encode می‌کند؟ | live copy به payload مسیر `/share?s=...` و Telegram URL می‌رسد؛ policy privacy/expiry/revocation موجود نیست. | expiry، storage، payload schema، privacy و revocation را تعیین کن. |
| OQ-012 | NEEDS_USER_DECISION | empty route/forecast در catalog واقعی چه زمانی و با چه actionی نمایش داده شود؟ | branch `route-empty-state` در Destination bundle هست اما Touchal routeهای فعال دارد و branch در URL مرجع مشاهده نشد. | copy، fallback و معیار نبودن route/forecast را تأیید کن. |
| OQ-013 | NEEDS_USER_DECISION | در mobile، route axis اجازهٔ scroll افقی scoped دارد یا باید layout دیگری داشته باشد؟ | root overflow در ۱۲ حالت مشاهده نشد؛ محدودیت محصول فقط overflow کل صفحه را ممنوع می‌کند. | inner scroll، keyboard/touch behavior و معیار پذیرش آن را مشخص کن. |
| OQ-014 | PASS | Login فقط reference است یا باید live و interactive نیز validate شود؟ | تصمیم قطعی: Login برای مرحلهٔ بعد است؛ چهار screenshot و design doc فعلاً reference هستند. | Login در milestone اول پیاده یا live-validated نمی‌شود. |
| OQ-015 | PASS | آیا می‌توان عدم تغییر فایل خارج از scope را اثبات کرد؟ | baseline اولیه با پیام `chore: add Hawatch design handoff` ساخته و working tree نهایی clean کنترل شد. | تصمیم/کنترل انجام شد. |

## قاعدهٔ ادامهٔ کار

OQهای BLOCKED فقط reference unavailable هستند و طبق تصمیم کاربر مانع ادامهٔ handoff نیستند. OQهای NEEDS_USER_DECISION باقی‌مانده (provider/API، مدل forecast، route timing، share policy و scoped mobile axis) تصمیم‌های آیندهٔ implementation هستند؛ در این milestone هیچ implementation شروع نمی‌شود.
