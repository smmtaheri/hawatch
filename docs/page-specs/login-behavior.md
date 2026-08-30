# رفتار ورود

## رفتار فعلی

- کلیک روی «ورود» از هر صفحهٔ عمومی route را به `/login?returnTo=…` می‌برد، اما صفحهٔ قبلی را به‌عنوان background حفظ می‌کند.
- روی mobile ورود تمام‌صفحه است؛ روی desktop یک dialog متمرکز است. Back، Escape، backdrop و × همان context قبلی را بازیابی می‌کنند.
- بازکردن مستقیم یا refresh مسیر `/login` یک صفحهٔ کامل و قابل‌بستن نشان می‌دهد.
- شمارهٔ موبایل input واقعی است، ولی «دریافت کد ورود» disabled می‌ماند و دلیل آن را اعلام می‌کند. هیچ API، session یا auth mock وجود ندارد.

## قرارداد لازم پیش از فعال‌سازی OTP

- اعتبارسنجی شمارهٔ ایران، `POST /api/v1/auth/otp/request`، پیام خطا و rate limit.
- مرحلهٔ verify با پنج خانهٔ نمایشی و یک input واقعی برای paste/autofill.
- `POST /api/v1/auth/otp/verify`، session و redirect امن به `returnTo`.
- expiry، resend و محدودیت retry با متن فارسی و stateهای loading/error.
