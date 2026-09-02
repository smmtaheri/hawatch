# ابهام‌ها و تصمیم‌های باز

تاریخ بررسی: 2026-08-28

این فایل فقط مواردی را ثبت می‌کند که از منابع قابل‌دسترسی قابل اثبات نبودند یا بین منابع اختلاف دارند. هیچ موردی برای پرکردن خلأ evidence حدس زده نشده است.

| ID | وضعیت | سؤال/ابهام | evidence موجود | تصمیم یا ورودی لازم |
| --- | --- | --- | --- | --- |
| OQ-001 | BLOCKED | سورس فعلی `/workspace/sites/hawatch-weather` کجاست و نسخهٔ مرجع آن چیست؟ | مسیر در این محیط وجود ندارد؛ فقط HTML و assetهای منتشرشدهٔ live قابل دریافت‌اند. | طبق تصمیم کاربر reference unavailable ثبت شد و مانع validation/ادامهٔ handoff نیست. |
| OQ-002 | BLOCKED | probe/result تاریخی Open-Meteo و sourceهای `/workspace/scratch/...` در checkout فعلی موجود نیستند. | `references/Hawatch.docx` موجود و قابل‌خواندن است؛ manifest اکنون به همین فایل repository اشاره می‌کند و pathهای تاریخی probe/result را نگه نمی‌دارد. | در این milestone به probe/result تاریخی نیاز نیست؛ اگر برای مقایسهٔ عددی لازم شد باید دوباره ارائه شوند. |
| OQ-003 | PASS | منظور از «دقیقاً ۱۶ تصویر» ۱۶ asset منطقی است یا ۱۶ فایل فیزیکی؟ | تصمیم قطعی: ۴ صفحه × ۲ تم × ۲ دستگاه = ۱۶ asset. ۱۶ organized copy برای حفظ ساختار تحویل مجاز است؛ مجموع فیزیکی ۳۲ است. | تصمیم ثبت و ابهام رفع شد؛ هیچ تصویری حذف نمی‌شود. |
| OQ-004 | PASS | token canonical کدام است؟ | تصمیم قطعی: `design/tokens/visual-tokens.json` تنها منبع مقدارهاست؛ markdownها فقط توضیح‌دهنده‌اند و مقدار مستقل ندارند. | اختلاف‌های قبلی نسبت به DOCX/live در این validation با canonical بودن JSON حل شد. |
| OQ-005 | PASS | loading در Home، Destination، Route و Point چه UI و timeout/fallback داشته باشد؟ | تصمیم قطعی: skeleton با حفظ layout. | در state contract گزارش‌ها ثبت شد؛ جزئیات timeout آینده است. |
| OQ-006 | PASS | error و retry forecast/API چگونه نمایش داده شود؟ | تصمیم قطعی: پیام خطا داخل همان بخش + retry؛ search نیز query را حفظ می‌کند. | در state contract گزارش‌ها ثبت شد؛ live فعلی همهٔ branchها را expose نمی‌کند. |
| OQ-007 | PASS | stale/freshness بر چه timestamp، timezone و thresholdی تعیین شود؟ | تصمیم قطعی: دادهٔ قبلی با زمان آخرین بروزرسانی و هشدار کهربایی نمایش داده شود. | در state contract گزارش‌ها ثبت شد؛ threshold/timezone آینده باید با API contract نهایی شود. |
| OQ-008 | OPEN | provider نهایی، fallback و ownership API داخلی چیست؟ | API داخلی محلی با demo mode پیاده شده؛ مسیر Open-Meteo/ingest command وجود دارد اما از API یا startup خودکار فراخوانی نمی‌شود. | provider واقعی، fallback و ownership را تأیید کن. |
| OQ-009 | PASS | مدل forecast روزها، period و unitها چیست؟ | پنجرهٔ ۷روزه، timezone رسمی `Asia/Tehran` و سه پنجرهٔ ثابت با چهار برش دوساعته در API/UI محلی پیاده شده است. | صبح ۰۳–۱۱، بعدازظهر ۱۱–۱۹ و شب ۱۹–۰۳ روز بعد؛ انتخاب پیش‌فرض بر اساس ساعت تهران است. |
| OQ-010 | PARTIAL | domain rule محاسبهٔ route plan چیست؟ | Tochal v3: هر پنج مسیر estimated. Kalkchal هندسهٔ کامل GPX با timestamp مصنوعی؛ Shahrestanak برآورد ترکیبی estimated (نه curated). GPX فقط evidence داخلی آفلاین است. ارتفاع `velenjak_parking` با waypoint/report و DEM cross-check شده اما provisional است. | کالیبراسیون میدانی و ورودی per-segment. |
| OQ-011 | OPEN | share link دائمی است یا کوتاه‌عمر؟ | UI اشتراک لینک reconstructable با query params دارد؛ backend share ندارد. | expiry/privacy/revocation را تعیین کن. |
| OQ-012 | PARTIAL | empty route/forecast چه زمانی؟ | empty/error/stale UI محلی پیاده شده؛ catalog فعلی مقصدها/مسیرهای مستند را دارد. | معیار catalog خالی در production را تأیید کن. |
| OQ-013 | PARTIAL | mobile route axis و inner scroll؟ | root overflow در viewportهای مرجع بررسی شده؛ timeline/day tabs می‌توانند inner scroll داشته باشند. | معیار پذیرش نهایی inner scroll را قفل کن. |
| OQ-014 | PARTIAL | ورود پیامکی چه زمانی فعال می‌شود؟ | UI route-backed ورود (mobile تمام‌صفحه، desktop dialog و `returnTo`) پیاده شده، اما API/session/OTP وجود ندارد. | قرارداد OTP، rate limit، expiry و session قبل از فعال‌کردن CTA تعیین شود. |
| OQ-015 | PASS | کنترل خارج از scope؟ | PNGهای canonical دست‌نخورده‌اند؛ دو reference تکمیلی ورود ثبت شده و Point بدون screenshot بی‌منبع به‌عنوان extension مستند شده است. | بدون تغییر. |

## قاعدهٔ ادامهٔ کار

OQهای BLOCKED فقط reference unavailable هستند و مانع اجرای محلی نیستند. OTP واقعی، provider واقعی، Kafka و Kubernetes همچنان خارج از scope این milestone‌اند.
