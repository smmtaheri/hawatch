# رفتار Route

## ورودی

نمونهٔ اصلی `/routes/touchal-darband` است. route باید parent destination، origin، destination و نقاط مرتب‌شده داشته باشد.

## planner

- date، period، start time و speed پارامترهای تصمیم‌اند.
- تغییر date/period باید point arrival، weather mapping و decision card را هماهنگ update کند.
- periodها در ساعت رسمی `Asia/Tehran` از پنجره‌های صبح ۰۳–۱۱، بعدازظهر ۱۱–۱۹ و شب ۱۹–۰۳ روز بعد استفاده می‌کنند و هرکدام چهار برش دوساعته دارند.
- تغییر start time/speed فقط وقتی `timing_pending` نیست forecast را refetch می‌کند؛ gauge با state محلی فوری حرکت می‌کند و commit با debounce/پایان تعامل انجام می‌شود.
- mobile ساعت و speed را در یک row جمع‌وجور نشان می‌دهد.
- فقط یک period control مشترک (صبح / بعدازظهر / شب) برای timeline و cards وجود دارد.
- کلیک روی نقطه → `/points/{weatherPointSlug}` (بدون planner query) + `fromRoute` state شامل pathname/search/href برای بازگشت کامل.
- legacy `/routes/.../points/...` redirect به canonical.

## تصمیم و اشتراک

decision card باید risk point و زمان آن را برجسته کند و امکان کپی/اشتراک را نشان دهد. کپی لینک برنامه در frontend فعلی queryهای قابل‌بازسازی را کپی می‌کند و share Telegram با لینک فعلی ساخته می‌شود؛ share server-side وجود ندارد.

## محور و overflow

نقاط مسیر و کارت هوا روی یک محور معناشناختی قرار می‌گیرند. اگر عرض کم است، container خود محور می‌تواند scroll شود؛ root صفحه هرگز overflow افقی نگیرد.
