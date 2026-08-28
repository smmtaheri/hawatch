# Visual regression handoff — 2026-08-28

این سند نتیجهٔ بازبینی پنج screenshot ارسالی کاربر و تطبیق آن با سورس فعلی است. این تصاویر evidence بازبینی هستند، نه asset مرجع طراحی؛ ۱۶ PNG موجود در `design/source-screens` و `design/screens` باید byte-for-byte حفظ شوند.

## قرارداد اصلاحی

| ناحیه | مشاهده | الزام طراحی/پیاده‌سازی | منبع |
| --- | --- | --- | --- |
| Destination period toggle | بازه‌های سپری‌شده مثل ساعت‌های گذشته کم‌رنگ نیستند | محاسبه از `meta.current_local_time` در `Asia/Tehran`؛ هیچ ساعت نمونهٔ ویژه‌ای مجاز نیست | screenshot + سورس فعلی + درخواست محصول |
| Destination heading | heading/description و timestamp خام فضای اضافی می‌سازند | label دقیق «انتخاب روز»؛ حذف timestamp خام از UI | screenshot + درخواست محصول |
| Point surface | Pas Ghal’eh در dark/light از Destination جدا شده و کارت‌های مسیر باریک/بلندند | shared Destination visual contract؛ related routes compact single-column | screenshot + سورس فعلی |
| Point identity | قلهٔ توچال به صفحهٔ standalone می‌رود | `WeatherPoint(kind=destination)` به Destination canonical resolve شود؛ رکورد و forecast duplicate نشوند | screenshot + سورس فعلی + مدل داده |
| Route timing | `timing pending` به کاربر leak شده و ETA آماده نیست | copy فارسی؛ بدون ETA/arrival ساختگی | screenshot + سورس فعلی |
| Route gauge | مقدار شروع روی default ثابت می‌ماند | در current Tehran period روی ساعت فعلی؛ گذشته dim، آینده عادی | screenshot + سورس فعلی + درخواست محصول |
| Route timeline | دما زیر markerها تکرار شده و hourly عمومی قله دیده می‌شود | marker فقط نام/ترتیب؛ point-level summary cards؛ حذف headline «تغییرات شب · هر دو ساعت» | screenshot + سورس فعلی |
| Point weather data | در `timing_pending` fallback فعلی نمونهٔ ظهر است | کارت point باید از همان point و period انتخاب‌شده باشد؛ fallback ثابت ظهر ممنوع | سورس فعلی + قرارداد forecast |

## سیاست تصویر

- برای Point screenshot مرجع مستقل در handoff اولیه وجود ندارد.
- تصویر جدید بدون منبع معتبر اضافه نمی‌شود.
- مقصد، Point و Route باید با tokenهای `design/tokens/visual-tokens.json` و componentهای مشترک به یک قرارداد بصری برسند.
