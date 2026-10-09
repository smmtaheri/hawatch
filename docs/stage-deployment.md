# استیج مستقل هواچ

برنچ `stage` با `scripts/deploy-stage-hawatch` مستقل از `deploy-hawatch` منتشر می‌شود.
سایت اصلی و فرمان production تغییر شاخه، build، migration یا restart نمی‌گیرند.

## فرمان‌ها از سیستم محلی

از worktree استیج که تغییرات در آن commit و push شده‌اند:

```bash
cd /home/nobitex/Desktop/Tasks/Nobitex/hawatch-stage
bash scripts/deploy-stage-hawatch
```

برای نصب نام فرمان دلخواه، یک‌بار روی سیستم محلی:

```bash
cd /home/nobitex/Desktop/Tasks/Nobitex/hawatch-stage
install -Dm755 scripts/deploy-stage-hawatch "$HOME/.local/bin/deploy-stage-hawatch"
"$HOME/.local/bin/deploy-stage-hawatch"
```

پیش‌فرض اتصال SSH همان alias موجود `hawatch` است. اگر لازم باشد از محلی تغییرش دهید:

```bash
HAWATCH_SSH_HOST=root@SERVER_IP bash scripts/deploy-stage-hawatch
```

wrapper فقط شاخهٔ تمیز `stage` را push می‌کند؛ روی سرور checkout استیج را
fast-forward می‌کند، تنظیمات مستقل را می‌سازد و تصاویر را پیش از جایگزینی سرویس
می‌سازد. مراحل بعدی در SSH انجام می‌شوند؛ نیازی به اجرای دستی فرمان روی سرور نیست.

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

فرمان `scripts/stage-down.sh` قدیمی cleanupِ volume انجام می‌دهد؛ برای استیج دارای
دیتابیس مستقل از آن استفاده نکنید مگر عمداً حذف دادهٔ استیج را خواسته باشید.
