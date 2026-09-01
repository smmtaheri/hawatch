# راهنمای استاندارد افزودن مقصد، نقطه و مسیر

این سند مرجع اصلی افزودن مقصدهای جدید به Hawatch است. برای شروع کار نفر بعدی
همین سند را بخواند؛ قرارداد جزئی‌تر فیلدها در
[`catalog-and-weather-validation.md`](catalog-and-weather-validation.md) و رفتار
forecast در [`api/forecast-contract.md`](api/forecast-contract.md) است.

## اصل معماری

دیتابیس منبع حقیقت runtime است. مقصد، WeatherPoint، Route و RoutePoint بعد از
import در دیتابیس ذخیره می‌شوند و برای اضافه‌کردن آن‌ها deploy یا migration لازم
نیست.

فایل JSON فقط یک ورودی versioned برای import است. می‌تواند در `/tmp` یا یک
مخزن خصوصی نگه‌داری شود و با `--stdin` از کامپیوتر اپراتور به کانتینر API
فرستاده شود؛ فایل JSON و GPX لازم نیست روی سرور کپی شوند.

کدهای عمومی این workflow در repository هستند:

- `scripts/validate_open_meteo_catalog.py`: اعتبارسنجی read-only مختصات، DEM و provider؛
- `scripts/analyze_route_tracks.py`: تحلیل read-only GPX روی کامپیوتر محلی؛
- `scripts/publish_catalog.py`: اجرای استاندارد کل workflow محلی/SSH؛
- `seed_catalog --stdin`: check-only یا import اتمیک در دیتابیس؛
- `ingest_open_meteo`: ذخیرهٔ forecast نقاط فعال؛
- `catalog_preflight`: بررسی read-only دادهٔ واقعی داخل دیتابیس.

## داده‌های لازم

### مقصد

برای هر مقصد یک رکورد با این اطلاعات لازم است:

- `slug` یکتا و پایدار، مثلاً `damavand`؛
- نام، نام کوتاه، منطقه و `category_key`؛ برای دماوند `volcano`؛
- مختصات canonical به‌صورت WGS84 ده‌دهی؛
- ارتفاع معتبر و منبع آن؛
- `climate`، تصویر و alt text؛
- `popular_order` و `is_popular` برای ترتیب نمایش.

`category_key` فقط متن دسته‌بندی نیست؛ کلید معنایی آیکون مقصد هم هست و از
دیتابیس به فرانت می‌رسد. برای مثال، اسکلیم باید `waterfall` داشته باشد و دماوند
`volcano`. بعد از اضافه‌شدن یک کلید به مجموعهٔ runtime، ثبت مقصدهای بعدی با یکی
از کلیدهای موجود فقط با import کاتالوگ یا Admin انجام می‌شود و deploy جداگانه
لازم ندارد. کلید ناشناخته نباید استفاده شود؛ UI برای جلوگیری از نمایش گمراه‌کننده
به‌جای کوه، نشان خنثی نشان می‌دهد.

همان نقطهٔ مقصد باید در `weather_points` با `kind: "destination"` هم تعریف شود
تا صفحهٔ مقصد و مسیرها به یک WeatherPoint canonical وصل باشند.

### WeatherPoint

برای هر نقطه:

- slug یکتا، نام و مختصات دقیق؛
- `elevation_m` از منبع قابل‌اعتماد، ترجیحاً DEM/PBF تأییدشده؛
- `elevation_source` یا `evidence_note` برای audit؛
- اگر ارتفاع هنوز قطعی نیست، مقدار `null` و وضعیت provisional استفاده شود؛
- GPX `<ele>` به‌تنهایی حقیقت ارتفاع نیست.

GPX برای گرفتن آب‌وهوا لازم نیست. مختصات و ارتفاع برای ساخت WeatherPoint
کافی است؛ GPX فقط برای بررسی هندسه، فاصله، صعود و نقاط میانی مسیر استفاده می‌شود.

### Route

برای هر مسیر:

- `slug`، عنوان، subtitle، برچسب جبهه و origin/destination label؛
- آرایهٔ `points` به‌ترتیب حرکت از مبدأ تا مقصد؛
- `sort_order` مثبت؛ عدد کمتر زودتر نمایش داده می‌شود؛
- `featured: true` فقط برای مسیرهای پیشنهادی UI است و ترتیب را تعیین نمی‌کند؛
- `distance_km` و `ascent_m` فقط وقتی ثبت شوند که evidence کافی دارند.

یک WeatherPoint می‌تواند بین چند Route مشترک باشد. برای آن یک slug بسازید و
همان slug را در چند مسیر استفاده کنید؛ برای هر مسیر RoutePoint جداگانه ساخته
می‌شود و timing آن مسیر را دارد.

### زمان‌بندی arrival-aware

اگر می‌خواهیم زیر هر نقطهٔ مسیر زمان رسیدن و آب‌وهوای همان زمان نمایش داده شود،
route باید timing کامل داشته باشد:

```json
{
  "timing_status": "estimated",
  "one_way_minutes": 650,
  "timing": {
    "method": "gpx-geometry+dem+web-reports-v1",
    "version": "damavand-timing-v1",
    "confidence": "medium",
    "uncertainty_minutes": 90,
    "source_urls": ["https://example.org/source"],
    "cumulative_minutes": {
      "trailhead": 0,
      "shelter": 270,
      "summit": 650
    }
  }
}
```

قواعد اجباری:

- `timing_status` باید `estimated` یا `curated` باشد؛
- `one_way_minutes` زمان صعود یک‌طرفه در سرعت متوسط است؛
- cumulative برای تمام نقاط مسیر لازم است؛
- مقدار اول صفر و همهٔ مقادیر بعدی strictly increasing باشند؛
- مقدار نهایی cumulative با `one_way_minutes` برابر باشد؛
- method، version، confidence، uncertainty و حداقل یک source URL ثبت شوند؛
- timestamp ثبت‌شدهٔ یک GPX چندروزه، زمان حرکت مسیر نیست؛ استراحت/شب‌مانی نباید
  وارد ETA شود؛
- اگر timing قابل‌دفاع نیست، route باید `pending` بماند. در این حالت forecast
  عمومی نقطه موجود است، اما arrival forecast عمداً ساخته نمی‌شود.

سرعت‌های آرام و سریع در runtime از زمان متوسط مشتق می‌شوند (`1.25` و `0.80`).
لازم نیست برای هر سرعت سه مجموعه timing جداگانه ذخیره شود.

## GPX و manifest

اگر GPX دارید، آن را فقط در checkout محلی زیر `tracks/<destination>/` بگذارید.
کل `tracks/` در Git ignore است و نباید commit، image یا سرور شود. `manifest.json`
فقط mapping فایل GPX به route، کیفیت timestamp و وضعیت license است؛ API در زمان
seed یا ingest آن را نمی‌خواند.

تحلیل محلی:

```bash
cd /path/to/hawatch

python3 scripts/analyze_route_tracks.py \
  --manifest tracks/damavand/manifest.json \
  --catalog /tmp/damavand_v1.json \
  > /tmp/damavand_tracks_report.json
```

خروجی distance، صعود نرم‌شده و نزدیک‌ترین نقطهٔ track را گزارش می‌کند؛ خودش
catalog را تغییر نمی‌دهد. timing نهایی تصمیم editorial است و باید با گزارش مسیر
و منابع وب/میدانی ثبت شود، نه اینکه یک timestamp خام بدون بررسی وارد ETA شود.

## فلو پیشنهادی کامل

### ۱. ساخت و ویرایش catalog روی local

یک فایل مثل `/tmp/damavand_v1.json` بسازید. این فایل باید shape نمونهٔ
`apps/api/fixtures/catalog/tochal_v1.json` را داشته باشد و route timing کامل
داشته باشد اگر قرار است arrival weather نمایش داده شود.

برای شروع می‌توان از
[`templates/catalog-template.json`](templates/catalog-template.json) یک کپی
گرفت و همهٔ مقادیر نمونه را با دادهٔ مقصد واقعی جایگزین کرد. فایل template عمداً
یک route `pending` دارد تا مسیر ناقص به‌اشتباه به‌عنوان arrival-ready منتشر نشود.

برای مقصد جدید لازم نیست فایل را در repository یا سرور قرار دهید. اگر بخواهید
نسخهٔ داده قابل بازبینی داشته باشید، آن را در یک محل خصوصی/محلی نگه دارید؛
runtime بعد از import دیتابیس است.

### ۲. اعتبارسنجی محلی provider و ارتفاع

این فرمان هیچ database write ندارد و از Open-Meteo برای elevation و forecast
ساعتی استفاده می‌کند:

```bash
cd /path/to/hawatch
python3 scripts/validate_open_meteo_catalog.py \
  --catalog /tmp/damavand_v1.json
```

این بررسی باید نشان دهد:

- مختصات در محدودهٔ WGS84 و تکراری نیستند؛
- همهٔ routeها فقط به pointهای موجود اشاره می‌کنند؛
- برای هر point دادهٔ ساعتی provider وجود دارد؛
- فاصلهٔ مرکز grid provider حداکثر ۵ کیلومتر است؛
- اختلاف elevation catalog و DEM در محدودهٔ قابل‌بررسی است.

این تست ثابت نمی‌کند پیش‌بینی weather از نظر MAE در دنیای واقعی «دقیق» است؛
فقط می‌سنجد نقطه به grid درست وصل است و forecast قابل دریافت است. سنجش دقت
تجربی نیازمند observation واقعی/ایستگاه مرجع و workflow جداگانه است.

### ۳. یک فرمان برای check و publish

حالت بدون `--apply` فقط بررسی می‌کند:

```bash
cd /path/to/hawatch
python3 scripts/publish_catalog.py \
  --catalog /tmp/damavand_v1.json \
  --host root@SERVER_IP
```

این wrapper به‌ترتیب این کارها را انجام می‌دهد:

1. local Open-Meteo/DEM validation؛
2. ارسال JSON از stdin به سرور و `seed_catalog --check-only`؛
3. توقف بدون هیچ database write.

پس از موفقیت check، publish واقعی:

```bash
python3 scripts/publish_catalog.py \
  --catalog /tmp/damavand_v1.json \
  --host root@SERVER_IP \
  --apply
```

در حالت apply، wrapper به‌ترتیب زیر عمل می‌کند:

1. catalog را با `seed_catalog --stdin --strict` به‌صورت اتمیک import می‌کند؛
2. فقط slugهای همین catalog را با `ingest_open_meteo` می‌گیرد؛
3. `catalog_preflight --destination ... --require-forecast --strict` را اجرا می‌کند؛
4. اگر همه‌چیز pass شود، مقصد آمادهٔ refresh صفحه است.

اگر عمداً route بدون timing اضافه می‌کنید، باید آگاهانه استفاده کنید:

```bash
python3 scripts/publish_catalog.py \
  --catalog /tmp/draft.json \
  --host root@SERVER_IP \
  --apply \
  --allow-pending-timing
```

این گزینه مشکل را پنهان نمی‌کند؛ route در دیتابیس `pending` می‌ماند و arrival
weather آن در UI نمایش داده نمی‌شود. برای launch عمومی بهتر است بدون این گزینه
کار کنید تا missing timing جلوی publish گرفته شود.

### ۴. معادل دستی روی سرور

اگر wrapper در دسترس نبود، از root checkout سرور:

```bash
ssh root@SERVER_IP \
  'cd /root/hawatch && docker compose --env-file .env -f infra/compose/compose.yaml exec -T api python manage.py seed_catalog --stdin --check-only' \
  < /tmp/damavand_v1.json

ssh root@SERVER_IP \
  'cd /root/hawatch && docker compose --env-file .env -f infra/compose/compose.yaml exec -T api python manage.py seed_catalog --stdin --strict' \
  < /tmp/damavand_v1.json

ssh root@SERVER_IP \
  'cd /root/hawatch && docker compose --env-file .env -f infra/compose/compose.yaml exec -T api python manage.py ingest_open_meteo'

ssh root@SERVER_IP \
  'cd /root/hawatch && docker compose --env-file .env -f infra/compose/compose.yaml exec -T api python manage.py catalog_preflight --destination damavand --require-forecast --strict'
```

در فرمان‌های بالا `/tmp/damavand_v1.json` روی local خوانده می‌شود و از stdin
عبور می‌کند؛ لازم نیست `/tmp` روی سرور وجود داشته باشد.

برای بررسی مقصد بدون تغییر:

```bash
ssh root@SERVER_IP \
  'cd /root/hawatch && docker compose --env-file .env -f infra/compose/compose.yaml exec -T api python manage.py catalog_preflight --destination damavand --require-forecast'
```

در `catalog_preflight`، حالت `--strict` warningهای timing را هم failure می‌کند.
برای مقصدی که هنوز timing ندارد، `pass=False` با warning طبیعی است؛ این نشانهٔ
خرابی ingest نیست.

### وضعیت فعلی دماوند

برای دماوند، چهار route اصلی با timing تخمینی اولیه وارد دیتابیس شده‌اند:

| route | زمان متوسط یک‌طرفه | عدم‌قطعیت | وضعیت |
| --- | ---: | ---: | --- |
| جنوبی | ۶۱۵ دقیقه | ±۹۰ دقیقه | estimated |
| غربی | ۶۹۰ دقیقه | ±۹۰ دقیقه | estimated |
| شمال‌شرقی | ۶۵۰ دقیقه | ±۹۰ دقیقه | estimated |
| شمالی | ۷۵۰ دقیقه | ±۹۰ دقیقه | estimated |

این اعداد برای اتصال forecast به زمان رسیدن استفاده می‌شوند و field-curated
نیستند؛ بعداً با چند track مستقل و گزارش میدانی می‌توان آن‌ها را به‌روزرسانی کرد.
GPX شمالی timestamp معتبر برای محاسبهٔ moving time نداشت و timestamp خام آن در
این timing استفاده نشده است.

### ۵. مسیر Admin بدون JSON

برای ورود دستی:

1. Admin → WeatherPoint: slug، نام، مختصات، elevation، `is_active=true` و
   `ingest_enabled=true`؛ `fixture_managed` را دستی true نکنید.
2. در صورت نیاز Destination profile را به WeatherPoint canonical وصل کنید.
3. Admin → Route: مقصد فعال، عنوان، `sort_order` و active.
4. RoutePointها را به‌ترتیب بسازید و برای همه `cumulative_minutes` وارد کنید.
5. بعد از save، publish service ترتیب، origin/target، segment، axis و timing را
   normalize می‌کند؛ timing ناقص عمداً pending می‌شود.
6. ingest هدفمند را اجرا و preflight را چک کنید.

برای اضافه‌کردن سریع مقصدهای متعدد، JSON + wrapper پیشنهاد می‌شود؛ Admin برای
اصلاح یک رکورد یا override اپراتوری مناسب‌تر است.

## حل خطاهای رایج

### `timed_routes=0` یا `زمان‌بندی در دسترس نیست`

نقاط forecast دارند اما route timing ندارد یا cumulative یکی از نقاط خالی است.
دوباره ingest کردن این مشکل را حل نمی‌کند. timing را به JSON اضافه و دوباره با
`seed_catalog --stdin --strict` import کنید.

### `provider_checked=17` ولی route هنوز خالی است

این حالت طبیعی است: provider برای WeatherPointها موفق بوده، اما API برای اتصال
forecast به نقطهٔ مسیر به arrival time نیاز دارد. timing و `cumulative_minutes`
را بررسی کنید.

### `Catalog input is valid; No database changes made`

این خروجی `--check-only` است و موفقیت آن به معنی import نیست. مرحلهٔ apply را
بعد از بررسی اجرا کنید.

### slug conflict

import معمولی non-destructive است. ردیف operator-managed overwrite نمی‌شود؛ در
حالت strict کل import rollback می‌شود. slug موجود را reuse کنید یا conflict را
در Admin بررسی کنید؛ `--force-adopt` فقط با تصمیم صریح اپراتور استفاده شود.

### دادهٔ هوا قدیمی است

ingest scheduler طبق timezone تهران در ساعت‌های ۰۰:۰۰، ۰۶:۰۰، ۱۲:۰۰ و ۱۸:۰۰
اجرا می‌شود. برای refresh فوری:

```bash
docker compose --env-file .env -f infra/compose/compose.yaml run --rm ingest
```

سپس preflight را اجرا کنید. frontend مستقیماً به Open-Meteo وصل نمی‌شود؛ فقط
forecast ذخیره‌شدهٔ دیتابیس را می‌خواند.

## چک‌لیست قبل از اعلام آماده‌بودن

- [ ] مقصد و canonical destination WeatherPoint مختصات و elevation منبع‌دار دارند.
- [ ] هر route `sort_order` درست دارد و points از مبدأ تا مقصد مرتب‌اند.
- [ ] برای هر route عمومی distance/ascent قابل‌دفاع است.
- [ ] routeهای دارای arrival weather timing کامل و provenance دارند.
- [ ] `validate_open_meteo_catalog.py` بدون error pass شده است.
- [ ] remote `seed_catalog --stdin --check-only` pass شده است.
- [ ] import strict انجام شده است.
- [ ] ingest موفق بوده است.
- [ ] preflight با `--require-forecast --strict` pass شده است.
- [ ] صفحهٔ مقصد و هر route با date/period/start_time واقعی refresh و بررسی شده‌اند.
- [ ] GPX و manifest داخل `tracks/` باقی مانده و commit نشده‌اند.
