# آمار بازدید داخلی هواچ

هواچ برای ثبت بازدید از ابزار خارجی استفاده نمی‌کند. frontend بعد از هر
navigation در SPA که به یک URL متعارف `/points/<slug>` یا `/routes/<slug>` برسد،
یک درخواست غیرهمزمان و کوتاه به `POST /api/v1/analytics/pageview/` می‌فرستد.
backend فقط slug فعال و موجود را می‌پذیرد و ثبت در یک جدول PostgreSQL با ایندکس
زمان و صفحه انجام می‌شود؛ خطای این درخواست هرگز مانع نمایش صفحه نمی‌شود.
این endpoint فقط پاسخ پذیرش/نادیده‌گرفتن همان event را برمی‌گرداند و هیچ آمار یا
فهرست eventی برای خواندن ارائه نمی‌کند؛ API عمومی read برای analytics وجود ندارد.

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

رویداد خام فقط ۳۰ روز باقی می‌ماند. maintenance موجود Compose، command
`cleanup_analytics_retention` را به‌صورت روزانه به‌عنوان یک بررسی idempotent اجرا
می‌کند؛ command هر بار تمام eventهای عقب‌افتادهٔ قدیمی‌تر از ۳۰ روز را بر اساس ماه
تجمیع و سپس حذف می‌کند. بنابراین اگر چند نوبت maintenance اجرا نشود، اجرای بعدی
همهٔ ماه‌های عقب‌افتاده را امن پوشش می‌دهد. تجمیع‌های ماهانه فقط شمارنده نگه
می‌دارند و Page View را دقیق حفظ می‌کنند؛ Unique Visitor تاریخی جمع distinct هر
ماه است و ممکن است یک visitor را در چند ماه دوباره بشمارد.

بازه‌ها بر اساس شروع روز در timezone پروژه (`Asia/Tehran`) محاسبه می‌شوند:
«امروز»، هفت روز تقویمی اخیر (امروز و شش روز قبل)، سی روز تقویمی اخیر و کل زمان.

## مشاهده در Django Admin

پس از ورود به Django Admin، از مسیر **Analytics → Page view events → گزارش بازدید
صفحات** یا URL مستقیم زیر استفاده کنید:

`/admin/analytics/pageviewevent/overview/`

این صفحه فقط برای superuserهای فعال قابل مشاهده است؛ staff معمولی و کاربران عادی
به آن، فهرست raw eventها یا هیچ endpoint خواندنی دسترسی ندارند. اگر بیش از یک
superuser ساخته شود، همهٔ آن‌ها آمار را می‌بینند. این نسخه allowlist جداگانه‌ای
ندارد و کنترل دسترسی همان superuser است.

این صفحه همهٔ Point و Routeهای فعال، حتی صفحات با بازدید صفر، نام فارسی، slug،
Page View و Unique Visitor را نشان می‌دهد. نوع صفحه، بازه، معیار و ترتیب صعودی یا
نزولی قابل فیلتر است و کارت خلاصهٔ هر چهار بازه را هم نمایش می‌دهد. مقدار Unique
Visitor در جدول بر مبنای distinct hashهای همان صفحه و در خلاصه بر مبنای distinct
hashهای کل scope انتخاب‌شده محاسبه می‌شود؛ در «کل زمان» تجمیع‌های ماهانه هم وارد
می‌شوند و Unique Visitor تاریخی تقریبی است.

برای راه‌اندازی، migration analytics را اعمال کنید. برای اجرای دستی retention:

```bash
docker compose --env-file .env -f infra/compose/compose.yaml exec -T api \
  python manage.py cleanup_analytics_retention --dry-run

docker compose --env-file .env -f infra/compose/compose.yaml exec -T api \
  python manage.py cleanup_analytics_retention
```

دستور دوم فقط eventهای قدیمی را تجمیع و حذف می‌کند و اجرای دوبارهٔ آن تغییری در
دادهٔ قبلاً پردازش‌شده نمی‌دهد.
