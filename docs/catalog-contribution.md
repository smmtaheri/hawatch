# قرارداد واحد افزودن مقصد، مسیر و نقطه

این سند مسیر مرجع برای هر مقصد جدید است. کاتالوگ JSON ورودی قابل بازتولید است؛
دیتابیس منبع حقیقت runtime است. در این مرحله SEO عمومی و redirect قدیمی نداریم:
slug جدید canonical است و URL قبلی عمداً ممکن است 404 شود.

## ۱. اطلاعات لازم

برای هر مقصد:

- `destination.slug` یکتا، نام فارسی، `category_key`، منطقه، مختصات WGS84،
  ارتفاع و منبع ارتفاع، `climate`، تصویر و alt؛
- یک WeatherPoint با همان مختصات/ارتفاع و `kind: "destination"`؛ این رکورد برای
  forecast لازم است اما صفحهٔ عمومی آن `/points/` نیست و به `/destination/` تعلق دارد؛
- اگر مسیر پیادهٔ معتبر نداریم، `routes: {}` کافی است. مسیر آفرودی، خودرو،
  دوچرخه یا صخره‌نوردی را hiking route ثبت نکنید.

برای هر WeatherPoint مستقل:

- slug انگلیسی lowercase با hyphen، بدون underscore، `name` و `short_label`؛
- `page_name` یکتا و قابل جست‌وجوی مستقل، `place_type`، `identity_summary`؛
- `importance` یکی از `primary`/`support` و `name_status` یکی از
  `official`/`established`/`descriptive`؛
- `aliases` برای شکل‌های رایج جست‌وجو و `source_urls` برای منابع هویت/موقعیت؛
- مختصات دقیق و `elevation_m` معتبر به‌همراه `elevation_source` یا evidence.

`page_name` نباید عبارت عمومی مثل «استراحتگاه مسیر» یا «شیب نهایی قله» باشد.
نام باید عارضهٔ واقعی را با زمینهٔ مقصد مشخص کند؛ برای مثال «پناهگاه سیمرغ
دماوند» یا «روستای کلاک بالا». نقطهٔ destination canonical در slug داخلی خود
می‌تواند underscore داشته باشد چون صفحهٔ مستقل ندارد؛ این استثنا فقط برای همان
رکورد canonical مقصد است.

## ۲. ترک و نقاط مسیر

در شروع کار agent باید این فولدر را در checkout محلی بسازد:

```bash
cd /path/to/hawatch
mkdir -p tracks/<destination-slug>
```

هر ترک باید مسیر پیادهٔ شناخته‌شده و پیوسته‌ای با مبدأ و مقصد مشخص باشد. ترک
دوچرخه، خودرو، موتور، مسیر صخره‌نوردی/یخچالی فنی، ترک پراکنده یا مسیر نامرتبط
برای route قابل قبول نیست. اگر یک ترک نزولی است، فقط پس از تعیین جهت و تطبیق
با منبع مستقل می‌توان آن را برعکس تحلیل کرد؛ timestamp و ارتفاع خام GPX به‌تنهایی
حقیقت نیستند.

برای route اصلی ترجیحاً دو ترک مستقل تطبیق داده شود. هر route عمومی باید حداقل
زنجیرهٔ `مبدأ → یک عارضهٔ واقعی میانی → مقصد` داشته باشد. نقطهٔ ساختگی یا generic
برای پرکردن این زنجیره اضافه نشود؛ اگر landmark میانی اثبات نشده، route pending
بماند.

نام فایل دانلودی را قبل از تحلیل روشن کنید:
`<destination>-<side>-<origin>-to-<target>-<year>.gpx`.
فایل‌ها و `manifest.json` در `.gitignore` هستند و هرگز commit، image یا server
نمی‌شوند. manifest فقط mapping فایل، route، منبع و نقش `primary`/`crosscheck`
را نگه می‌دارد.

## ۳. ساخت و اعتبارسنجی محلی

از ریشهٔ repository:

```bash
python3 scripts/analyze_route_tracks.py \
  --manifest tracks/<destination-slug>/manifest.json \
  --catalog /tmp/<destination-slug>_v1.json

python3 scripts/validate_open_meteo_catalog.py \
  --catalog /tmp/<destination-slug>_v1.json
```

دستور دوم برای تک‌تک pointها Open-Meteo را read-only صدا می‌زند و وجود elevation،
grid معتبر، hourly data و فاصلهٔ grid تا مختصات را بررسی می‌کند. اختلاف catalog و
DEM بیشتر از ۱۰۰ متر، grid دورتر از ۵ کیلومتر، پاسخ ناقص یا خطای هر point یعنی
کل import متوقف می‌شود؛ مختصات/ارتفاع آن point باید اصلاح یا از catalog حذف شود.
GPX برای forecast لازم نیست، ولی برای distance/ascent/ETA و یافتن landmark لازم
است.

سپس قرارداد هویت و route را بررسی کنید:

```bash
cd apps/api
uv run python manage.py validate_catalog --file catalog/<file>.json
uv run python manage.py validate_catalog --all --strict
```

این validator duplicate slug، underscore، page name/alias collision، metadata
ناقص، coordinate/elevation نامعتبر، route کمتر از سه نقطه، reference شکسته و
sort order تکراری را گزارش می‌کند. با `--database`، دیتابیس فعلی نیز read-only
بررسی می‌شود:

```bash
uv run python manage.py validate_catalog --all --database --strict
```

## ۴. واردکردن روی local

```bash
cd apps/api
uv run python manage.py migrate
uv run python manage.py seed_catalog --file catalog/<file>.json --strict
uv run python manage.py ingest_open_meteo --slugs <point-1>,<point-2>
uv run python manage.py catalog_preflight --destination <destination-slug> --require-forecast --strict
```

`seed_catalog` اتمیک و idempotent است. `--prune` فقط وقتی استفاده شود که حذف
رکوردهای fixture-managed عمداً بررسی شده باشد. پس از ingest، preflight باید برای
همهٔ pointهای مقصد `provider_checked` و forecast قابل استفاده نشان دهد. پیش‌بینی
از DB خوانده می‌شود؛ frontend مستقیماً Open-Meteo را صدا نمی‌زند.

## ۵. import به سرور از روی local

فایل را روی سرور کپی نکنید؛ از stdin بفرستید. حالت استاندارد شامل validation
محلی، check راه دور، import، ingest هدفمند و preflight است:

```bash
cd /path/to/hawatch
python3 scripts/publish_catalog.py \
  --catalog /tmp/<destination-slug>_v1.json \
  --host hawatch \
  --destination <destination-slug> \
  --apply
```

`hawatch` همان alias SSH است. اگر route عمداً timing ندارد، انتشار فقط با تصمیم
صریح و `--allow-pending-timing` مجاز است؛ در این حالت forecast نقطه‌ها می‌آید
ولی arrival weather مسیر ساخته نمی‌شود. بدون `--apply` همین دستور فقط check می‌کند
و هیچ writeای ندارد.

پس از import، برای تغییر مقصدهای محبوب فقط از command ادمین استفاده کنید؛ مقصد
جدید خودکار روی Home نمی‌رود:

```bash
uv run python manage.py set_popular_destinations --slugs a,b,c,d
```

حداکثر چهار مقصد محبوب است. همهٔ مقصدهای فعال در search قابل پیدا شدن‌اند، اما
صفحهٔ Home فقط همین چهار مورد را نشان می‌دهد.

## ۶. کنترل‌های اجباری بعد از تغییر

قبل از commit، این موارد باید pass شوند:

```bash
cd /path/to/hawatch
git diff --check
PYTHONPATH=apps/api/src python3 -m compileall -q apps/api/src
cd apps/api && uv run python manage.py makemigrations --check
uv run pytest
```

همچنین با `git grep` مطمئن شوید slug قدیمی در catalog، API، frontend و docs
فعلی نمانده است. migrationهای تاریخی تنها سابقهٔ بازپخش schema هستند و نباید
برای compatibility URL جدید استفاده شوند. بعد از افزودن رکورد، SEO/sitemap
عمومی در milestone جداگانه روی همین `page_name` و slug canonical ساخته می‌شود.
