# رفتار Route

## ورودی

نمونهٔ اصلی `/routes/touchal-darband` است. route باید parent destination، origin، destination و نقاط مرتب‌شده داشته باشد.

## planner

- date، period، start time و speed پارامترهای تصمیم‌اند.
- تغییر date/period باید point arrival، weather mapping و decision card را هماهنگ update کند.
- periodها در ساعت رسمی `Asia/Tehran` از چهار پنجرهٔ نیمه‌شب ۰۰–۰۶، صبح ۰۶–۱۲، ظهر ۱۲–۱۸ و شب ۱۸–۲۴ استفاده می‌کنند و هرکدام سه برش دوساعته دارند.
- periodهای کاملاً گذشته نسبت به `meta.current_local_time` کم‌رنگ می‌شوند؛ این قاعده به ساعت نمونهٔ خاصی وابسته نیست.
- اگر start_time در URL نباشد و تاریخ/period جاری باشد، gauge روی ساعت فعلی تهران قرار می‌گیرد؛ بخش گذشتهٔ gauge کم‌رنگ و بخش آینده عادی است.
- تغییر start time/speed فقط وقتی `timing_pending` نیست forecast را refetch می‌کند؛ gauge با state محلی فوری حرکت می‌کند و commit با debounce/پایان تعامل انجام می‌شود.
- برای مسیرهای estimated (مثل Tochal v3)، arrival هر نقطه از cumulative متوسط × ضریب زمان pace با گرد ۵ دقیقه‌ای ساخته می‌شود؛ forecast همان WeatherPoint نزدیک به `arrival_at` (±۹۰ دقیقه؛ در تساوی، `forecast_at` زودتر) انتخاب می‌شود. شهرستانک نیز estimated ترکیبی است (نه curated).
- کارت نقطه زمان تقریبی (`حدود …`)، آیکون/شرط/دما/باد و در صورت نیاز نشان `تخمینی · ±N دقیقه` را نشان می‌دهد؛ عنوان period عمومی بالای هر نقطه نیست. `state` فقط از severity پیش‌بینی همان نقطه می‌آید.
- mobile ساعت و speed را در یک row جمع‌وجور نشان می‌دهد.
- فقط یک period control مشترک (نیمه‌شب / صبح / ظهر / شب) برای timeline و cards وجود دارد.
- کلیک روی نقطه → `/points/{weatherPointSlug}` (بدون planner query) + `fromRoute` state شامل pathname/search/href برای بازگشت کامل؛ exception: point مقصدی مثل قلهٔ توچال به `/destination/touchal` canonical می‌رود.
- اگر Destination از Route باز شود و URL خودش `date`/`period` صریح نداشته باشد، forecast اولیه از `date`/`period` موجود در `fromRoute.search` initialize می‌شود؛ `start_time`/`speed` به URL مقصد اضافه نمی‌شوند.
- legacy `/routes/.../points/...` redirect به canonical.

## تصمیم و اشتراک

decision card باید risk point و زمان آن را برجسته کند و امکان کپی/اشتراک را نشان دهد. helper مشترک `buildRouteShareUrl` برای «کپی لینک» و «ارسال در تلگرام» URL canonical با `date`، `period`، `start_time` ASCII و `speed` می‌سازد؛ Telegram از `window.location.href` خام استفاده نمی‌کند. share server-side وجود ندارد.

پایین کارت share فقط تجهیزات پیشنهادی نمایش داده می‌شوند؛ متن‌های توضیحی قدیمیِ
recommendation در UI نمایش داده نمی‌شوند. API برای سازگاری `recommendations` را
نگه می‌دارد و علاوه بر آن `decision.gear` را به‌صورت آرایه‌ای از کلیدهای معنایی
برمی‌گرداند (مثل `hiking-boots`، `water-bottle` و `headlamp`). نگاشت کلید به
نام فارسی و SVG در `GearIcon` و `apps/web/public/icons/gear/` است؛ برای افزودن
وسیلهٔ جدید باید هر دو قرارداد نام و asset به‌روزرسانی شوند.

وقتی timing pending است، متن خام `timing pending` ممنوع است؛ باید پیام فارسی قابل فهم نمایش داده شود و ETA/زمان رسیدن ساختگی نمایش داده نشود.

ردیف آمار کلی تکراری در انتهای صفحهٔ Route نمایش داده نمی‌شود. مقادیر مسافت، صعود، زمان تخمینی و ساعت پایان نباید به‌صورت کارت‌های جداگانه در پایین صفحه render شوند.

## محور و overflow

نقاط مسیر و کارت خلاصهٔ هوای همان نقاط روی یک محور معناشناختی و داخل یک
scroll-owner مشترک قرار می‌گیرند؛ بنابراین marker و کارت متناظر همیشه با هم
حرکت می‌کنند. در web حداکثر شش ستون در viewport دیده می‌شود و نقطه‌های بیشتر
در همان ردیف با اسکرول افقی در دسترس‌اند. در mobile نیز همین ساختار با عرض
فشرده‌تر استفاده می‌شود؛ root صفحه هرگز overflow افقی نمی‌گیرد.
