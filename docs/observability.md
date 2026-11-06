# Observability و retention هواچ

این stack فقط برای هواچ است و هیچ SSH، deploy یا تنظیمی خارج از repository انجام نمی‌دهد. برای pilot کم‌هزینه، observability سنگین پیش‌فرض خاموش است.

## اجزا

- API با `RequestMetricsMiddleware`، request/trace id و logهای JSON در console و `hawatch_logs` کار می‌کند.
- `/api/v1/metrics/` exposition استاندارد Prometheus است و با Bearer token محافظت می‌شود. token از Compose secret می‌آید.
- Prometheus فقط API داخلی `api:8000` را scrape می‌کند؛ host port ندارد.
- Grafana با login اجباری و dashboard provisioned، health، inventory نقطه/مسیر/point، error rate، latency، ingest، retry و freshness را نشان می‌دهد.
- Vector فقط volumeی را می‌بیند که API و maintenance برای logهای Hawatch روی آن می‌نویسند و فقط همان JSONLها را به indexهای `hawatch-logs-YYYY.MM.DD` در OpenSearch می‌فرستد.
- OpenSearch و OpenSearch Dashboards برای جست‌وجوی log provision می‌شوند. OpenSearch host port ندارد و OSD فقط port قابل‌تنظیم `OPENSEARCH_DASHBOARDS_PUBLISH_PORT` دارد. اتصال داخلی OSD با کاربر service جداگانه و password قوی `OPENSEARCH_DASHBOARDS_SERVICE_PASSWORD` انجام می‌شود؛ login خود OSD همچنان به credentialهای OpenSearch نیاز دارد.
- `maintenance` هر `RETENTION_INTERVAL_SECONDS` یک‌بار `cleanup_retention` و
  `cleanup_analytics_retention` را اجرا می‌کند. دومی برای سازگاری باقی مانده و
  تعداد eventهای نگه‌داری‌شده را بدون حذف یا تجمیع دوباره گزارش می‌کند.

## profile کم‌هزینه

Compose به‌صورت عادی PostgreSQL، Redis، API، web، ingest one-shot،
`ingest-scheduler`، `sitemap-publisher` و maintenance سبک را اجرا می‌کند.
OpenSearch، Dashboards، Vector، Prometheus و Grafana همگی در profile `observability` هستند:

```bash
docker compose --env-file .env -f infra/compose/compose.yaml up -d
docker compose --env-file .env -f infra/compose/compose.yaml --profile observability up -d
```

برای مشاهدهٔ روزانهٔ پایلوت، endpoint عمومی health برای availability و endpoint authenticated status برای freshness و ingest کافی هستند:

- `GET /api/v1/health/ready/`
- `GET /api/v1/health/status/` با `Authorization: Bearer <HAWATCH_METRICS_TOKEN>`

status از PostgreSQL خوانده می‌شود و تعداد نقطه، مسیر، point، آخرین attempt، آخرین snapshot قابل‌استفاده، retry، خطای ۲۴ ساعت اخیر و تعداد رکورد live را گزارش می‌کند.

## retention

مقدار `HAWATCH_RETENTION_DAYS` عمداً بین ۱ و ۷ محدود است و مقدار پیش‌فرض آن ۷ روز است.

Retention analytics مستقل از این مقدار است: از قابلیت گزارش منابع ورود، event
خام و نشست ناشناس حفظ می‌شوند تا گزارش N روز دلخواه و یکتای واقعی بازه ممکن
باشد. `cleanup_analytics_retention` غیرتخریبی است؛ رشد حجم این جدول‌ها باید پایش
شود. تجمیع‌های ماهانهٔ قدیمی تغییر نمی‌کنند و فقط در گزارش کل زمانِ بدون فیلتر
منبع/ناوبری، با برچسب یکتای تقریبی نمایش داده می‌شوند. دادهٔ حذف‌شدهٔ گذشته
قابل بازسازی نیست؛ مرز پوشش دقیق در گزارش مشخص است. قرارداد کامل در
[`analytics.md`](analytics.md) آمده است.

- `ForecastRecord` فعلی (hourly) بر اساس `generated_at` پاک می‌شود؛ رکوردهای متصل به آخرین snapshot قابل‌استفاده برای fallback حفظ می‌شوند. این policy با دادهٔ demo و live یکسان اعمال می‌شود.
- `ForecastSnapshot` فعلی raw JSON و metadata هر ingest را نگه می‌دارد و بر اساس `generated_at` پاک می‌شود؛ آخرین snapshot قابل‌استفاده استثنای fallback است. `ForecastAssessment` اگر در آینده اضافه شود، command آن را با timestamp استاندارد تشخیص می‌دهد.
- فقط فایل‌های rotated با الگوی `*.jsonl.*` حذف می‌شوند؛ فایل active برای جلوگیری از حذف inode در حال استفاده نگه داشته می‌شود و handler با rotation روزانه و `backupCount=6` بیشتر از هفت روز فایل فعال/چرخیده نگه نمی‌دارد.
- Prometheus با `--storage.tsdb.retention.time=7d` اجرا می‌شود.
- maintenance فقط indexهای دقیقاً با الگوی `hawatch-logs-YYYY.MM.DD` را که قدیمی‌تر از window هستند حذف می‌کند؛ هیچ index ناشناخته‌ای target نمی‌شود.

## متریک‌های مهم

| Metric | معنی |
| --- | --- |
| `hawatch_health_status` | آخرین وضعیت live/ready |
| `hawatch_database_up` | دسترسی DB در scrape اخیر |
| `hawatch_catalog_points` / `routes` / `weather_points` | تعداد فعلی catalog |
| `hawatch_http_requests_total` | تعداد request بر اساس route/status |
| `hawatch_http_errors_total` | پاسخ‌های 4xx/5xx |
| `hawatch_http_request_duration_seconds` | histogram latency |
| `hawatch_ingest_runs_total` | موفق/ناموفق بودن ingest؛ در این branch provider live ندارد و تا اتصال ingest صفر می‌ماند |
| `hawatch_ingest_points_total` | تعداد pointهای موفق/ناموفق ingest |
| `hawatch_ingest_retries_total` | retryهای provider |
| `hawatch_ingest_duration_seconds` | زمان ingest |
| `hawatch_forecast_freshness_records` | تعداد رکوردها بر اساس `data_mode` و `freshness` |

توابع `record_ingest_run`، `record_ingest_points`، `record_ingest_retry` و `record_ingest_duration` در `apps/api/src/hawatch/common/observability.py` برای adapter واقعی provider آماده‌اند و در seed دمو به‌جای ingest metric جعلی ثبت نمی‌شوند.

سه متریک HTTP (request/error/duration) در Redis بین workerها مشترک‌اند؛ هدر
`X-Hawatch-HTTP-Metrics-Scope` در پاسخ metrics، `shared-redis` یا fallback محدود به
`process` را مشخص می‌کند. قطع Redis پاسخ کاربران را fail نمی‌کند؛ retry اتصال
محدود و circuit breaker دارد. ری‌استارت/eviction Redis شمارنده‌ها را reset می‌کند؛
این‌ها دفتر حساب دائمی نیستند. سایر counterها process-local و gaugeهای catalog
و freshness از DB هنگام scrape خوانده می‌شوند. چرخش فایل JSONL با قفل بین‌پردازشی
و بازکردن مجدد inode از ازدست‌رفتن لاگ هنگام rotation چند worker جلوگیری می‌کند.
رجیستری process-local نیز با قفل درون‌پردازشی از نوشتن/خواندن هم‌زمان threadها
محافظت می‌شود؛ تماس Redis خارج از این قفل است تا handlerها به‌خاطر metrics
پشت یک تماس شبکه صف نشوند.

بخش `sitemap` در health/status محافظت‌شده شامل زمان آخرین تلاش و بررسی موفق،
آخرین تغییر محتوا، تعداد URLها، hash و مدت ساخت است. `check_stale=true` یعنی
بیش از سه دورهٔ بازسازی از آخرین موفقیت گذشته است؛ این وضعیت حتی اگر XML قبلی
هنوز 200 باشد نیازمند بررسی publisher است. `sitemap.jsonl` روی volume لاگ حفظ
می‌شود. access log JSON در Nginx نیز زمان کل/upstream، status، bytes و شناسهٔ
gateway و upstream را دارد؛ query string، کوکی و Authorization ثبت نمی‌شوند.
`client_ip` در این لاگ، peer شبکهٔ gateway است و پشت CDN الزاماً IP کاربر نیست.
لاگ API و publisher روی volume پایدار است؛ access log gateway روی stdout و تابع
retention کانتینر است، بنابراین برای نگهداری آن پس از حذف کانتینر باید قبل از
تعویض export شود یا جمع‌آوری بیرونی لاگ فعال باشد.

## secret و اجرای محلی

هیچ secretی در repository نیست. `.env.example` فقط placeholder دارد؛ قبل از اجرا password/token قوی در `.env` قرار بده:

```bash
cp .env.example .env
openssl rand -hex 32   # برای HAWATCH_METRICS_TOKEN
openssl rand -base64 36  # برای OPENSEARCH_INITIAL_ADMIN_PASSWORD، OPENSEARCH_DASHBOARDS_SERVICE_PASSWORD و GRAFANA_ADMIN_PASSWORD
```

سپس مقادیر تولیدشده را فقط در `.env` بگذار. برای اعتبارسنجی بدون اجرای سرویس‌ها:

```bash
docker compose --env-file .env -f infra/compose/compose.yaml config --quiet
```

اجرای observability کامل (اختیاری و مناسب سرور جدا):

```bash
docker compose --env-file .env -f infra/compose/compose.yaml --profile observability up -d --build
```

آدرس‌های قابل‌دسترسی فقط این‌ها هستند:

- frontend: `http://localhost:5173`
- API: `http://localhost:8000`
- Grafana: `http://localhost:${GRAFANA_PUBLISH_PORT}`، پیش‌فرض `3000`
- OpenSearch Dashboards: `http://localhost:${OPENSEARCH_DASHBOARDS_PUBLISH_PORT}`، پیش‌فرض `5601`

PostgreSQL، Redis، OpenSearch، Prometheus و Vector host port ندارند. Redis در stack
عادی همراه `sitemap-publisher` فعال است. OpenSearch، Dashboards، Vector، Prometheus
و Grafana فقط با profile `observability` اجرا می‌شوند.
برای اجرای هم‌زمان یک checkout دیگر، فقط `API_PUBLISH_PORT`، `WEB_PUBLISH_PORT` و `VITE_API_BASE_URL` را در `.env` تغییر بده؛ port پیش‌فرض featureهای فعلی همان ۸۰۰۰ و ۵۱۷۳ است.

برای اجرای دستی retention یا مشاهدهٔ نتیجه:

```bash
docker compose --env-file .env -f infra/compose/compose.yaml exec api python manage.py cleanup_retention --dry-run --skip-opensearch
docker compose --env-file .env -f infra/compose/compose.yaml exec api python manage.py cleanup_analytics_retention --dry-run
docker compose --env-file .env -f infra/compose/compose.yaml logs -f api maintenance
```

خاموش‌کردن همهٔ سرویس‌های همین Compose بدون حذف volume:

```bash
docker compose --env-file .env -f infra/compose/compose.yaml down
```

`down -v` عمداً در مسیر عادی استفاده نمی‌شود چون volume دیتابیس و dashboard را حذف می‌کند.
