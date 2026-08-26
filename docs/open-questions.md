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
| OQ-008 | OPEN | provider نهایی، fallback و ownership API داخلی چیست؟ | API داخلی محلی با demo mode پیاده شده؛ Open-Meteo هنوز فراخوانی نمی‌شود. | provider واقعی، fallback و ownership را تأیید کن. |
| OQ-009 | PARTIAL | مدل forecast روزها، period و unitها چیست؟ | پنجرهٔ ۷روزه و hourly هر ۲ ساعت در API/UI محلی پیاده شده؛ semantics آینده می‌تواند تغییر کند. | timezone/horizon/unit policy نهایی را در صورت نیاز قفل کن. |
| OQ-010 | PARTIAL | domain rule محاسبهٔ route plan چیست؟ | multiplierهای آرام/متوسط/سریع از sample زنده در seed محلی استفاده می‌شوند. | فرمول timing نهایی محصول را تصویب کن. |
| OQ-011 | OPEN | share link دائمی است یا کوتاه‌عمر؟ | UI اشتراک لینک reconstructable با query params دارد؛ backend share ندارد. | expiry/privacy/revocation را تعیین کن. |
| OQ-012 | PARTIAL | empty route/forecast چه زمانی؟ | empty/error/stale UI محلی پیاده شده؛ catalog فعلی مقصدها/مسیرهای مستند را دارد. | معیار catalog خالی در production را تأیید کن. |
| OQ-013 | PARTIAL | mobile route axis و inner scroll؟ | root overflow در viewportهای مرجع بررسی شده؛ timeline/day tabs می‌توانند inner scroll داشته باشند. | معیار پذیرش نهایی inner scroll را قفل کن. |
| OQ-014 | PASS | Login فقط reference است؟ | Login در milestone اول پیاده نشده است. | بدون تغییر. |
| OQ-015 | PASS | کنترل خارج از scope؟ | design assets و Login docs دست‌نخورده‌اند. | بدون تغییر. |

## قاعدهٔ ادامهٔ کار

OQهای BLOCKED فقط reference unavailable هستند و مانع اجرای محلی نیستند. Login، provider واقعی، Kafka و Kubernetes همچنان خارج از scope این milestone‌اند.
