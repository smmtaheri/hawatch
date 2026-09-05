# رفتار ورود

## رفتار فعلی

- کلیک روی «ورود» از هر صفحهٔ عمومی route را به `/login?returnTo=…` می‌برد، اما صفحهٔ قبلی را به‌عنوان background حفظ می‌کند.
- روی mobile ورود تمام‌صفحه است؛ روی desktop یک dialog متمرکز است. Back، Escape، backdrop و × همان context قبلی را بازیابی می‌کنند.
- بازکردن مستقیم یا refresh مسیر `/login` یک صفحهٔ کامل و قابل‌بستن نشان می‌دهد.
- برای تست موقت، فقط شماره و کد مجازِ server-side (`DEMO_AUTH_ALLOWED_PHONE` و `DEMO_AUTH_FIXED_OTP`) پذیرفته می‌شوند؛ هیچ مقدار محرمانه‌ای در bundle، متن یا placeholder رابط نیست و درخواست OTP خارجی ارسال نمی‌شود.
- پس از تأیید کد، Django یک session اول‌شخص `HttpOnly` با اعتبار ۳۰ روز می‌سازد. session و مجوز پیش‌بینی در backend اعمال می‌شوند، نه در `localStorage` یا فقط UI.
- در حالت ورود، Header به دکمهٔ «حساب» تبدیل می‌شود. popup مینیمال فقط «حساب کاربری»، «طرح فعلی: عضویت رایگان» و «خروج از حساب» را دارد.
- شماره‌های دیگر و کدهای نادرست بدون ایجاد session رد می‌شوند. این flow آزمایشی است؛ OTP واقعی بعداً فقط جای endpoint ورود را می‌گیرد و قرارداد account/plan را تغییر نمی‌دهد.

## دسترسی forecast و طرح‌ها

- Django Admin → «حساب و دسترسی» → «سیاست دسترسی پیش‌بینی» تنها تنظیم فعال را نگه می‌دارد؛ تغییر آن نیازمند deploy نیست.
- `display_day_count` تعداد tabهای قابل‌نمایش است و از ۷ روز دادهٔ فعلی provider بالاتر نمی‌رود.
- مقدار `visible_days_from_yesterday` عمداً از دیروز شمرده می‌شود: `۰` فقط دیروز، `۱` تا امروز، `۲` تا فردا و به همین ترتیب.
- مهمان، طرح پیش‌فرضِ کاربر واردشده و هر `ForecastPlan` جداگانه قابل تنظیم‌اند. طرح و عضویت کاربر از Django Admin ساخته، فعال/غیرفعال یا منقضی می‌شوند؛ پرداخت آینده فقط یک membership/entitlement فعال می‌کند.
- APIهای forecast تاریخ قفل‌شده را با `403` و بدون payload هوا برمی‌گردانند. پاسخ‌های forecast وابسته به دسترسی `Cache-Control: private, no-store` دارند تا CDN دادهٔ سطح بالاتر را cache عمومی نکند.

## قرارداد لازم پیش از فعال‌سازی OTP واقعی

- اعتبارسنجی شمارهٔ ایران، `POST /api/v1/auth/otp/request`، پیام خطا و rate limit.
- مرحلهٔ verify با پنج خانهٔ نمایشی و یک input واقعی برای paste/autofill.
- `POST /api/v1/auth/otp/verify`، session و redirect امن به `returnTo`.
- expiry، resend و محدودیت retry با متن فارسی و stateهای loading/error.
