# اجرای محلی هواچ

## پیش‌نیاز

- Docker Engine و Docker Compose v2
- برای توسعهٔ خارج از Compose: Node 22، pnpm 9.15.9، Python 3.14، uv، PostgreSQL/PostGIS

## شروع

```bash
cp .env.example .env
# برای pilot، observability سنگین لازم نیست؛ secretهای آن فقط هنگام فعال‌کردن profile لازم‌اند.
docker compose --env-file .env -f infra/compose/compose.yaml up -d --build
```

`.env.example` فقط مستندات است؛ Compose از `.env` واقعی برای runtime استفاده می‌کند.

API هنگام start:

1. منتظر health PostgreSQL می‌ماند
2. migration اجرا می‌کند
3. اگر `DEMO_DATA_ENABLED=true` باشد، `seed_demo_data` را idempotent اجرا می‌کند
4. اگر `DEMO_DATA_ENABLED=false` باشد و `HAWATCH_BOOTSTRAP_LIVE_CATALOG_IF_EMPTY=true` (پیش‌فرض)، فقط وقتی catalog زنده خالی است `bootstrap_live_catalog_if_empty` را اجرا می‌کند — بدون sync/prune در هر restart و بدون فراخوانی Open-Meteo
5. Gunicorn را روی `:8000` با سه worker از نوع gthread و دو thread برای هر worker بالا می‌آورد؛ ظرفیت production در Compose ثابت است.
6. web به‌صورت static production با Nginx روی `:5173` سرو می‌شود

## آدرس‌ها و پورت‌ها

| سرویس | آدرس |
| --- | --- |
| web | http://localhost:5173 |
| api | http://localhost:8000/api/v1/ |
| status | http://localhost:8000/api/v1/health/status/ (Bearer token) |
| postgres | فقط داخل شبکهٔ Compose روی `postgres:5432` |
| redis (optional) | فقط داخل شبکهٔ Compose روی `redis:6379`؛ profile `cache` |
| Grafana (optional) | localhost:`GRAFANA_PUBLISH_PORT`؛ فقط profile `observability` |
| OpenSearch Dashboards (optional) | localhost:`OPENSEARCH_DASHBOARDS_PUBLISH_PORT`؛ فقط profile `observability` |

## توقف و لاگ

```bash
docker compose --env-file .env -f infra/compose/compose.yaml logs -f
docker compose --env-file .env -f infra/compose/compose.yaml down
```

حذف volume دیتابیس:

```bash
docker compose -f infra/compose/compose.yaml down -v
```

## دادهٔ دمو

دادهٔ هوا از generator قطعی با timezone `Asia/Tehran` ساخته می‌شود. seed version پیش‌فرض `hawatch-demo-v1` است. همان صفحه در همان تاریخ/ساعت محلی مقدار یکسان می‌دهد و با تغییر date/hour عوض می‌شود.

غیرفعال‌کردن دمو برای مسیر live:

```bash
DEMO_DATA_ENABLED=false
```

Bootstrap کاتالوگ توچال بدون ingestion:

```bash
cd apps/api
uv run python manage.py bootstrap_live_catalog_if_empty
# یا import صریح (غیرتخریبی): uv run python manage.py seed_tochal_catalog
```

Ingestion از handlerهای API صدا زده نمی‌شود. سرویس one-shot برای اجرای دستی وجود دارد و `ingest-scheduler` در Compose آن را هر روز ساعت ۰۰، ۰۶، ۱۲ و ۱۸ به وقت تهران اجرا می‌کند:

```bash
docker compose --env-file .env -f infra/compose/compose.yaml run --rm ingest
```

برای مشاهدهٔ scheduler:

```bash
docker compose --env-file .env -f infra/compose/compose.yaml logs -f ingest-scheduler
```

Retention: snapshotهای خام و رکوردهای forecast قدیمی‌تر از ۷ روز پاک می‌شوند؛ آخرین snapshot قابل‌استفاده برای fallback حفظ می‌شود. ingest با upsert داخل transaction انجام می‌شود و شکست کامل، دادهٔ قبلی را حذف نمی‌کند. maintenance سبک این cleanup را روزانه اجرا می‌کند.

پنجرهٔ پیش‌فرض ingest هفت روز تقویمی است: امروز تا شش روز بعد
(`OPEN_METEO_FORECAST_DAYS=7` و `OPEN_METEO_PAST_DAYS=0`). روز گذشته فقط از
ingest قبلی در دیتابیس نگه داشته می‌شود و دوباره از Open-Meteo گرفته نمی‌شود.

## توسعهٔ frontend بدون Docker web

```bash
pnpm install
pnpm dev
```

`VITE_API_BASE_URL` به‌صورت portable روی `/api/v1` تنظیم می‌شود؛ Vite در development این مسیر را به `http://localhost:8000` proxy می‌کند.

## توسعهٔ API بدون Docker api

با یک Postgres/PostGIS در حال اجرا:

```bash
cd apps/api
uv sync --group dev
export DJANGO_SETTINGS_MODULE=hawatch.config.settings.local
# از .env محلی برای OPEN_METEO_* و DEMO_DATA_ENABLED استفاده کنید
uv run python manage.py migrate
uv run python manage.py seed_demo_data   # یا seed_tochal_catalog وقتی DEMO_DATA_ENABLED=false
uv run python manage.py runserver 0.0.0.0:8000
```

## تست

```bash
pnpm test
docker compose -f infra/compose/compose.yaml exec api pytest
docker compose -f infra/compose/compose.yaml config
```

pytest روی میزبان بدون GDAL/PostGIS معمولاً fail می‌شود؛ تست backend را داخل container اجرا کنید.

تست‌ها همیشه از `hawatch.config.settings.test` استفاده می‌کنند: provider خارجی
غیرفعال است، ساعت تقویمی هر تست روی یک زمان مرجع مستقل شروع می‌شود و کش و
شمارنده‌ها بین تست‌ها مشترک نیستند. timerهای elapsed/performance واقعی‌اند؛
آزمون‌های OS/process با marker `real_clock` زمان واقعی دارند. Redis محیط runtime
به pytest ارث نمی‌رسد؛ پاک‌سازی کش تست نباید Redis سایت را پاک کند.

برای اجرای کامل و سریع‌تر بکند با دیتابیس‌های مستقل هر worker:

```bash
cd apps/api
uv run pytest -n 4 --strict-markers --strict-config
```

تست‌های اسکریپت‌ها جدا هستند و از ریشهٔ repository اجرا می‌شوند:

```bash
uv run --project apps/api pytest scripts
```

تست‌های Redis بین‌پردازشی فقط با `HAWATCH_TEST_REDIS_URL` به یک Redis **اختصاصی
و دورریختنیِ تست** وصل می‌شوند؛ هرگز URL Redis سایت را برای این متغیر نگذارید.
تست مهاجرت تاریخی یک DB موقت با نام `hawatch_legacy_test_*` می‌سازد، فقط forward
اجرا می‌کند و در پایان همان DB را حذف می‌کند؛ schema دیتابیس اصلی تست عقب برده
نمی‌شود. کاربر PostgreSQL تست باید اجازهٔ ساخت دیتابیس داشته باشد.

تنظیمات pytest، catalog کامل را برای تست‌های جست‌وجو و API وارد می‌کند اما
Forecast دمو را فقط برای نقاط زنجیرهٔ مسیرهای توچال و گهر می‌سازد؛ این نقاط تمام
endpointهای forecast مورد استفادهٔ suite را پوشش می‌دهند و از ساخت ده‌ها هزار
رکورد تکراری برای تست‌های بدون نیاز جلوگیری می‌کنند. تنظیم فوق فقط در
`hawatch.config.settings.test` فعال است و روی runtime یا ingest واقعی اثری ندارد.

fixture مشترک، کاتالوگ جاری را یک‌بار با importer واقعی می‌سازد و آن تراکنش را
rollback می‌کند؛ سپس برای هر تست کپی مستقل ردیف‌ها و forecast تازه ایجاد می‌شود.
تست‌های خود importer/sync همچنان مسیر واقعی import را اجرا می‌کنند. انتظارهای
نام/ارتفاع، زنجیره، زمان‌بندی و عضویت از catalog فعلی و مسافت از پروفایل بازبینی‌شده
می‌آیند؛ invariants مثل canonical یکتا، زنجیرهٔ پیوسته، زمان صعودی، حفظ داده در
پاسخ ناقص و نبود لینک ساختگی همچنان مستقل و سخت‌گیرانه بررسی می‌شوند.

## خارج از scope این milestone

- OTP واقعی و session ورود (فعلاً flow آزمایشی frontend با مقادیر ثابتِ فقط داخل کد و انقضای ۳۰روزه فعال است؛ مقدارها در UI نمایش داده نمی‌شوند)
- فراخوانی live Open-Meteo از handlerهای API یا از CI بدون mock
- Redis اجباری، Celery، Kafka، data lake
- Kubernetes manifests
- صفحهٔ point link و share server-side
