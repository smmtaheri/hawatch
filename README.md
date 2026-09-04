# هواچ (Hawatch)

هواچ محصولی فارسی و تصمیم‌محور برای دیدن هوای نقطه و برنامه‌ریزی مسیر است. کاربر به‌جای دیدن یک دمای منفرد، شرایط نقطه و تغییرات آب‌وهوا را در طول مسیر می‌بیند تا بتواند زمان حرکت، مسیر و امکان ادامه‌دادن یا برگشتن را آگاهانه‌تر انتخاب کند.

## وضعیت این repository

این repository شامل design handoff، مستندات محصول، و اولین نسخهٔ محلی اجرایی است:

- frontend: `apps/web` — React + TypeScript + Vite
- backend: `apps/api` — Django + Django REST Framework + PostGIS
- local/pilot stack: `infra/compose/compose.yaml` — web production، api، postgres، ingest one-shot، scheduler شش‌ساعته و maintenance سبک
- gateway: Nginx روی port قابل‌تنظیم `NGINX_PUBLISH_PORT` (پیش‌فرض `80`) برای health check و proxy وب/API

مسیر `/login?returnTo=…` و لایهٔ responsive ورود در دسترس است: ورود عادی روی همان صفحه به‌صورت overlay باز می‌شود (mobile تمام‌صفحه و desktop dialog). احراز هویت واقعی، ارسال OTP و API ورود هنوز پیاده نشده‌اند و UI این وضعیت را صریح نشان می‌دهد.

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

## استقرار سریع روی سرور

برای نصب پیش‌نیازها، clone، ساخت امن `.env`، اجرای Compose سبک و health check از اسکریپت زیر استفاده کنید:

```bash
apt-get update && apt-get install -y ca-certificates curl
curl -fsSL https://raw.githubusercontent.com/smmtaheri/hawatch/main/scripts/deploy.sh -o /root/hawatch-deploy.sh
chmod 700 /root/hawatch-deploy.sh
PUBLIC_HOST=SERVER_IP /root/hawatch-deploy.sh
```

راهنمای کامل، گزینه‌های اسکریپت و دستور توقف در `docs/deployment.md` است. این اسکریپت به‌صورت پیش‌فرض Redis و observability سنگین را اجرا نمی‌کند.

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

راهنمای کامل و مرجع workflow افزودن نقطه و مسیر در
[`docs/catalog-onboarding.md`](docs/catalog-onboarding.md) است. برای نقطه جدید
ابتدا همان سند را بخوانید؛ خلاصهٔ سریع زیر برای دسترسی سریع به commandهای اصلی
است.

برای افزودن نقطه بعدی، یک catalog JSON هم‌شکل `apps/api/fixtures/catalog/tochal_v1.json` در `apps/api/fixtures/catalog/` قرار دهید و ابتدا validator read-only را اجرا کنید. نقاطی که route پیادهٔ معتبر ندارند هم مجازند؛ در این حالت از [`docs/templates/point-only-catalog-template.json`](docs/templates/point-only-catalog-template.json) استفاده کنید و `routes` را `{}` نگه دارید:

```bash
python3 scripts/validate_open_meteo_catalog.py --catalog apps/api/fixtures/catalog/my_point_v1.json
```

سپس همان فایل را import کنید (غیرتخریبی؛ prune فقط با `--prune`):

```bash
docker compose -f infra/compose/compose.yaml exec api \
  python manage.py seed_catalog --file catalog/my_point_v1.json
docker compose -f infra/compose/compose.yaml exec api \
  python manage.py ingest_open_meteo
```

برای جلوگیری از اجرای دستی و اشتباه مراحل local/server، می‌توانید catalog را
مستقیماً از local با wrapper بررسی و publish کنید:

```bash
python3 scripts/publish_catalog.py \
  --catalog /tmp/my_point_v1.json \
  --host root@SERVER_IP                 # check-only؛ بدون write

python3 scripts/publish_catalog.py \
  --catalog /tmp/my_point_v1.json \
  --host root@SERVER_IP \
  --apply                                # import + ingest + preflight
```

این wrapper فایل JSON یا GPX را به سرور کپی نمی‌کند؛ catalog را فقط از stdin
به کانتینر API می‌فرستد. `--apply` برای routeهای بدون timing متوقف می‌شود تا
اطلاعات arrival به‌صورت ناخواسته ناقص منتشر نشود.

برای اعمال نسخهٔ جدید همهٔ کاتالوگ‌ها روی دیتابیس موجود، bootstrap ضمنی کافی
نیست. ابتدا backup بگیرید، سپس برنامهٔ تغییر را بدون write ببینید و بعد از
بازبینی صریحاً اعمال کنید:

```bash
docker compose --env-file .env -f infra/compose/compose.yaml exec -T api \
  python manage.py sync_catalog --dry-run

docker compose --env-file .env -f infra/compose/compose.yaml exec -T api \
  python manage.py sync_catalog --apply
```

این command فقط ردیف‌های `fixture_managed=true` را برای stale cleanup هدف می‌گیرد؛
رکوردهای دستی حفظ می‌شوند و conflict مبهم باعث توقف atomic sync می‌شود.

ترتیب release روی سرور: ابتدا backup دیتابیس، سپس `migrate`، اجرای
`sync_catalog --dry-run` و بازبینی گزارش، اجرای `sync_catalog --apply`، بعد
`validate_catalog --all --database --strict` و در پایان smoke test با curl و
مرورگر برای Home، Point، Route، search، canonical، query/noindex، robots، sitemap
و 404. این مراحل باید توسط اپراتور اجرا شوند و در این تغییر روی production اجرا
نشده‌اند.

جزئیات قرارداد، تفاوت elevation catalog و DEM، و smoke test در `docs/catalog-and-weather-validation.md` است.

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
- Redis: optional، profile `cache`؛ در این milestone لازم نیست
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
