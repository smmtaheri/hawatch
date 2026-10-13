# هواچ (Hawatch)

هواچ محصولی فارسی و تصمیم‌محور برای دیدن هوای نقطه و برنامه‌ریزی مسیر است. کاربر به‌جای دیدن یک دمای منفرد، شرایط نقطه و تغییرات آب‌وهوا را در طول مسیر می‌بیند تا بتواند زمان حرکت، مسیر و امکان ادامه‌دادن یا برگشتن را آگاهانه‌تر انتخاب کند.

## وضعیت این repository

این repository شامل design handoff، مستندات محصول، و اولین نسخهٔ محلی اجرایی است:

- frontend: `apps/web` — React + TypeScript + Vite
- backend: `apps/api` — Django + Django REST Framework + PostGIS
- local/pilot stack: `infra/compose/compose.yaml` — web production، api، postgres، ingest one-shot، scheduler شش‌ساعته و maintenance سبک
- gateway: Nginx روی port قابل‌تنظیم `NGINX_PUBLISH_PORT` (پیش‌فرض `80`) برای health check و proxy وب/API

مسیر `/login?returnTo=…` و لایهٔ responsive ورود در دسترس است: ورود عادی روی همان صفحه به‌صورت overlay باز می‌شود (mobile تمام‌صفحه و desktop dialog). login موقت allowlist و کد ثابت را فقط از env سرور می‌خواند و session امن Django می‌سازد؛ OTP واقعی هنوز جایگزین نشده است. سیاست روزهای forecast و طرح‌های دسترسی از Django Admin مدیریت می‌شوند؛ جزئیات در [`docs/page-specs/login-behavior.md`](docs/page-specs/login-behavior.md) است.

رفتار خروج، همگام‌سازی حساب بین تب‌های همان مرورگر و نشست مستقل ادمین در
[docs/session-lifecycle.md](docs/session-lifecycle.md) مستند شده است.

## صفحات این نسخه

- **Home** `/`
- **Point Forecast**
  - Point role: `/points/tochal`
  - Point role: `/points/tochal-sarband-square` (همان قالب بصری Point؛ بدون planner)
- **Route** `/routes/tochal-darband` (و سایر مسیرهای مستند)

Home جست‌وجوی unified همهٔ نقاط را با پیشنهادهای prefix و debounce کوتاه انجام می‌دهد. کلیک روی نقطه از Route به URL canonical آن می‌رود و context برنامه‌ریزی مسیر را برای بازگشت حفظ می‌کند.

## اجرای محلی

پیش‌نیاز: Docker و Docker Compose.

```bash
cp .env.example .env
docker compose --env-file .env -f infra/compose/compose.yaml up -d --build
```

پس از ساخته‌شدن imageها:

```bash
docker compose --env-file .env -f infra/compose/compose.yaml up -d
```

- frontend: http://localhost:5173
- API: http://localhost:8000/api/v1/
- gateway: http://localhost (وب و API از یک ورودی)
- health live: http://localhost:8000/api/v1/health/live/
- health ready: http://localhost:8000/api/v1/health/ready/
- وضعیت عملیاتی: http://localhost:8000/api/v1/health/status/ (با Bearer token)

در Compose، `ingest-scheduler` command یک‌بارهٔ ingest را هر روز ساعت ۰۰، ۰۶، ۱۲ و ۱۸ به وقت تهران اجرا می‌کند. اجرای دستی ingest همچنان ممکن است:

```bash
docker compose --env-file .env -f infra/compose/compose.yaml run --rm ingest
```

برای cadence شش‌ساعته، `FORECAST_STALE_AFTER_HOURS` را حداقل `7` نگه دارید؛ deploy script اگر این مقدار در `.env` وجود نداشته باشد مقدار ۷ را می‌گذارد.

درخواست‌های provider هواشناسی از proxyهای SOCKS5 فعال در مدل `WeatherProxy` با
چرخش round-robin عبور می‌کنند. credentialها رمزنگاری‌شده در DB هستند و فقط
superuser آن‌ها را در Admin مدیریت می‌کند. برای ورود اولیهٔ دو proxy، بعد از
اجرای migration از `python manage.py seed_weather_proxies --interactive` استفاده
کنید؛ اگر هیچ proxy فعالی نباشد رفتار به درخواست مستقیم برمی‌گردد.

Observability سنگین پیش‌فرض خاموش است و فقط در صورت نیاز فعال می‌شود:

```bash
docker compose --env-file .env -f infra/compose/compose.yaml --profile observability up -d
```

توقف:

```bash
docker compose --env-file .env -f infra/compose/compose.yaml down
```

لاگ‌ها:

```bash
docker compose -f infra/compose/compose.yaml logs -f api web postgres
```

جزئیات بیشتر در `docs/local-development.md` و `infra/compose/README.md`.

آمار بازدید داخلی Point و Route (بدون ابزار خارجی) در Django Admin توضیح داده
شده است: [`docs/analytics.md`](docs/analytics.md).

SEO و HTML اولیهٔ قابل‌خزش Home، Point و Route در
[`docs/seo.md`](docs/seo.md) توضیح داده شده است.

سناریوی کامل backup، به‌روزرسانی backup و restore اضطراری روی سرور جدید در
[`docs/backup-restore.md`](docs/backup-restore.md) مستند شده است.

قرارداد رنگ، مرزهای عددی، دادهٔ ناقص و محدودیت هشدارهای مقصد و مسیر در
[docs/weather-warnings.md](docs/weather-warnings.md) مستند شده است.

## محیط Stage

استیج پیش‌بینی هفته روی برنچ `stage` مستقل از production است و از فرمان محلی
`bash scripts/deploy-stage-hawatch` استفاده می‌کند. دیتابیس و Redis استیج مستقل‌اند؛
دادهٔ واقعی عمومی در اولین راه‌اندازی با export فقط‌خواندنی کپی می‌شود.
راهنمای اجرا از سیستم محلی در [docs/stage-deployment.md](docs/stage-deployment.md)
و قرارداد هفته/کش/تجهیزات در [docs/week-forecast.md](docs/week-forecast.md) است.
منابع طراحی و گالری v5 در [راهنمای منابع](docs/design/forecast-v5/README.md) مرتب شده‌اند.
`deploy-hawatch` همچنان فقط production/main را منتشر می‌کند.

## استقرار سریع روی سرور

برای نصب پیش‌نیازها، clone، ساخت امن `.env`، اجرای Compose سبک و health check از اسکریپت زیر استفاده کنید:

```bash
apt-get update && apt-get install -y ca-certificates curl
curl -fsSL https://raw.githubusercontent.com/smmtaheri/hawatch/main/scripts/deploy.sh -o /root/hawatch-deploy.sh
chmod 700 /root/hawatch-deploy.sh
PUBLIC_HOST=SERVER_IP /root/hawatch-deploy.sh
```

راهنمای کامل، گزینه‌های اسکریپت و دستور توقف در `docs/deployment.md` است. این اسکریپت به‌صورت پیش‌فرض observability سنگین را اجرا نمی‌کند.

## محل فایل `.env`

فایل runtime در ریشهٔ پروژه قرار دارد:

```text
/root/hawatch/.env        # روی سرور
./.env                    # در checkout محلی
```

`.env` عمداً در Git ignore است، permission آن باید `600` باشد و شامل secret واقعی است؛ آن را commit یا عمومی نکنید. برای انتقال همین تنظیمات به سرور بعدی، فایل را امن کپی کنید و فقط IP را در مقادیر مربوط به host عوض کنید:

```bash
scp .env root@NEW_SERVER:/root/hawatch/.env
ssh root@NEW_SERVER "chmod 600 /root/hawatch/.env && sed -i 's/202.133.89.120/NEW_IP/g' /root/hawatch/.env"
```

پس از انتقال، اسکریپت `scripts/deploy.sh` را اجرا کنید تا Compose و تنظیمات runtime را validate کند. هر deploy ابتدا فقط containerهای Compose پروژهٔ Hawatch را با `down --remove-orphans` متوقف می‌کند و سپس با `--force-recreate` بالا می‌آورد؛ volumeهای دیتابیس حفظ می‌شوند. برای توسعهٔ local تازه، از `.env.example` استفاده کنید و snapshot واقعی سرور را روی GitHub قرار ندهید.

## افزودن نقطه و اعتبارسنجی weather

راهنمای workflow در [`docs/catalog-onboarding.md`](docs/catalog-onboarding.md)
است. برای افزودن معمولی و افزایشی نقطه، بک‌آپ دیتابیس، migration، restart یا
sync کل catalogها لازم نیست. نقطهٔ بدون مسیر را با `routes: {}` ثبت کنید؛ GPX و
ساخت فولدر `tracks/` فقط وقتی لازم‌اند که واقعاً Route پیاده تعریف می‌شود.

یک catalog نسخه‌دار در `apps/api/fixtures/catalog/` بسازید/به‌روزرسانی کنید،
هویت و تکراری‌نبودن نقطه را بررسی کنید، سپس wrapper را یک‌بار در حالت apply اجرا
کنید. این wrapper اعتبارسنجی Open-Meteo/ارتفاع، check شکل catalog، import اتمیک،
ingest هدفمند و preflight همان نقطه را انجام می‌دهد:

```bash
python3 scripts/publish_catalog.py \
  --catalog apps/api/fixtures/catalog/my_point_v1.json \
  --host hawatch \
  --point my-point \
  --apply
```

`--apply` فایل را به سرور کپی نمی‌کند؛ JSON را از stdin به API می‌فرستد. آن را
بدون `--apply` و سپس دوباره با `--apply` اجرا نکنید، چون مرحلهٔ provider در هر
اجرا تکرار می‌شود. پس از موفقیت، fixture را commit/push کنید تا سابقهٔ نسخه‌دار
در Git بماند. import عادی غیرتخریبی است؛ `--prune` استفاده نکنید.

`sync_catalog --dry-run/--apply` برای همگام‌سازی عمدیِ مجموعهٔ کامل fixtureها یا
پاک‌سازی/تغییرات گسترده است، نه افزودن یک نقطه. بک‌آپ برای افزودن افزایشی لازم
نیست؛ بک‌آپ فقط برای عملیات تخریبی/گسترده، migration پرریسک یا بنا به درخواست
صریح اپراتور گرفته می‌شود. جزئیات قرارداد و استثناها در
[`docs/catalog-onboarding.md`](docs/catalog-onboarding.md) و
[`docs/catalog-and-weather-validation.md`](docs/catalog-and-weather-validation.md)
است.

## افزودن نقطه/مسیر بدون deploy

Database منبع حقیقت runtime است؛ JSON فقط bootstrap/import است. `tracks/` فقط evidence محلی است و در Git ignore می‌شود.

### Draft در برابر Active

- `is_active=false` روی Point / Route / WeatherPoint یعنی پیش‌نویس یا غیرفعال: از API عمومی، siblingها، related routes، search و شمارش health حذف می‌شود.
- `ingest_enabled=false` نقطه را از ingest کنار می‌گذارد حتی اگر active باشد.
- فعال‌بودن خود WeatherPoint و یا پیوند آن به Route فعال، وضعیت عمومی و ingest را تعیین می‌کند.

### افزودن WeatherPoint

1. Django admin → WeatherPoint (`is_active`، `ingest_enabled=true`؛ elevation از DEM نه GPX `<ele>`؛ `fixture_managed` را دستی true نکنید).
2. برای نمایش عمومی و SEO، خود نقطه را فعال و `seo_indexable=true` کنید؛ تمام
   نقاط فعال و عمومی fixture باید این flag را داشته باشند. نقطهٔ متصل به Route
   فعال بدون این flag فقط برای سازگاری ingest/search پشتیبانی می‌شود و خطای
   validation است.

### افزودن و publish مسیر

1. Route را با Point فعال بسازید (`is_active=true`).
2. RoutePointهای مرتب با WeatherPoint و `cumulative_minutes` کامل وارد کنید.
3. پس از ذخیره، سرویس مشترک `normalize_and_publish_route` ترتیب، origin/target، segment، axis، progress را همگام می‌کند؛ timing ناقص → `pending`.
4. Search بعد از commit بدون restart به‌روز می‌شود.
5. Ingest بعدی نقاط فعال واجد شرایط را می‌گیرد؛ فوری بدون restart:

```bash
docker compose -f infra/compose/compose.yaml exec api \
  python manage.py ingest_open_meteo --slugs your_point_slug
```

### Import غیرتخریبی و prune

- `seed_catalog` / `seed_tochal_catalog` بدون `--prune` هیچ ردیف operator-managed را حذف یا overwrite نمی‌کند.
- برخورد slug با ردیف `fixture_managed=false` گزارش می‌شود و skip می‌شود مگر `--force-adopt`.
- `--prune` فقط ردیف‌های `fixture_managed` غایب از JSON را حذف می‌کند؛ اگر هنوز به ردیف دستی ارجاع داشته باشند، skip + گزارش می‌شوند.

Startup زنده catalog را در هر restart بازنویسی نمی‌کند؛ فقط اگر catalog زنده خالی باشد و `HAWATCH_BOOTSTRAP_LIVE_CATALOG_IF_EMPTY=true` باشد bootstrap می‌کند.

## stack

- frontend: React + TypeScript + Vite + pnpm workspace
- backend: Django 5.2 LTS + DRF + Python 3.14 + uv
- database: PostgreSQL 16 + PostGIS 3.5
- Redis: کش مشترک هفته، فعال به‌صورت پیش‌فرض با سقف ۱۲۸MB و LRU
- Kafka و data lake: خارج از این milestone
- Observability اختیاری: OpenSearch + Dashboards، Vector، Prometheus و Grafana با profile `observability`؛ جزئیات در `docs/observability.md`

## ساختار repository

```text
design/       تصاویر، tokenها، سیستم طراحی و مشخصات صفحه‌ها
docs/         brief، flow، رفتار صفحه، API، معماری، ADR و QA
apps/web      frontend
apps/api      Django API
infra/        Compose و یادداشت Kubernetes آینده
scripts/      ابزارهای کمکی
AGENTS.md     قوانین ثابت همکاری روی محصول
```
