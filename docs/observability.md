# Observability و retention هواچ

این stack فقط برای هواچ است و هیچ SSH، deploy یا تنظیمی خارج از repository انجام نمی‌دهد.

## اجزا

- API با `RequestMetricsMiddleware`، request/trace id و logهای JSON در console و `hawatch_logs` کار می‌کند.
- `/api/v1/metrics/` exposition استاندارد Prometheus است و با Bearer token محافظت می‌شود. token از Compose secret می‌آید.
- Prometheus فقط API داخلی `api:8000` را scrape می‌کند؛ host port ندارد.
- Grafana با login اجباری و dashboard provisioned، health، inventory مقصد/مسیر/point، error rate، latency، ingest، retry و freshness را نشان می‌دهد.
- Vector فقط volumeی را می‌بیند که API و maintenance برای logهای Hawatch روی آن می‌نویسند و فقط همان JSONLها را به indexهای `hawatch-logs-YYYY.MM.DD` در OpenSearch می‌فرستد.
- OpenSearch و OpenSearch Dashboards برای جست‌وجوی log provision می‌شوند. OpenSearch host port ندارد و OSD فقط port قابل‌تنظیم `OPENSEARCH_DASHBOARDS_PUBLISH_PORT` دارد. اتصال داخلی OSD با کاربر service جداگانه و password قوی `OPENSEARCH_DASHBOARDS_SERVICE_PASSWORD` انجام می‌شود؛ login خود OSD همچنان به credentialهای OpenSearch نیاز دارد.
- `maintenance` هر `RETENTION_INTERVAL_SECONDS` یک‌بار `cleanup_retention` را اجرا می‌کند.

## retention

مقدار `HAWATCH_RETENTION_DAYS` عمداً بین ۱ و ۷ محدود است و مقدار پیش‌فرض آن ۷ روز است.

- `ForecastRecord` فعلی (hourly) بر اساس `generated_at` پاک می‌شود.
- مدل‌های `ForecastSnapshot` و `ForecastAssessment` در schema فعلی وجود ندارند؛ command آن‌ها را ایجاد نمی‌کند، اما اگر بعداً در app forecasts با timestampهای استاندارد اضافه شوند، نام مدل و فیلد timestamp را تشخیص می‌دهد.
- فقط فایل‌های rotated با الگوی `*.jsonl.*` حذف می‌شوند؛ فایل active برای جلوگیری از حذف inode در حال استفاده نگه داشته می‌شود و handler با rotation روزانه و `backupCount=6` بیشتر از هفت روز فایل فعال/چرخیده نگه نمی‌دارد.
- Prometheus با `--storage.tsdb.retention.time=7d` اجرا می‌شود.
- maintenance فقط indexهای دقیقاً با الگوی `hawatch-logs-YYYY.MM.DD` را که قدیمی‌تر از window هستند حذف می‌کند؛ هیچ index ناشناخته‌ای target نمی‌شود.

## متریک‌های مهم

| Metric | معنی |
| --- | --- |
| `hawatch_health_status` | آخرین وضعیت live/ready |
| `hawatch_database_up` | دسترسی DB در scrape اخیر |
| `hawatch_catalog_destinations` / `routes` / `weather_points` | تعداد فعلی catalog |
| `hawatch_http_requests_total` | تعداد request بر اساس route/status |
| `hawatch_http_errors_total` | پاسخ‌های 4xx/5xx |
| `hawatch_http_request_duration_seconds` | histogram latency |
| `hawatch_ingest_runs_total` | موفق/ناموفق بودن ingest؛ در این branch provider live ندارد و تا اتصال ingest صفر می‌ماند |
| `hawatch_ingest_points_total` | تعداد pointهای موفق/ناموفق ingest |
| `hawatch_ingest_retries_total` | retryهای provider |
| `hawatch_ingest_duration_seconds` | زمان ingest |
| `hawatch_forecast_freshness_records` | تعداد رکوردها بر اساس `data_mode` و `freshness` |

توابع `record_ingest_run`، `record_ingest_points`، `record_ingest_retry` و `record_ingest_duration` در `apps/api/src/hawatch/common/observability.py` برای adapter واقعی provider آماده‌اند و در seed دمو به‌جای ingest metric جعلی ثبت نمی‌شوند.

در این milestone registry متریک‌های counter/histogram داخل process است؛ gaugeهای catalog و freshness از DB هنگام scrape خوانده می‌شوند. چون provider live/worker هنوز در این checkout وجود ندارد، ingest counterها فعلاً صفر می‌مانند. پیش از اجرای چند worker یا ingest جداگانه در production باید registry مشترک یا multiprocess اضافه شود تا counterها بین processها کامل جمع شوند.

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

اجرای کامل:

```bash
docker compose --env-file .env -f infra/compose/compose.yaml up -d --build
```

آدرس‌های قابل‌دسترسی فقط این‌ها هستند:

- frontend: `http://localhost:5173`
- API: `http://localhost:8000`
- Grafana: `http://localhost:${GRAFANA_PUBLISH_PORT}`، پیش‌فرض `3000`
- OpenSearch Dashboards: `http://localhost:${OPENSEARCH_DASHBOARDS_PUBLISH_PORT}`، پیش‌فرض `5601`

PostgreSQL، Redis، OpenSearch، Prometheus و Vector host port ندارند. Redis همچنان optional و فقط با profile `cache` است.
برای اجرای هم‌زمان یک checkout دیگر، فقط `API_PUBLISH_PORT`، `WEB_PUBLISH_PORT` و `VITE_API_BASE_URL` را در `.env` تغییر بده؛ port پیش‌فرض featureهای فعلی همان ۸۰۰۰ و ۵۱۷۳ است.

برای اجرای دستی retention یا مشاهدهٔ نتیجه:

```bash
docker compose --env-file .env -f infra/compose/compose.yaml exec api python manage.py cleanup_retention --dry-run
docker compose --env-file .env -f infra/compose/compose.yaml logs -f api maintenance vector
```

خاموش‌کردن همهٔ سرویس‌های همین Compose بدون حذف volume:

```bash
docker compose --env-file .env -f infra/compose/compose.yaml down
```

`down -v` عمداً در مسیر عادی استفاده نمی‌شود چون volume دیتابیس و dashboard را حذف می‌کند.
