# Catalog و صحت‌سنجی آب‌وهوا

کاتالوگ زنده در دیتابیس نگهداری می‌شود و seeder عمومی فقط ابزار bootstrap/import است. برای افزودن یک مقصد بزرگ مثل دماوند، می‌توان manifest JSON را فقط از stdin به کانتینر فرستاد؛ لازم نیست فایل manifest یا GPX داخل image، repository یا commit قرار بگیرد. برای shared pointهای بین چند مسیر فقط یک slug تعریف کنید و slug را در آرایهٔ `points` مسیرها تکرار کنید.

حداقل قرارداد فایل:

- `catalog_version` یکتا و versioned
- `destination` با فیلدهای متادیتای مقصد و `latitude`/`longitude` ده‌دهی WGS84
- `weather_points` با `name`، مختصات و `elevation_m`؛ مقدار `null` یعنی ارتفاع هنوز منبع معتبر ندارد
- `routes` با مشخصات نمایش و آرایهٔ مرتب `points` که فقط به slugهای همین فایل اشاره می‌کند
- اختیاری: بلوک `timing` برای مسیرهای دارای زمان‌بندی تخمینی/curated

ورودی‌های لازم برای هر مقصد جدید: یک canonical destination WeatherPoint با مختصات WGS84، نام و منبع ارتفاع؛ برای هر route نیز slug، عنوان، `sort_order` مثبت (عدد کمتر = نمایش زودتر)، زنجیرهٔ مرتب نقاط، مسافت/صعود در صورت اطمینان، و timing تجمعی در صورت فعال‌کردن پیش‌بینی زمان رسیدن. `featured` فقط نشانهٔ پیشنهاد UI است و ترتیب routeها را تعیین نمی‌کند. GPX برای آب‌وهوا لازم نیست؛ برای فاصله، پروفایل صعود، نقاط میانی و زمان‌بندی دقیق، evidence توصیه‌شده است.

## زمان‌بندی مسیر (catalog-driven)

برای افزودن مقصد بعدی، timing باید از دادهٔ catalog بیاید نه کد اختصاصی:

- `timing_status`: `pending` | `estimated` | `curated`
- `one_way_minutes`: مدت صعود یک‌طرفه در pace متوسط؛ **هرگز** در `round_trip_minutes` ذخیره نشود
- `timing.method` / `timing.version` / `timing.confidence` / `timing.uncertainty_minutes` / `timing.source_urls`
- `timing.cumulative_minutes`: دیکشنری slug نقطه → دقیقه تجمعی متوسط از مبدأ (مبدأ = ۰)

اعتبارسنجی seed:

- همهٔ نقاط timed روی route وجود دارند و duplicate نیستند
- اولین cumulative صفر است و بعد از مبدأ strictly monotonic است
- `one_way_minutes` با cumulative نهایی برابر است
- `segment_minutes` (در صورت ذکر) با اختلاف cumulativeها یکی است
- اگر timing مبهم/ناقص است باید `pending` بماند؛ seed مقادیر را invent نمی‌کند
- seed idempotent است

### Tochal timing v3

Catalog version `hawatch-tochal-catalog-v4` / timing version `tochal-timing-v3`:

| route | status | method | notes |
| --- | --- | --- | --- |
| touchal-darband | estimated | `web-naismith-total+gpx-profile-v2` | GPX-profiled cumulatives; medium total 315 |
| touchal-welanjak | estimated | `web-naismith-total+gpx-profile-v2` | origin `velenjak_parking`; medium total 360 |
| touchal-ahar | estimated | `web-naismith-total+gpx-profile-v2` | medium total 380; qezqunchal ~212 m off-track |
| touchal-kalkchal | estimated | `gpx-geometry+web-naismith-v3` | full geometry GPX; synthetic 40s timestamps unusable for moving time; medium 390 / ± 45 |
| touchal-shahrestanak | estimated | `composite-gpx+dem+web-reports-v1` | composite village→Naseri + Naseri→summit; medium 370 / ± 50; not curated |

GPX under `tracks/tochal/` is internal evidence (`license_status: unverified`) and is **gitignored** (`/tracks/`). Do not parse at API/seed/ingest runtime and do not redistribute until licensing is confirmed. Offline review (local only): `python3 scripts/analyze_route_tracks.py`. Manifest `timestamp_quality` must be respected: when not `recorded`, analyzer nulls elapsed/moving time.

Device GPX `<ele>` is reference-only; PBF/DEM remain elevation truth. Route-level `distance_km`/`ascent_m` may be GPX-informed; verified per-segment distance/ascent/terrain remains a future curated upgrade.

## Database-first catalog (runtime)

The database is the runtime source of truth. JSON fixtures are bootstrap/import artifacts only.

- Normal import (`seed_catalog` / `seed_tochal_catalog`) is **non-destructive**. Operator-managed rows (`fixture_managed=false`) survive and are never silently overwritten on slug collision (skip + conflict report; optional `--force-adopt`).
- Without `--prune`, manual RoutePoints on fixture routes are preserved even when absent from JSON.
- Pruning requires explicit `--prune` and only removes `fixture_managed` rows absent from the JSON. Referenced fixture rows that would cause `ProtectedError` are skipped and reported. Never runs at API startup.
- Production startup (`DEMO_DATA_ENABLED=false`) runs `bootstrap_live_catalog_if_empty` when `HAWATCH_BOOTSTRAP_LIVE_CATALOG_IF_EMPTY=true` (default): seeds only if no live WeatherPoints exist.
- Scheduled ingest selects points that are `is_active` + `ingest_enabled` and exposed by an active Destination **profile** or an active Route whose Destination is active. Legacy `WeatherPoint.destination` ownership alone is insufficient. Snapshot revision is `dbrev-…`.
- Inactive Destination / Route / WeatherPoint rows are omitted from public APIs, siblings, related routes, search, and health catalog counts.
- Admin and catalog import share `normalize_and_publish_route` for ordering, denormalized fields, origin/target, segments, axis, timing demotion, and search rebuild.
- `tracks/` is local-only research evidence (gitignored); never commit GPX/manifest.

### فلوی استاندارد افزودن مقصد جدید

این فلوی عمومی برای دماوند و مقصدهای بعدی است:

1. در لوکال یک manifest بسازید؛ مختصات و ارتفاع catalog را از منابع قابل‌اعتماد وارد کنید. GPX فقط برای تحلیل آفلاین مسیر و ساخت distance/ascent/timing استفاده شود و هرگز در API، seed یا ingest parse نشود.
2. قبل از هر write، اعتبارسنجی provider را اجرا کنید:

```bash
python3 scripts/validate_open_meteo_catalog.py \
  --catalog /tmp/damavand.json
```

این بررسی WGS84، مختصات تکراری، route references، DEM/provider elevation، وجود forecast ساعتی و فاصلهٔ مرکز grid تا مختصات را چک می‌کند؛ فاصلهٔ بیشتر از ۵ کیلومتر fail است. اگر ارتفاع هنوز قطعی نیست، فقط موقتاً از `--allow-unresolved-elevation` استفاده کنید و نقطه را provisional نگه دارید.

3. manifest را بدون قرار دادن فایل در سرور یا image بررسی شکلی کنید:

```bash
cd /root/hawatch
docker compose --env-file .env -f infra/compose/compose.yaml exec -T api \
  python manage.py seed_catalog --stdin --check-only < /tmp/damavand.json
```

4. پس از موفقیت preflight، آن را به‌صورت اتمیک و strict وارد دیتابیس کنید. این کار کد deploy نمی‌خواهد؛ فقط JSON از stdin منتقل می‌شود:

```bash
docker compose --env-file .env -f infra/compose/compose.yaml exec -T api \
  python manage.py seed_catalog --stdin --strict < /tmp/damavand.json
```

Import بدون `--prune` است؛ در slug conflict با ردیف operator-managed کل عملیات در حالت `--strict` rollback می‌شود. `--prune` فقط برای حذف عمدی fixture-managedهاست.

5. ingest هدفمند را اجرا و فاصلهٔ provider را از دادهٔ واقعی ذخیره‌شده کنترل کنید:

```bash
docker compose --env-file .env -f infra/compose/compose.yaml exec -T api \
  python manage.py ingest_open_meteo --slugs damavand_summit,damavand_shelter

docker compose --env-file .env -f infra/compose/compose.yaml exec -T api \
  python manage.py catalog_preflight --destination damavand --require-forecast --strict
```

`catalog_preflight` فقط read-only است و canonical link، فعال‌بودن مقصد/route/point، ترتیب route، زنجیرهٔ نقاط، endpointها، timing و آخرین resolution/forecast Open-Meteo را گزارش می‌کند. اگر timing ناقص باشد route همچنان قابل نمایش است اما `pending` می‌ماند و پیش‌بینی arrival برای آن ساخته نمی‌شود.

### افزودن WeatherPoint و Route بدون deploy

1. Django admin → WeatherPoint: مختصات، DEM elevation، `is_active`/`ingest_enabled=true`؛ `fixture_managed` را دستی true نکنید.
2. اختیاری: Destination profile روی همان نقطه.
3. Route + مرتب‌سازی RoutePointها با cumulative کامل؛ برای متن کاربر فقط `public_note` کوتاه وارد کنید. evidence/منبع/یادداشت GPX را در `internal_note` نگه دارید؛ سرویس publish نرمال‌سازی می‌کند؛ timing ناقص → `pending`.
4. پس از commit، search index خودکار rebuild می‌شود (بدون restart).
5. ingest بعدی همهٔ نقاط فعال واجد شرایط را می‌گیرد؛ برای فوری: `ingest_open_meteo --slugs your_slug`.

ضریب زمان نسبی (نه km/h): آرام `1.25`، متوسط `1.00`، سریع `0.80`؛ مدت‌ها به نزدیک‌ترین ۵ دقیقه گرد می‌شوند.

نکات ساختاری:

- مبدأ کلکچال/پیازچال: `jamshidieh_park` در پارکینگ شرقی GPX (`35.824629`, `51.465985`، DEM `1826` m، provisional). `piyazchal_pass` ≈135 m و `lezoon_east` ≈217 m از track؛ مختصاتشان auto-update نشده‌اند.
- مبدأ ولنجک: `velenjak_parking` (provisional؛ ارتفاع null تا DEM)؛ `velenjak` عمومی حذف نمی‌شود
- `tochal_hotel` روی زنجیرهٔ اجباری ولنجک نیست؛ روی شهرستانک هست
- گردنهٔ شهرستانک (`shahrestanak_pass`) از بازارک (`bazarek_pass`) متمایز است؛ `naseri_junction` / `bazarek_pass` / `shahneshin_pass` فقط برای variantهای آینده در catalog می‌مانند

منبع‌های ثبت‌شده در catalog/Wikiloc evidence:

- https://mojekooh.com/قله-توچال/
- https://www.wikiloc.com/mountaineering-trails/qlh-twchl-z-msyr-drbnd-110322184
- https://www.wikiloc.com/hiking-trails/qlh-twchl-z-wlnjkh-174731165
- https://www.wikiloc.com/hiking-trails/qlh-twchl-z-ahr-w-shkhrb-40908439
- https://www.wikiloc.com/hiking-trails/qlh-twchl-z-shhrstnkh-186308660
- https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0295848

در catalog توچال، ارتفاع‌های دارای `ele` در PBF منبع اصلی هستند. ارتفاع‌های هشت point قبلیِ بدون `ele` اکنون با `status: provisional` و منبع مقایسه‌ای ثبت شده‌اند: ولنجک ۱۷۵۵، هتل توچال ۳۵۴۵، کمپ کلکچال ۲۶۰۰، آهار ۲۱۴۰، شکرآب ۲۴۰۰، شهرستانک ۲۲۰۰، کاخ ناصری ۲۳۱۶ و سه‌راه ناصری ۳۴۵۷ متر. مقدار کاخ ناصری و سه‌راه ناصری بر اساس DEM مختصات فیزیکی PBF است و برای elevation survey-grade ادعا نمی‌شود. `jamshidieh_park` نیز provisional است (دسترسی بالای مسیر؛ چند ورودی).

## بررسی محلی و import catalog

از ریشهٔ repository:

```bash
python3 scripts/validate_open_meteo_catalog.py \
  --catalog apps/api/fixtures/catalog/my_destination_v1.json
```

validator هیچ فایلی، database یا snapshotی نمی‌نویسد. مختصات را از نظر WGS84، duplicate و route reference بررسی می‌کند؛ elevation API سرویس Open-Meteo را برای مقایسهٔ DEM می‌خواند؛ سپس forecast را با قرارداد واقعی provider صدا می‌زند و cardinality، elevation metadata، دادهٔ ساعتی و فاصلهٔ مرکز grid تا مختصات درخواست‌شده را چک می‌کند. فاصلهٔ بیش از ۵ کیلومتر failure است. elevationهای catalog با DEM مقایسه می‌شوند ولی DEM به‌صورت خودکار جایگزین منبع catalog نمی‌شود.

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
  python manage.py ingest_open_meteo
```

Import پیش‌فرض غیرتخریبی است (`--prune` فقط صریح). `seed_catalog --stdin` برای افزودن/به‌روزرسانی داده بدون deploy فایل manifest است و `--check-only` هیچ writeای ندارد. Ingest از WeatherPointهای فعال DB انتخاب می‌کند (نه filename JSON)؛ revision اسنپ‌شات `dbrev-…` است. برای ingest فوری چند slug: `--slugs a,b`. از API handlerها جداست؛ frontend نیز مستقیماً به Open-Meteo وصل نمی‌شود.

## ارتفاع در درخواست weather

اگر `elevation_m` موجود و status آن قطعی باشد، provider همان ارتفاع catalog را همراه `cell_selection=land` به Open-Meteo می‌فرستد تا برای statistical downscaling استفاده شود. برای ارتفاع‌های `provisional`، همان ارتفاع صریح ارسال می‌شود اما `cell_selection=nearest` انتخاب می‌شود تا یک اختلاف ارتفاع غیرقطعی، weather cell را به نقطه‌ای دور منتقل نکند. اگر null باشد، ارتفاعی جعل یا در catalog ذخیره نمی‌شود؛ درخواست با `cell_selection=nearest` انجام می‌شود و elevation برگشتی فقط در `ForecastPointResolution` به‌عنوان metadata provider ثبت می‌شود. پس از افزودن elevation معتبر به فایل، اجرای بعدی ingest خودکار آن را در درخواست استفاده می‌کند.

مختصات برگشتی provider، فاصلهٔ آن از مختصات catalog و elevation برگشتی ذخیره می‌شوند؛ batch ناسازگار یا دورتر از ۵ کیلومتر اصلاً persist نمی‌شود.
