# آمار بازدید داخلی هواچ

## اتصال پایه به GA4

آمار داخلی بالا مرجع مستقل هواچ باقی می‌ماند. GA4 فقط برای page viewهای عمومی
استفاده می‌شود و رویداد اختصاصی هواچ به آن ارسال نمی‌کند. تنظیم runtime با
متغیر عمومی `GA4_MEASUREMENT_ID` انجام می‌شود؛ مقدار فعلی stream برابر
`G-B9F7GYQ0X8` است. آن را در `.env` کنار فایل Compose بگذارید:

```dotenv
GA4_MEASUREMENT_ID=G-B9F7GYQ0X8
```

در production این فایل روی سرور، معمولاً `/root/hawatch/.env`، تنظیم می‌شود.
همان متغیر به‌صورت runtime از طریق `env_file` به API/Django می‌رسد و Compose آن
را هنگام build وب به `VITE_GA4_MEASUREMENT_ID` می‌دهد. Django شناسه را در HTML
صفحات SSR می‌گذارد؛ bundle هم آن را برای مسیرهای عمومی‌ای که از پوستهٔ استاتیک
React می‌آیند می‌خواند. اسکریپت deploy فایل `.env` موجود را جایگزین نمی‌کند؛ در
سرورهای فعلی این خط باید پیش از deploy کد اضافه شود تا هم image وب با شناسه ساخته
شود و هم API آن را هنگام شروع بعدی بخواند. در توسعهٔ محلی می‌توان متغیر را خالی
گذاشت. مقدار غایب/نامعتبر بی‌صدا GA4 را غیرفعال می‌کند.

GA4 فقط در build production، روی `https://hawatch.ir` یا
`https://www.hawatch.ir` و بیرون از preview فعال می‌شود. Vite dev server،
localhost، HTTP، preview/QA و صفحات خارج از مسیرهای عمومی مجاز هیچ اسکریپت یا
درخواستی به Google نمی‌فرستند.

React Router مسیرهای عمومی خانه، فهرست مقصدها/مسیرها، صفحهٔ اشتراک، نقطه و مسیر
را دنبال می‌کند؛ صفحهٔ login که به خانه redirect می‌شود و صفحات ناموجود در این
allowlist نیستند. تغییر query یا hash به‌تنهایی
page view نیست. مسیر فقط بعد از آماده‌شدن عنوان React ثبت می‌شود. HTML SSR صفحهٔ
مستقیم عنوان آماده را از قبل دارد؛ صفحهٔ نقطه/مسیر در ناوبری SPA تا دریافت نام
واقعی همان مقصد صبر می‌کند. بازکردن مستقیم، refresh و هر انتقال واقعی مسیر از
جمله Back/Forward یک page view می‌سازند. تکرار effect در React StrictMode و
تغییر query/filter با coordinator هر مسیر حذف می‌شود. عنوان از `document.title`
همان لحظهٔ آماده‌شدن و URL فقط از origin و pathname عمومی ساخته می‌شود؛ query،
hash و referrer بیرونی مرورگر هرگز فرستاده نمی‌شوند. ایمیل، شماره و عبارت‌های
credential-like نیز از title ارسالی حذف می‌شوند. برای پیمایش داخلی در GA، فقط
pathname عمومی صفحهٔ قبلی به‌عنوان referrer مجازی استفاده می‌شود؛ referrer بیرونی
در بازدید اول خالی است.

در Google tag روی GA Signals و ad personalization سیگنال خاموش‌اند. کد
`send_page_view: false` را به `config` می‌دهد و `page_view` را دستی ثبت می‌کند.
در کد فعلی پروژه cookie-consent/CMP یا تنظیم Consent Mode پیدا نشد؛ این اتصال
موجودیت آن را تغییر نمی‌دهد. اگر سیاست محصول/حوزهٔ فعالیت به رضایت پیشینی نیاز
دارد، باید CMP/Consent Mode جداگانه طراحی شود، نه اینکه این پیاده‌سازی را به‌جای
رضایت تلقی کنیم.

### تنظیمات پنل GA4

برای جلوگیری از تکرار و جمع‌آوری URLهای queryدار، در **Admin → Data streams →
web stream هواچ → Enhanced measurement** کل Enhanced Measurement را فعلاً خاموش
کنید. کد هواچ page view را دستی می‌فرستد؛ GA4 همچنان رویدادهای پایهٔ خودش مثل
`session_start`، `first_visit` و `user_engagement` را طبق رفتار معمول ثبت می‌کند.
بعداً اگر scroll/click/download هم خواستید، می‌توانیم گزینه‌های لازم را جدا
فعال کنیم، اما ثبت خودکار Page views و به‌ویژه **Page changes based on browser
history events** نباید همزمان با ثبت دستی فعال باشد. این قاعده با راهنمای رسمی
Google برای page view دستی در SPA هم‌راستاست.

### تأیید پس از deploy

1. در سرور، خط `GA4_MEASUREMENT_ID=G-B9F7GYQ0X8` را به `.env` اضافه و deploy
   عادی کد را اجرا کنید؛ این متغیر را در فایل‌های frontend یا HTML ثابت نگذارید.
2. در Chrome DevTools → Network، فیلتر `gtag/js` را بزنید و صفحهٔ عمومی را
   باز کنید. باید حداکثر یک بار `gtag/js?id=G-B9F7GYQ0X8` بارگیری شود؛ درخواست‌های
   `collect` باید `en=page_view` و `dl` تمیز بدون `?`/`#` داشته باشند. اولین
   `dr` خالی و referrerهای بعدی فقط URL داخلیِ بدون query باشند.
3. برای DebugView، از **Tag Assistant → Troubleshoot tag** حالت debug را فقط
   برای مرورگر خودت فعال کن و در GA4 **Admin → DebugView** برو. DebugView باید
   برای خانه → مقصدها → نقطه → مسیر، و نیز Back/Forward یک `page_view` با
   `page_title` و `page_location` همان صفحه نشان دهد؛ تغییر تاریخ/ساعت/سرعت
   نباید event جدید بسازد. Refresh باید یک event جدید برای بارگذاری جدید بسازد.
4. در **Reports → Realtime** بعد از چند ثانیه همان session و page viewها را
   ببینید. تأیید دریافت واقعی در DebugView/Realtime نیازمند دسترسی شما به
   property GA4 است؛ تست کد به‌تنهایی تحویل داده‌شدن event به Google را اثبات
   نمی‌کند.

اگر Google، افزونهٔ مسدودکننده یا شبکه درخواست را رد کند، خطای script به‌صورت
بی‌صدا مدیریت می‌شود، صف موقت پاک می‌شود و تلاش مجدد خودکار انجام نمی‌شود؛ UI و
درخواست‌های Open-Meteo وابستگی‌ای به بارگیری GA ندارند.

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

کارت‌های «مقصدهای محبوب» هوم از چهار مقصد مستقل و indexable با بیشترین
بازدیدکنندهٔ یکتای ثبت‌شده در همین بازهٔ هفت‌روزه ساخته می‌شوند. شمارش فقط رویداد
صفحهٔ مقصد (`point`) را می‌پذیرد؛ بازدید مسیرها و نقاط فنی مسیر در رتبه‌بندی نیست.
در تساوی، ترتیب curated کاتالوگ و سپس slug ترتیب پایدار را می‌سازد. نتیجهٔ کوچک
هوم پنج دقیقه در Redis نگه‌داری می‌شود و HTML اولیه آن را به فرانت می‌دهد تا
نمایش کارت‌ها به درخواست جداگانهٔ فهرست نقاط وابسته نباشد.

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
