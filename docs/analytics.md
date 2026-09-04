# آمار بازدید داخلی هواچ

هواچ برای ثبت بازدید از ابزار خارجی استفاده نمی‌کند. frontend بعد از هر
navigation در SPA که به یک URL متعارف `/points/<slug>` یا `/routes/<slug>` برسد،
یک درخواست غیرهمزمان و کوتاه به `POST /api/v1/analytics/pageview/` می‌فرستد.
backend فقط slug فعال و موجود را می‌پذیرد و ثبت در یک جدول PostgreSQL با ایندکس
زمان و صفحه انجام می‌شود؛ خطای این درخواست هرگز مانع نمایش صفحه نمی‌شود.

## حریم خصوصی و شمارش

مرورگر یک شناسهٔ تصادفی first-party را در `localStorage` نگه می‌دارد. این شناسه
شخصی یا IP نیست و هر history entry یک `navigation_id` تصادفی دارد. API فقط HMAC
آن شناسه را با `SECRET_KEY` ذخیره می‌کند؛ مقدار خام شناسه، IP، User-Agent یا دادهٔ
شخصی در جدول analytics ذخیره نمی‌شود. ترکیب نوع صفحه، slug، visitor hash و
navigation ID یکتا است، بنابراین retry یا اجرای دوبارهٔ effect همان navigation
را دوبار نمی‌شمارد. در صورت مسدودبودن localStorage، شناسه فقط برای همان navigation
استفاده می‌شود و دقت unique visitor کاهش می‌یابد.

Page View تعداد eventهای یکتای ثبت‌شده است. بازدیدکنندهٔ یکتا تعداد distinct
visitor hashها در همان صفحه و بازه است؛ این مقدار تقریبی است، چون پاک‌شدن storage
یا تعویض مرورگر شناسهٔ جدید می‌سازد. درخواست‌های staff، bot، health check و API
صفحه‌ای ثبت نمی‌شوند و endpoint برای هر visitor در هر دقیقه rate limit پایه دارد.

بازه‌ها بر اساس شروع روز در timezone پروژه (`Asia/Tehran`) محاسبه می‌شوند:
«امروز»، هفت روز تقویمی اخیر (امروز و شش روز قبل)، سی روز تقویمی اخیر و کل زمان.

## مشاهده در Django Admin

پس از ورود به Django Admin، از مسیر **Analytics → Page view events → گزارش بازدید
صفحات** یا URL مستقیم زیر استفاده کنید:

`/admin/analytics/pageviewevent/overview/`

این صفحه همهٔ Point و Routeهای فعال، حتی صفحات با بازدید صفر، نام فارسی، slug،
Page View و Unique Visitor را نشان می‌دهد. نوع صفحه، بازه، معیار و ترتیب صعودی یا
نزولی قابل فیلتر است و کارت خلاصهٔ هر چهار بازه را هم نمایش می‌دهد. مقدار Unique
Visitor در جدول بر مبنای distinct hashهای همان صفحه و در خلاصه بر مبنای distinct
hashهای کل scope انتخاب‌شده محاسبه می‌شود.

برای راه‌اندازی، migration analytics را اعمال کنید. نگهداری یا حذف دوره‌ای eventها
عمداً به تصمیم retention جداگانه موکول شده است.
