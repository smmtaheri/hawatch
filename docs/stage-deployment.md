# استیج مستقل هواچ

برنچ `stage` با `scripts/deploy-stage-hawatch` مستقل از `deploy-hawatch` منتشر می‌شود.
سایت اصلی و فرمان production تغییر شاخه، build، migration یا restart نمی‌گیرند.

## فرمان‌ها از سیستم محلی

فرمان‌های سراسری، مستقل از فولدر و برنچ فعلی:

```bash
deploy-stage-hawatch        # انتشار آخرین کامیت‌های ورک‌تری اختصاصی stage
stage-hawatch status        # وضعیت و سلامت؛ فقط‌خواندنی
stage-hawatch down          # خاموش‌کردن بدون حذف دیتابیس/کانتینرها
stage-hawatch up            # روشن‌کردن همان نسخهٔ قبلی، بدون build یا ingest
```

برای نصب/به‌روزرسانی فرمان‌ها، یک‌بار روی سیستم محلی:

```bash
bash /home/nobitex/Desktop/Tasks/Nobitex/hawatch-stage/scripts/install-stage-commands.sh
```

نصاب symlinkهای `~/.local/bin` را به اسکریپت‌های ورک‌تری `hawatch-stage` وصل
می‌کند؛ مسیر بر اساس خود فایل resolve می‌شود، نه cwd. فولدر جاری می‌تواند خانه،
پروژهٔ دیگری یا ورک‌تری مین روی هر برنچی باشد. هیچ checkout/switch/reset روی
برنچ جاری انجام نمی‌شود؛ دیپلوی همیشه فقط از ورک‌تری تمیزِ برنچ `stage` است.
فایل غیر-symlink یا فرمان متعلق به مخزن دیگری overwrite نمی‌شود.

فرمان `stage-hawatch deploy` هم همان دیپلوی است؛ `stage-hawatch` بدون آرگومان
وضعیت را نشان می‌دهد. پیش‌فرض اتصال SSH همان alias موجود `hawatch` است:

```bash
HAWATCH_SSH_HOST=root@SERVER_IP stage-hawatch status
```

wrapper فقط شاخهٔ تمیز `stage` را push می‌کند؛ روی سرور checkout استیج را
fast-forward می‌کند، تنظیمات مستقل را می‌سازد و تصاویر را پیش از جایگزینی سرویس
می‌سازد. مراحل بعدی در SSH انجام می‌شوند؛ نیازی به اجرای دستی فرمان روی سرور نیست.

بعد از پایان موفق، [صفحهٔ توچال استیج](http://202.133.89.120:5050/points/tochal)
را باز کنید. برای تغییر کد حتماً deploy لازم است؛ `up` فقط کانتینرهای موجود را
با همان image و volume قبلی روشن می‌کند. اگر هنوز دیپلوی اولیه انجام نشده، `up`
با پیام «ابتدا deploy-stage-hawatch» متوقف می‌شود و چیزی خودکار ساخته نمی‌شود.

`status` یکی از `UP`، `DOWN`، `PARTIAL`، `UNHEALTHY` یا `NOT DEPLOYED` و جدول شش
سرویس/health/image را چاپ می‌کند. `UP` تنها با سلامت سرویس‌ها و پاسخ وب/API اعلام
می‌شود؛ خطای SSH/Docker به‌جای DOWN، خطا برمی‌گرداند. مشاهدهٔ وضعیت حتی هنگام
دیپلوی فقط‌خواندنی است. deploy/up/down یک قفل مشترک دارند تا هم‌زمان اجرا نشوند.

## داده و سرویس‌ها

- HTTP استیج روی پورت `5050`؛ مسیر `/root/hawatch-stage` و تنظیمات
  `/root/hawatch-stage.env`، پروژهٔ Docker به نام `hawatch-stage`.
- PostgreSQL/PostGIS با database و user `hawatch_stage`، volume مستقل `stage-db`.
  رمز و SECRET_KEY مستقل تولید می‌شوند؛ تنظیمات qa اتصال به دیتابیس production را
  رد می‌کند. تنظیمات قدیمیِ اشاره‌کننده به production بازاستفاده نمی‌شوند.
- تنها در اولین راه‌اندازی دیتابیس خالی، دادهٔ واقعی عمومی catalog/forecast از
  دیتابیس production با transaction **READ ONLY** کپی می‌شود. حساب‌ها، session،
  عضویت، کلیدها و WeatherProxy کپی نمی‌شوند. جدول‌های موجود استیج overwrite نمی‌شوند.
  تا زمان آماده‌شدن کپی اولیه ممکن است مرحلهٔ export/import طول بکشد.
- فرودِ دارای شواهد محلی فقط وقتی زنجیرهٔ canonical مسیر مطابق است اعمال می‌شود.
  فایل GPX و manifest به سرور یا image منتقل نمی‌شوند.
- ingest مستقل Open-Meteo، ده روز داده برای هشت تاریخ قابل انتخاب و ادامهٔ معمول
  مسیرها؛ scheduler مستقل طبق برنامهٔ موجود تهران. انتخاب برنامه درخواست provider
  ایجاد نمی‌کند. بدون proxy اختصاصی، مسیر direct موجود در transport استفاده می‌شود.
- Redis مستقل، سقف ۱۲۸ MB با eviction و بدون persistence؛ دادهٔ اصلی در PostgreSQL.
  بعد از ingest، payload مقصدهای محبوب و مسیرهای featured با سقف ۲۰ مورد هر نوع گرم
  می‌شود. اگر Redis قطع باشد API از DB پاسخ می‌سازد.
- استیج noindex است، admin عمومی بسته است و cookieهای qa از سایت اصلی جدا هستند.

## بررسی پس از دیپلوی، از محلی

آدرس خروجی wrapper را در مرورگر باز کنید. برای بررسی headerها و پاسخ هفته:

```bash
cd /home/nobitex/Desktop/Tasks/Nobitex/hawatch-stage
python3 scripts/check-week-cache.py --base-url http://SERVER_IP:5050
```

`X-Hawatch-Cache: HIT` مربوط به Redis/API است، نه CDN. برای اثبات کش CDN باید
همین بررسی روی آدرس عبوری از CDN انجام شود و headerهای CDN، Age یا dashboard آن
نیز بررسی شود. فقط header Cache-Control اثبات HIT نیست. تغییر تنظیمات CDN در این
milestone اجرا نشده است.

فرمان `stage-hawatch down` فقط کانتینرهای پروژهٔ `hawatch-stage` را متوقف می‌کند؛
هیچ volume، image، شبکه، داده یا فایل تنظیماتی حذف نمی‌شود. helper مستقیم سرور
`scripts/stage-down.sh` نیز به همین کنترل‌کنندهٔ واحد وصل است و دیگر cleanup
تخریبی ندارد. jobهای one-off هدف روشن/خاموش‌کردن نیستند. در این کار، خود فرمان
up/down/deploy روی سرور اجرا نشده؛ فقط status واقعی و سناریوهای شبیه‌سازی‌شده
بررسی شده‌اند.

## بررسی کمینه/بیشینه و شاخص‌های جدید

پس از انتشار، `/points/tochal` و یک مقصد گرم را باز کنید. در «جزئیات تخصصی»،
UV ردیف پیش‌آخر و شاخص گرما ردیف آخر است. جفت کمینه/بیشینه برای روز و بازهٔ
۶/۳ساعته دیده می‌شود و در ۱ساعته حذف می‌شود. گرما برای هوای خنک یا ورودی ناقص
عمداً «—» است؛ عدد ساختگی نشان داده نمی‌شود. تغییر بازه/تم نباید GET هوای تازه
داشته باشد. جزئیات داده و بررسی‌ها در [forecast-indicators.md](forecast-indicators.md).
