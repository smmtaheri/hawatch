# pipeline دادهٔ هوا

## وضعیت فعلی

API از forecastهای دمو یا live در PostgreSQL می‌خواند. frontend منبع داده را نمی‌بیند؛ فقط contract داخلی را مصرف می‌کند.

- `DEMO_DATA_ENABLED=true`: seed دمو برای توسعه
- `DEMO_DATA_ENABLED=false`: catalog با `seed_tochal_catalog`؛ forecast فقط از snapshotهای live؛ API هرگز Open-Meteo را صدا نمی‌زند

## مسیر داده

```text
provider (one-shot management command، هر ۶ ساعت با scheduler بیرونی)
  → raw weather ingestion + advisory lock
  → ForecastSnapshot (raw JSON, checksum)
  → normalization
  → PostgreSQL ForecastRecord (live، bulk upsert بر اساس point/time/seed)
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
- آخرین دادهٔ سالم برای نقاط موفق با bulk upsert داخل transaction جایگزین می‌شود؛ نقاط ناموفق batch قبلی را نگه می‌دارند
- هیچ delete قبل از موفقیت persistence انجام نمی‌شود؛ شکست provider یا خطای DB، آخرین دادهٔ قابل‌استفاده را حفظ می‌کند
- برای هر `WeatherPoint + forecast_at + seed_version` فقط یک رکورد live نگه داشته می‌شود
- default پنجرهٔ provider برای قرارداد فعلی UI برابر `forecast_days=7` و `past_days=1` است؛ حالت compact پنج‌روزه (`5/0`) فقط با تصمیم مستقل برای تغییر UI فعال می‌شود
- پاسخ provider فقط وقتی به catalog point متصل می‌شود که `latitude` و `longitude` معتبر داشته باشد و مرکز grid حداکثر ۵ کیلومتر با مختصات درخواستی فاصله داشته باشد؛ پاسخ دور یا ناقص کل batch را رد می‌کند
- برای pointهایی که ارتفاع catalog دارند، `cell_selection=land` همراه با elevation صریح استفاده می‌شود؛ برای pointهای بدون ارتفاع catalog، `cell_selection=nearest` استفاده می‌شود تا انتخاب land cell دور، weather نقطه را جابه‌جا نکند
- تنظیم optional proxy (`WEATHER_PROXY_URL`) هنوز استفاده‌نشده است

## قرارداد مختصات provider

Open-Meteo مختصات دقیق point را بازنمی‌گرداند؛ `latitude` و `longitude` پاسخ، مرکز سلول grid انتخاب‌شده هستند. بنابراین برابر نبودن آن‌ها با catalog به‌تنهایی خطا نیست. با این حال، ingest پیش از ذخیره‌سازی فاصلهٔ Haversine را کنترل می‌کند و هر پاسخ خارج از آستانهٔ ۵ کیلومتر، یا فاقد مختصات معتبر، قابل استفاده نیست و به‌عنوان batch ناموفق نگه داشته می‌شود. مختصات و ارتفاع برگشتی در `ForecastPointResolution` فقط metadata provider هستند و هرگز catalog truth را overwrite نمی‌کنند.

## observability و retention اجرایی

API متریک‌های داخلی Prometheus را در `/api/v1/metrics/` با Bearer token ارائه می‌کند. requestها با `request_id` و `trace_id` در logهای JSON ثبت می‌شوند؛ debug level به stack ارسال نمی‌شود. Vector فقط فایل‌های JSONL داخل volume اختصاصی Hawatch را به OpenSearch می‌فرستد.

maintenance سبک با command `cleanup_retention --skip-opensearch` اجرا می‌شود. سقف retention هفت روز است و برای hourly forecast، raw snapshot و فایل‌های rotated log اعمال می‌شود؛ آخرین snapshot قابل‌استفاده و رکوردهای متصل به آن برای fallback استثنا هستند. OpenSearch index و Prometheus TSDB فقط وقتی profile `observability` فعال باشد و maintenance متصل به آن stack اجرا شود پاک‌سازی می‌شوند. `ForecastAssessment` در schema فعلی وجود ندارد و command بدون ساختن model جدید، نبود آن را گزارش می‌کند.

Open-Meteo می‌تواند provider آزمایشی باشد؛ انتخاب نهایی هنوز باز است.
