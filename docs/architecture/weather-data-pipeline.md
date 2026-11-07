# pipeline دادهٔ هوا

## وضعیت فعلی

API از forecastهای دمو یا live در PostgreSQL می‌خواند. frontend منبع داده را نمی‌بیند؛ فقط contract داخلی را مصرف می‌کند.

- `DEMO_DATA_ENABLED=true`: seed دمو برای توسعه
- `DEMO_DATA_ENABLED=false`: اگر catalog زنده خالی باشد `bootstrap_live_catalog_if_empty`؛ در غیر این صورت DB دست‌نخورده می‌ماند. forecast فقط از snapshotهای live؛ API هرگز Open-Meteo را صدا نمی‌زند. Ingest از WeatherPointهای فعال DB است (نه filename JSON).

## مسیر داده

```text
provider (one-shot management command، هر ۶ ساعت با `ingest-scheduler` داخلی در ساعت‌های ۰۰، ۰۶، ۱۲ و ۱۸ تهران)
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
- صف وزنی مشترک برای همهٔ درخواست‌های runtime؛ جزئیات و retry در بخش سهمیه
- جلوگیری از اجرای هم‌زمان ingestion با advisory lock
- آخرین دادهٔ سالم برای نقاط موفق با bulk upsert داخل transaction جایگزین می‌شود؛ نقاط ناموفق batch قبلی را نگه می‌دارند
- هیچ delete قبل از موفقیت persistence انجام نمی‌شود؛ شکست provider یا خطای DB، آخرین دادهٔ قابل‌استفاده را حفظ می‌کند
- برای هر `WeatherPoint + forecast_at + seed_version` فقط یک رکورد live نگه داشته می‌شود
- default پنجرهٔ provider برابر `forecast_days=10` و `past_days=0` است: امروز تا
  نه روز بعد درخواست می‌شود. رکوردهای روز گذشته که از ingest قبلی در DB هستند
  نگه داشته می‌شوند اما دوباره از provider درخواست نمی‌شوند؛ رکوردهای live قدیمی‌تر
  از روز گذشته حذف می‌شوند.
- پاسخ provider فقط وقتی به catalog point متصل می‌شود که `latitude` و `longitude` معتبر داشته باشد و مرکز grid حداکثر ۶ کیلومتر با مختصات درخواستی فاصله داشته باشد؛ پاسخ دور یا ناقص فقط همان نقطه را رد می‌کند، نه همسایه‌های سالم در batch.
- منبع اصلی `best_match` است. برای grid دور در حالت `land` ابتدا همان مدل با
  `nearest` امتحان می‌شود. سپس هر نقطه‌ای که هنوز پاسخ معتبر و رکورد ساعتی
  قابل‌ذخیره ندارد (از جمله HTTP/transport ناموفق به‌جز ۴۲۹، پاسخ خالی یا نامعتبر)، یک
  مرحلهٔ fallback با `models=ecmwf_ifs` و `cell_selection=nearest` دارد؛ retry
  محدود transport همچنان برقرار است. این سیاست عمومی است و فهرست slug ندارد.
- fallback مختصات و elevation مقصد، متغیرها و پنجرهٔ forecast را حفظ می‌کند و
  از همان gate فاصله و normalization عبور می‌کند. شکست هر دو مدل دادهٔ قبلی
  نقطه را نگه می‌دارد؛ داده‌های سالم best_match با ECMWF جایگزین نمی‌شوند.
- مدل هر batch در raw snapshot ثبت می‌شود و `models_param` مدل‌های درخواست‌شده
  را منعکس می‌کند، نه تضمین موفقیت آن‌ها. متغیرهای ناموجود ECMWF، مانند ارتفاع
  تراز انجماد، ناموجود باقی می‌مانند و ساخته نمی‌شوند. API و frontend همچنان
  فقط forecast ذخیره‌شده را مصرف می‌کنند؛ تغییر UI یا schema لازم نیست.
- برای pointهایی که ارتفاع catalog دارند، `cell_selection=land` همراه با elevation صریح استفاده می‌شود؛ برای pointهای بدون ارتفاع catalog، `cell_selection=nearest` استفاده می‌شود تا انتخاب land cell دور، weather نقطه را جابه‌جا نکند
- تمام درخواست‌های providerهای هواشناسی از `WeatherHttpTransport` عبور می‌کنند.
  پروکسی‌های SOCKS5 در مدل `WeatherProxy` و داخل PostgreSQL نگه‌داری می‌شوند؛
  URI رمزنگاری‌شده است و فقط superuser می‌تواند آن را در Admin مدیریت کند.
  انتخاب فعال‌ها با cursor قفل‌شدهٔ `WeatherProxyRotation` به‌صورت round-robin
  انجام می‌شود (بر اساس `sort_order` و سپس شناسه). هر retry نیز درخواست جدیدی
  است و proxy بعدی را می‌گیرد. اگر هیچ proxy فعال نباشد، درخواست مستقیم است؛ در
  صورت وجود proxy فعال، شکست همهٔ آن‌ها به direct fallback تبدیل نمی‌شود.
- مقدار `WEATHER_PROXY_ENCRYPTION_KEY` باید بین api، ingest و scheduler یکسان و
  خارج از Git باشد. `scripts/deploy.sh` آن را در `.env` سرور در صورت نبودن
  تولید می‌کند. credentialها هرگز در fixture/migration یا log چاپ نمی‌شوند.
- اجرای `seed_weather_proxies --interactive` یا مقدارهای موقت
  `WEATHER_PROXY_CA_URL` و `WEATHER_PROXY_US_URL` دو proxy اولیه را به‌صورت
  idempotent وارد DB می‌کند؛ پس از ورود می‌توان آن‌ها را از Admin ویرایش، فعال،
  غیرفعال یا حذف کرد.

## قرارداد مختصات provider

Open-Meteo مختصات دقیق point را بازنمی‌گرداند؛ `latitude` و `longitude` پاسخ، مرکز سلول grid انتخاب‌شده هستند. بنابراین برابر نبودن آن‌ها با catalog به‌تنهایی خطا نیست. با این حال، ingest پیش از ذخیره‌سازی فاصلهٔ Haversine را کنترل می‌کند و هر پاسخ خارج از آستانهٔ ۶ کیلومتر، یا فاقد مختصات معتبر، قابل استفاده نیست و به‌عنوان نقطهٔ ناموفق نگه داشته می‌شود. مختصات و ارتفاع برگشتی در `ForecastPointResolution` فقط metadata provider هستند و هرگز catalog truth را overwrite نمی‌کنند.

## سهمیه، ترتیب و افزایش مقیاس

- هر batch حداکثر ۲۵ نقطه دارد؛ مقدار قدیمی ۱۰۰ در env یا آرگومان نیز به ۲۵
  محدود می‌شود. نقاط فاقد forecast و سپس نقاط با قدیمی‌ترین زمان دریافت، در
  گروه‌های انتخاب cell/elevation زودتر قرار می‌گیرند.
- `WeatherHttpTransport` قبل از انتخاب پروکسی، در Redis سهمیه رزرو می‌کند.
  همهٔ فرایندها و مدل‌ها کلید مشترک دارند. سقف هم‌زمانی یک درخواست است؛ lease
  حین HTTP تمدید و بعد از پاسخ آزاد می‌شود. انتظارها تراکنش نوشتن DB ندارند؛
  advisory lock کل ingest طبق قبل باقی است.
- وزن تقریبی درخواست برابر تعداد نقاط × تعداد مدل‌های صریح ×
  `max(1, variables/10)` × `max(1, days/14)` است. `best_match` یک انتخاب صریح
  است. هر تلاش حتی اگر ناموفق باشد، محافظه‌کارانه در بودجه حساب می‌شود.
- حداقل فاصلهٔ شروع درخواست‌ها ۱۰ ثانیه است. سقف‌های rolling مشترک
  ۳۰۰ واحد در ۶۰ ثانیه، ۴۵۰۰ در یک ساعت و ۹۰۰۰ در ۲۴ ساعت‌اند. پرشدن هر پنجره
  باعث انتظار تا آزادشدن سهمیه می‌شود؛ سقف ثابت زمان اجرای job وجود ندارد.
  scheduler بعد از پایان job، نزدیک‌ترین زمان برنامه‌ریزی‌شدهٔ بعدی را انتخاب
  می‌کند و اجراهای جاافتاده را هم‌زمان راه نمی‌اندازد.
- پاسخ ۴۲۹ باعث cooldown مشترک حداقل ۶۵، سپس ۱۲۰ و ۱۸۰ ثانیه می‌شود؛ هدر
  `Retry-After` به شکل ثانیه یا HTTP-date و مقدار JSON پشتیبانی می‌شود و هیچ
  سقف ۳۰ثانیه‌ای آن را قطع نمی‌کند. برای خطای hourly/daily، انتظار حداقل
  ۳۶۰۵/۸۶۴۰۵ ثانیه است. بعد از ۴۲۹، فاصلهٔ ارسال موقتاً دوبرابر می‌شود
  (تا ۶۰ ثانیه) و این کاهش سرعت تا یک ساعت بدون ۴۲۹ باقی می‌ماند.
- بعد از اتمام retryهای ۴۲۹، مدل عوض نمی‌شود و درخواست‌های باقی‌ماندهٔ همان
  collection ارسال نمی‌شوند. نتایج سالم ذخیره و دادهٔ قبلی بقیه نگه داشته
  می‌شود. خرابی هماهنگ‌کنندهٔ سهمیه هم مجوز ارسال بدون محدودیت نیست.
- `weather-quota` یک Redis داخلی ۳۲MB با `noeviction` و AOF/`appendfsync always`
  روی volume پایدار است؛ از Redis کشِ قابل‌حذف جداست. namespace مشترک با
  `OPEN_METEO_RATE_LIMIT_SCOPE` و اتصال با `OPEN_METEO_RATE_LIMIT_REDIS_URL`
  تنظیم می‌شود. استیج سرویس و volume مستقل دارد؛ آزمایش‌های pytest هرگز از
  Redis runtime استفاده نمی‌کنند. فرایندهایی که واقعاً یک سهمیهٔ provider را
  مصرف می‌کنند باید coordinator و scope مشترک داشته باشند.
- زمان دریافت واقعی هر batch در raw snapshot و `generated_at` رکوردهای آن
  ذخیره می‌شود؛ پایان یک اجرای طولانی، دادهٔ قدیمی batchهای اول را تازه جلوه
  نمی‌دهد. ذخیره‌سازی نهایی و یک بار invalidation/warm کش، طبق چرخهٔ قبلی است.
- `weather.request_attempt` برای تک‌تک تلاش‌ها، زمان، وزن، مدل، وضعیت HTTP،
  شمارهٔ تلاش، شناسهٔ پروکسی و زمان انتظار را ثبت می‌کند؛ URL کامل، مختصات و
  credential در این log نیست. `weather.quota_wait` علت انتظار را نشان می‌دهد.
  `weather.collection_finished` تعداد واقعی نقاط به‌روزشده را گزارش می‌کند؛
  برگشت snapshot قدیمی در شکست کامل به معنی موفقیت collection نیست.
- رشد تعداد نقاط، طول صف را بیشتر می‌کند. اگر بودجهٔ روزانه برای چهار چرخهٔ
  شش‌ساعته کافی نباشد، رویداد `weather.quota_capacity` ثبت می‌شود؛ سهمیهٔ محدود
  را نمی‌توان با انتظار کوتاه یا چرخش پروکسی به ظرفیت نامحدود تبدیل کرد.
  برای حفظ همان تناوب در حجم بالاتر، بودجهٔ واقعی/پلن provider باید افزایش یابد.
- rollout معمول، سرویس quota را بدون بازسازی postgres/کش بالا می‌آورد. volume
  quota را برای رفع خطا پاک نکنید؛ حذف آن سابقهٔ ۲۴ساعته را از بین می‌برد.
  دریافت‌های دستی خارج از transport (مثلاً validator مستقل محلی) در این دفتر
  ثبت نمی‌شوند؛ در ارزیابی مصرف provider باید جدا در نظر گرفته شوند.

مرجع محاسبهٔ سهمیه: https://open-meteo.com/en/pricing

## observability و retention اجرایی

API متریک‌های داخلی Prometheus را در `/api/v1/metrics/` با Bearer token ارائه می‌کند. requestها با `request_id` و `trace_id` در logهای JSON ثبت می‌شوند؛ debug level به stack ارسال نمی‌شود. Vector فقط فایل‌های JSONL داخل volume اختصاصی Hawatch را به OpenSearch می‌فرستد.

maintenance سبک با command `cleanup_retention --skip-opensearch` اجرا می‌شود. سقف retention هفت روز است و برای hourly forecast، raw snapshot و فایل‌های rotated log اعمال می‌شود؛ آخرین snapshot قابل‌استفاده و رکوردهای متصل به آن برای fallback استثنا هستند. OpenSearch index و Prometheus TSDB فقط وقتی profile `observability` فعال باشد و maintenance متصل به آن stack اجرا شود پاک‌سازی می‌شوند. `ForecastAssessment` در schema فعلی وجود ندارد و command بدون ساختن model جدید، نبود آن را گزارش می‌کند.

Open-Meteo می‌تواند provider آزمایشی باشد؛ providerهای بعدی باید از همین
transport مشترک استفاده کنند و نباید مستقیماً `urlopen` یا client دیگری را صدا
بزنند.
