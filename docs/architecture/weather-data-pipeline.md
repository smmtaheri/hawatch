# pipeline دادهٔ هوا

## وضعیت فعلی

API از forecastهای دمو یا live در PostgreSQL می‌خواند. frontend منبع داده را نمی‌بیند؛ فقط contract داخلی را مصرف می‌کند.

- `DEMO_DATA_ENABLED=true`: seed دمو + refresh ساعتی demo
- `DEMO_DATA_ENABLED=false`: catalog با `seed_tochal_catalog`؛ forecast فقط از snapshotهای live؛ API هرگز Open-Meteo را صدا نمی‌زند

## مسیر داده

```text
provider (management command)
  → raw weather ingestion + advisory lock
  → ForecastSnapshot (raw JSON, checksum)
  → normalization
  → PostgreSQL ForecastRecord (live)
  → API
  → retention cleanup (≤ 7 days raw snapshots)
```

Interfaceهای آماده‌شده / استفاده‌شده:

- `WeatherProvider` → `OpenMeteoProvider`
- `ForecastNormalizer` → `normalize_point_hourly`
- `RetentionPolicy` → `cleanup_old_snapshots`
- `JobLock` → Postgres advisory lock در `ingest_lock`

## الزامات عملیاتی

- نگهداری raw حداکثر یک هفته (`cleanup_old_snapshots`)؛ آخرین snapshot قابل‌استفاده قبل از جایگزین موفق حذف نمی‌شود
- catalog و تعریف route با retention هوا حذف نمی‌شوند
- retry و backoff محدود برای 429 و خطاهای موقت transport
- جلوگیری از اجرای هم‌زمان ingestion با advisory lock
- آخرین دادهٔ سالم برای نقاط موفق به‌صورت atomic جایگزین می‌شود؛ نقاط ناموفق batch قبلی را نگه می‌دارند
- پاسخ provider فقط وقتی به catalog point متصل می‌شود که `latitude` و `longitude` معتبر داشته باشد و مرکز grid حداکثر ۵ کیلومتر با مختصات درخواستی فاصله داشته باشد؛ پاسخ دور یا ناقص کل batch را رد می‌کند
- برای pointهایی که ارتفاع catalog دارند، `cell_selection=land` همراه با elevation صریح استفاده می‌شود؛ برای pointهای بدون ارتفاع catalog، `cell_selection=nearest` استفاده می‌شود تا انتخاب land cell دور، weather نقطه را جابه‌جا نکند
- تنظیم optional proxy (`WEATHER_PROXY_URL`) هنوز استفاده‌نشده است

## قرارداد مختصات provider

Open-Meteo مختصات دقیق point را بازنمی‌گرداند؛ `latitude` و `longitude` پاسخ، مرکز سلول grid انتخاب‌شده هستند. بنابراین برابر نبودن آن‌ها با catalog به‌تنهایی خطا نیست. با این حال، ingest پیش از ذخیره‌سازی فاصلهٔ Haversine را کنترل می‌کند و هر پاسخ خارج از آستانهٔ ۵ کیلومتر، یا فاقد مختصات معتبر، قابل استفاده نیست و به‌عنوان batch ناموفق نگه داشته می‌شود. مختصات و ارتفاع برگشتی در `ForecastPointResolution` فقط metadata provider هستند و هرگز catalog truth را overwrite نمی‌کنند.
