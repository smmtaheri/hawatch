# رفتار Route

## ورودی

نمونهٔ اصلی `/routes/touchal-darband` است. route باید parent destination، origin، destination و نقاط مرتب‌شده داشته باشد.

## planner

- date، period، start time و speed پارامترهای تصمیم‌اند.
- تغییر date/period باید point arrival، weather mapping و decision card را هماهنگ update کند.
- periodها در ساعت رسمی `Asia/Tehran` از پنجره‌های صبح ۰۳–۱۱، بعدازظهر ۱۱–۱۹ و شب ۱۹–۰۳ روز بعد استفاده می‌کنند و هرکدام چهار برش دوساعته دارند.
- periodهای کاملاً گذشته نسبت به `meta.current_local_time` کم‌رنگ می‌شوند؛ این قاعده به ساعت نمونهٔ خاصی وابسته نیست.
- اگر start_time در URL نباشد و تاریخ/period جاری باشد، gauge روی ساعت فعلی تهران قرار می‌گیرد؛ بخش گذشتهٔ gauge کم‌رنگ و بخش آینده عادی است.
- تغییر start time/speed فقط وقتی `timing_pending` نیست forecast را refetch می‌کند؛ gauge با state محلی فوری حرکت می‌کند و commit با debounce/پایان تعامل انجام می‌شود.
- mobile ساعت و speed را در یک row جمع‌وجور نشان می‌دهد.
- فقط یک period control مشترک (صبح / بعدازظهر / شب) برای timeline و cards وجود دارد.
- کلیک روی نقطه → `/points/{weatherPointSlug}` (بدون planner query) + `fromRoute` state شامل pathname/search/href برای بازگشت کامل؛ exception: point مقصدی مثل قلهٔ توچال به `/destination/touchal` canonical می‌رود.
- legacy `/routes/.../points/...` redirect به canonical.

## تصمیم و اشتراک

decision card باید risk point و زمان آن را برجسته کند و امکان کپی/اشتراک را نشان دهد. کپی لینک برنامه در frontend فعلی queryهای قابل‌بازسازی را کپی می‌کند و share Telegram با لینک فعلی ساخته می‌شود؛ share server-side وجود ندارد.

وقتی timing pending است، متن خام `timing pending` ممنوع است؛ باید پیام فارسی قابل فهم نمایش داده شود و ETA/زمان رسیدن ساختگی نمایش داده نشود.

## محور و overflow

نقاط مسیر و کارت خلاصهٔ هوای همان نقاط روی یک محور معناشناختی قرار می‌گیرند؛ دمای تکراری زیر marker حذف می‌شود و عبارت «تغییرات شب · هر دو ساعت» در Route نمایش داده نمی‌شود. اگر عرض کم است، container خود محور می‌تواند scroll شود؛ root صفحه هرگز overflow افقی نگیرد.
