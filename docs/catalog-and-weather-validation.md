# Catalog و صحت‌سنجی آب‌وهوا

هر مقصد جدید باید به‌صورت یک فایل JSON مستقل در `apps/api/fixtures/catalog/` اضافه شود. seeder عمومی routeها و `WeatherPoint`های مشترک را از همان فایل می‌سازد؛ برای shared pointهای بین چند مسیر فقط یک slug تعریف کنید و slug را در آرایهٔ `points` مسیرها تکرار کنید.

حداقل قرارداد فایل:

- `catalog_version` یکتا و versioned
- `destination` با فیلدهای متادیتای مقصد و `latitude`/`longitude` ده‌دهی WGS84
- `weather_points` با `name`، مختصات و `elevation_m`؛ مقدار `null` یعنی ارتفاع هنوز منبع معتبر ندارد
- `routes` با مشخصات نمایش و آرایهٔ مرتب `points` که فقط به slugهای همین فایل اشاره می‌کند

## ترتیب بررسی یک مقصد جدید

از ریشهٔ repository:

```bash
python3 scripts/validate_open_meteo_catalog.py \
  --catalog apps/api/fixtures/catalog/my_destination_v1.json
```

validator هیچ فایلی، database یا snapshotی نمی‌نویسد. مختصات را از نظر WGS84، duplicate و route reference بررسی می‌کند؛ elevation API سرویس Open-Meteo را برای مقایسهٔ DEM می‌خواند؛ سپس forecast را با قرارداد واقعی provider صدا می‌زند و cardinality، elevation metadata، دادهٔ ساعتی و فاصلهٔ مرکز grid تا مختصات درخواست‌شده را چک می‌کند. فاصلهٔ بیش از ۵ کیلومتر failure است. elevationهای catalog با DEM مقایسه می‌شوند ولی DEM به‌صورت خودکار جایگزین منبع catalog نمی‌شود.

در catalog توچال، ارتفاع‌های دارای `ele` در PBF منبع اصلی هستند. ارتفاع‌های هشت point قبلیِ بدون `ele` اکنون با `status: provisional` و منبع مقایسه‌ای ثبت شده‌اند: ولنجک ۱۷۵۵، هتل توچال ۳۵۴۵، کمپ کلکچال ۲۶۰۰، آهار ۲۱۴۰، شکرآب ۲۴۰۰، شهرستانک ۲۲۰۰، کاخ ناصری ۲۳۱۶ و سه‌راه ناصری ۳۴۵۷ متر. مقدار کاخ ناصری و سه‌راه ناصری بر اساس DEM مختصات فیزیکی PBF است و برای elevation survey-grade ادعا نمی‌شود.

برای smoke test مختصات وقتی بعضی pointها هنوز elevation معتبر ندارند:

```bash
python3 scripts/validate_open_meteo_catalog.py \
  --catalog apps/api/fixtures/catalog/my_destination_v1.json \
  --allow-unresolved-elevation
```

این گزینه فقط الزام ارتفاع را برای همان اجرای بررسی کنار می‌گذارد و به معنی تأیید ارتفاع نیست.

## Seed و ingest

```bash
docker compose -f infra/compose/compose.yaml exec api \
  python manage.py seed_catalog --file catalog/my_destination_v1.json

docker compose -f infra/compose/compose.yaml exec api \
  python manage.py ingest_open_meteo \
  --catalog catalog/my_destination_v1.json --seed-catalog
```

هر دو عملیات idempotent هستند. ingestion فقط pointهای همان `catalog_version` را می‌گیرد و از API handlerها جداست؛ frontend نیز مستقیماً به Open-Meteo وصل نمی‌شود.

## ارتفاع در درخواست weather

اگر `elevation_m` موجود و status آن قطعی باشد، provider همان ارتفاع catalog را همراه `cell_selection=land` به Open-Meteo می‌فرستد تا برای statistical downscaling استفاده شود. برای ارتفاع‌های `provisional`، همان ارتفاع صریح ارسال می‌شود اما `cell_selection=nearest` انتخاب می‌شود تا یک اختلاف ارتفاع غیرقطعی، weather cell را به نقطه‌ای دور منتقل نکند. اگر null باشد، ارتفاعی جعل یا در catalog ذخیره نمی‌شود؛ درخواست با `cell_selection=nearest` انجام می‌شود و elevation برگشتی فقط در `ForecastPointResolution` به‌عنوان metadata provider ثبت می‌شود. پس از افزودن elevation معتبر به فایل، اجرای بعدی ingest خودکار آن را در درخواست استفاده می‌کند.

مختصات برگشتی provider، فاصلهٔ آن از مختصات catalog و elevation برگشتی ذخیره می‌شوند؛ batch ناسازگار یا دورتر از ۵ کیلومتر اصلاً persist نمی‌شود.
