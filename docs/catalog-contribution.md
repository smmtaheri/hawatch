# قرارداد واحد افزودن نقطه و مسیر

این سند مسیر مرجع برای هر نقطه جدید است. کاتالوگ JSON ورودی قابل بازتولید است؛
دیتابیس منبع حقیقت runtime است. redirect قدیمی نداریم: slug جدید canonical است
و URL قبلی عمداً ممکن است 404 شود. SEO عمومی P0 با gate `seo_indexable` و
sitemap نقطه/مسیر در همین قرارداد فعال است.

## مالکیت catalog و افزودن نقطهٔ جدید

قبل از نوشتن JSON مشخص کنید نقطهٔ جدید مالک کدام catalog است. هر slug نقطه و هر
slug مسیر باید در کل پوشهٔ `apps/api/fixtures/catalog/` فقط یک مالک داشته باشد:

- نقطهٔ مستقل را دقیقاً یک‌بار در `weather_points` فایل مالک تعریف کنید؛ اگر در
  مسیر catalog دیگری استفاده می‌شود، آن را دوباره تعریف نکنید و فقط در
  `shared_weather_points` و `routes.*.points` با همان slug ارجاع دهید.
- اگر نقطهٔ جدید به یک catalog موجود اضافه می‌شود، همان فایل فعال را ویرایش کنید
  و `catalog_version` را به نسخهٔ بعدی تغییر دهید. فایل نسخهٔ قبلی را کنار فایل
  جدید در پوشهٔ fixture نگه ندارید؛ loader عمداً مالکیت تکراری را خطا می‌کند.
  تاریخچهٔ نسخهٔ قبلی در Git باقی می‌ماند.
- اگر نقطه بدون مسیر است، فقط canonical WeatherPoint را اضافه کنید و
  `routes: {}` بگذارید. برای آن GPX، Route یا نقطهٔ میانی ساختگی اضافه نکنید.
- اگر نقطه مسیر دارد، هر Route باید زنجیرهٔ واقعی مبدأ → landmark مستند → نقطه
  داشته باشد. route جاده‌ای/خودرویی/فنی را hiking route ثبت نکنید.
- نقاط یک Route را از نظر فاصلهٔ مختصات canonical، مخصوصاً نقاط متوالی، بررسی
  کنید. نقطه‌ای که کمتر از ۱۰۰ متر با نقطهٔ همان مسیر فاصله دارد باید landmark
  مستقل، نام روشن و ارزش واقعی برای کاربر (اطلاعات/هوا یا مرحلهٔ متفاوت) داشته
  باشد؛ صرفاً waypoint نزدیک یا تقسیم مصنوعی مسیر کافی نیست. فاصلهٔ کمتر از ۲۵
  متر duplicate محسوب می‌شود و باید merge شود؛ بازهٔ ۲۵ تا ۱۰۰ متر فقط با
  بررسی و ثبت علت روشن در `reviewed_nearby_point_pairs` مجاز است.
- slug باید lowercase، hyphenated، بدون underscore و پایدار باشد؛ `page_name`
  نیز در تمام catalogها یکتا و زمینه‌دار باشد. تمام نقاط فعال عمومی
  `seo_indexable: true` دارند و نقطهٔ جدید خودکار محبوب Home نمی‌شود.

بعد از تغییر، validator provider و catalog را اجرا کنید، سپس برای انتشار روی
دیتابیس موجود ابتدا `sync_catalog --dry-run` و بعد `sync_catalog --apply` را
استفاده کنید. این sync همهٔ catalogهای package‌شده را با هم و به‌صورت atomic
همگام می‌کند؛ رکوردهای دستی را overwrite نمی‌کند. `publish_catalog.py` برای
ارسال یک catalog موقت از stdin مناسب است، اما جایگزین ثبت fixture versioned در
repository نیست.

## ۱. اطلاعات لازم

برای هر نقطه:

- `point.slug` یکتا، نام فارسی، `category_key`، منطقه، مختصات WGS84،
  ارتفاع و منبع ارتفاع، `climate`، تصویر و alt؛
- همان WeatherPoint با همان مختصات/ارتفاع؛ نقطهٔ شاخص `kind: "primary"` و سایر
  نقاط `kind: "shared"` یا `kind: "route_point"` می‌گیرند. همین رکورد تنها
  هویت عمومی نقطه و منبع forecast است و به `/points/{slug}` می‌رود؛
- اگر مسیر پیادهٔ معتبر نداریم، `routes: {}` کافی است. مسیر آفرودی، خودرو،
  دوچرخه یا صخره‌نوردی را hiking route ثبت نکنید.

برای هر WeatherPoint مستقل:

- slug انگلیسی lowercase با hyphen، بدون underscore، `name` و `short_label`؛
- `page_name` یکتا و قابل جست‌وجوی مستقل، `place_type`، `identity_summary`؛
- نام نقطه باید زمینه‌دار و از نظر جست‌وجو مستقل باشد. نام‌هایی مثل «تپهٔ
  گوگردی» یا «استراحتگاه» به‌تنهایی قابل انتشار نیستند؛ آن‌ها را به شکل
  «تپهٔ گوگردی دماوند» یا «استراحتگاه مسیر شمالی علم‌کوه» بنویسید تا با نقاط
  مشابه قاطی نشوند. اگر چنین نام یکتایی برای عارضه وجود ندارد، نقطه را اضافه
  نکنید و صرفاً برای بهترشدن SEO نام ساختگی نسازید.
- `importance` یکی از `primary`/`support` و `name_status` یکی از
  `official`/`established`/`descriptive`؛
- `climate` باید یکی از profileهای demo (`alpine`، `desert`، `forest_fog`، `high_alpine`، `lake_valley` یا `meadow`) باشد؛ validator و Admin مقدار ناشناخته را قبل از import/save رد می‌کنند؛
- تمام WeatherPointهای فعال و عمومی `seo_indexable=true` هستند و صفحهٔ مستقل
  آن‌ها در sitemap می‌آید؛ نقطهٔ inactive یا synthetic مستثنی است. نقطهٔ متصل
  به route فعال بدون این flag فقط یک وضعیت ناسازگار است و validator آن را خطا می‌کند؛
- `aliases` برای شکل‌های رایج جست‌وجو و `source_urls` برای منابع هویت/موقعیت؛
- مختصات دقیق و `elevation_m` معتبر به‌همراه `elevation_source` یا evidence.

`page_name` نباید عبارت عمومی مثل «استراحتگاه مسیر» یا «شیب نهایی قله» باشد.
نام باید عارضهٔ واقعی را با زمینهٔ نقطه مشخص کند؛ برای مثال «جان‌پناه امیری
توچال» یا «روستای کلاک بالا». نقطهٔ شاخص در slug خود
باید بدون underscore باشد؛ همهٔ نقاط، از جمله نقاط شاخص، صفحهٔ canonical خود را
در `/points/{slug}` دارند.

## ۲. ترک و نقاط مسیر

در شروع کار agent باید این فولدر را در checkout محلی بسازد:

```bash
cd /path/to/hawatch
mkdir -p tracks/<point-slug>
```

هر ترک باید مسیر پیادهٔ شناخته‌شده و پیوسته‌ای با مبدأ و نقطه مشخص باشد. ترک
دوچرخه، خودرو، موتور، مسیر صخره‌نوردی/یخچالی فنی، ترک پراکنده یا مسیر نامرتبط
برای route قابل قبول نیست. اگر یک ترک نزولی است، فقط پس از تعیین جهت و تطبیق
با منبع مستقل می‌توان آن را برعکس تحلیل کرد؛ timestamp و ارتفاع خام GPX به‌تنهایی
حقیقت نیستند.

برای route اصلی ترجیحاً دو ترک مستقل تطبیق داده شود. هر route عمومی باید حداقل
زنجیرهٔ `مبدأ → یک عارضهٔ واقعی میانی → نقطه` داشته باشد. نقطهٔ ساختگی یا generic
برای پرکردن این زنجیره اضافه نشود؛ اگر landmark میانی اثبات نشده، route pending
بماند.

نام فایل دانلودی را قبل از تحلیل روشن کنید:
`<point>-<side>-<origin>-to-<target>-<year>.gpx`.
فایل‌ها و `manifest.json` در `.gitignore` هستند و هرگز commit، image یا server
نمی‌شوند. manifest فقط mapping فایل، route، منبع و نقش `primary`/`crosscheck`
را نگه می‌دارد.

## ۳. ساخت و اعتبارسنجی محلی

از ریشهٔ repository:

```bash
python3 scripts/analyze_route_tracks.py \
  --manifest tracks/<point-slug>/manifest.json \
  --catalog /tmp/<point-slug>_v1.json

python3 scripts/validate_open_meteo_catalog.py \
  --catalog /tmp/<point-slug>_v1.json
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
sort order تکراری را گزارش می‌کند. دو نقطهٔ فعال با فاصلهٔ کمتر از ۲۵ متر خطای
قطعی‌اند و باید merge شوند. فاصلهٔ ۲۵ تا ۱۰۰ متر هشدار curator می‌دهد، مگر این‌که
در همان catalog با `reviewed_nearby_point_pairs`، دو slug و علتِ روشن ثبت شده باشد؛
این استثنا فقط برای دو عارضهٔ واقعی و نام‌دار است و فاصلهٔ کمتر از ۲۵ متر را هرگز
مجاز نمی‌کند. با `--database`، دیتابیس فعلی نیز read-only بررسی می‌شود:

```bash
uv run python manage.py validate_catalog --all --database --strict
```

## ۴. واردکردن روی local

```bash
cd apps/api
uv run python manage.py migrate
uv run python manage.py seed_catalog --file catalog/<file>.json --strict
uv run python manage.py ingest_open_meteo --slugs <point-1>,<point-2>
uv run python manage.py catalog_preflight --point <point-slug> --require-forecast --strict
```

`seed_catalog` اتمیک و idempotent است. `--prune` فقط وقتی استفاده شود که حذف
رکوردهای fixture-managed عمداً بررسی شده باشد. پس از ingest، preflight باید برای
همهٔ pointهای نقطه `provider_checked` و forecast قابل استفاده نشان دهد. پیش‌بینی
از DB خوانده می‌شود؛ frontend مستقیماً Open-Meteo را صدا نمی‌زند.

## ۵. import به سرور از روی local

فایل را روی سرور کپی نکنید؛ از stdin بفرستید. حالت استاندارد شامل validation
محلی، check راه دور، import، ingest هدفمند و preflight است:

```bash
cd /path/to/hawatch
python3 scripts/publish_catalog.py \
  --catalog /tmp/<point-slug>_v1.json \
  --host hawatch \
  --point <point-slug> \
  --apply
```

`hawatch` همان alias SSH است. اگر route عمداً timing ندارد، انتشار فقط با تصمیم
صریح و `--allow-pending-timing` مجاز است؛ در این حالت forecast نقطه‌ها می‌آید
ولی arrival weather مسیر ساخته نمی‌شود. بدون `--apply` همین دستور فقط check می‌کند
و هیچ writeای ندارد.

پس از import، برای تغییر نقاطی محبوب فقط از command ادمین استفاده کنید؛ نقطه
جدید خودکار روی Home نمی‌رود:

```bash
uv run python manage.py set_popular_points --slugs a,b,c,d
```

حداکثر چهار نقطه محبوب است. همهٔ نقاطی فعال در search قابل پیدا شدن‌اند، اما
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
برای compatibility URL جدید استفاده شوند. SEO عمومی P0 همین حالا روی `page_name`
و slug canonical اعمال می‌شود: تمام نقاط فعال و عمومی و routeهای فعال وارد sitemap
می‌شوند و queryهای برنامه‌ریزی `noindex,follow` هستند.

برای همگام‌سازی release روی دیتابیس موجود، bootstrap ضمنی کافی نیست. ابتدا backup
بگیرید و command را در حالت امن اجرا کنید:

```bash
docker compose --env-file .env -f infra/compose/compose.yaml exec -T api \
  python manage.py sync_catalog --dry-run
```

گزارش، created/updated/unchanged، فهرست دقیق RoutePointها و رکوردهای
fixture-managed قابل حذف یا غیرفعال‌سازی و conflictهای operator-managed را نشان
می‌دهد. پس از بازبینی همان برنامه را اتمیک اعمال کنید:

```bash
docker compose --env-file .env -f infra/compose/compose.yaml exec -T api \
  python manage.py sync_catalog --apply
```

این command فقط ردیف‌های `fixture_managed=true` را برای stale cleanup هدف می‌گیرد؛
رکوردهای دستی حفظ می‌شوند و conflict مبهم باعث توقف sync می‌شود. اجرای دوبارهٔ
`--apply` روی دادهٔ همگام‌شده باید همهٔ رکوردهای موجود را unchanged گزارش کند.
