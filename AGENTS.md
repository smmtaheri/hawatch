# قوانین همکاری در repository هواچ

- نام محصول همیشه «هواچ» است؛ از «هاواچ» استفاده نکن.
- زبان محصول فارسی و layout آن RTL است.
- فونت مرجع محصول Estedad Variable است؛ فایل رسمی self-hosted در `apps/web/public/fonts/estedad-variable.woff2` نگهداری می‌شود و `apps/web/public/fonts/OFL.txt` باید همراه آن باقی بماند.
- هویت بصری فعلی نباید redesign یا با یک زبان بصری جدید جایگزین شود.
- تصاویر `design/screens` قرارداد بصری هستند و باید کنار implementation version شوند.
- هر تغییر برای mobile و desktop باید جداگانه بررسی شود.
- overflow افقی در کل صفحه ممنوع است؛ مخصوصاً در کارت‌های مقصد، روزها، مسیرها و داده‌های ساعتی.
- frontend نباید مستقیماً به provider هواشناسی یا database وصل شود؛ فقط از API داخلی استفاده کند.
- قبل از implementation، README، مستندات مرتبط و screenshotهای مرجع خوانده شوند.
- هر کار مربوط به افزودن مقصد، WeatherPoint، Route یا RoutePoint باید از
  `docs/catalog-onboarding.md` و `docs/catalog-and-weather-validation.md` شروع
  شود؛ این دو سند مرجع اجباری workflow هستند و باید کامل خوانده شوند.
- برای قرارداد یکپارچهٔ هویت، نام‌گذاری، validator و اجرای مرحله‌به‌مرحلهٔ
  local/server، `docs/catalog-contribution.md` نیز باید بعد از دو سند بالا
  کامل خوانده شود. slugهای قدیمی compatibility یا redirect ندارند و نقطهٔ
  canonical مقصد صفحهٔ مستقل `/points/` ندارد.
- هر Destination می‌تواند route-bearing یا destination-only باشد. برای
  destination-only فقط canonical WeatherPoint و forecast لازم است و catalog باید
  `routes: {}` داشته باشد؛ نبود route به‌خودی‌خود خطا نیست. مسیر جاده‌ای آفرود،
  خودرو یا دسترسی تفریحی را به‌عنوان hiking Route جا نزنید. برای چنین مقصدی
  نداشتن GPX مانع انتشار forecast مقصد نیست.
- اگر برای مقصد Route تعریف می‌شود، ابتدا روی local فولدر
  `tracks/<destination-slug>/` ساخته شود و ترک‌ها فقط همان‌جا بررسی شوند. قبل از
  ساخت catalog باید مناسب‌بودن هر ترک برای پیمایش پیاده، پیوستگی مسیر، مبدأ/مقصد
  و شناخته‌شدن مسیر بررسی شود؛ ترک دوچرخه، خودرو، صخره‌نوردی/یخچالی فنی، پراکنده
  یا نامرتبط نباید مبنای distance، ascent یا ETA قرار بگیرد. GPX و manifest هرگز
  commit، image یا سرور نمی‌شوند.
- هر Route عمومی باید حداقل زنجیرهٔ قابل‌شناساییِ مبدأ → یک عارضهٔ واقعیِ میانی
  مستند → مقصد را داشته باشد؛ نقطهٔ generic یا ساختگی برای پرکردن زنجیره اضافه
  نشود. اگر نقطهٔ میانی معتبر پیدا نشد، route تا تکمیل شواهد `pending` بماند.
- بعد از آماده‌کردن WeatherPointهای مقصد جدید، اجرای
  `scripts/validate_open_meteo_catalog.py` قبل از هر import اجباری است. پاسخ
  provider برای تک‌تک نقاط باید elevation، grid نزدیک و دادهٔ ساعتی معتبر
  داشته باشد و اختلاف catalog/DEM نباید از ۱۰۰ متر بیشتر شود؛ هر خطا کل import
  را متوقف می‌کند، نقطهٔ مشکل‌دار و علت باید به درخواست‌کننده گزارش شود و
  `seed_catalog` مستقیم بدون این gate برای onboarding مقصد جدید استفاده نشود.
- هر milestone باید محدود، قابل تست و قابل مقایسه با تصاویر باشد.
- compatibility نسخه‌های Django و DRF با Python 3.14 باید قبل از bump کردن version بررسی شود.
- Login در این milestone پیاده نمی‌شود؛ فایل‌های design و مستندات Login را دست‌نخورده نگه دار.
- تصاویر اصلی را resize، compress، re-encode یا حذف نکن.
