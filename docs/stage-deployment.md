# محیط Stage هواچ

برنچ `stage` نسخهٔ پیش‌نمایش هواچ را روی پورت `5050` اجرا می‌کند. `deploy-hawatch` ابتدا checkout برنچ `main` را روی سرویس production به‌روز می‌کند؛ سپس مقدار `HAWATCH_STAGE_ENABLED` را از فایل تنظیمات همان سرور می‌خواند. با مقدار `1`، stage هم deploy می‌شود؛ با مقدار `0` یا نبود فایل تنظیمات، فقط main فعال می‌ماند و منابع کانتینری stage پاک می‌شوند.

## سرویس‌ها و داده

| محیط | checkout | Compose project | سرویس‌ها | ورودی |
|---|---|---|---|---|
| Production | `/root/hawatch`، برنچ `main` | Compose اصلی | سرویس‌های production | پورت معمول سایت، پیش‌فرض `80` |
| Stage | `/root/hawatch-stage`، برنچ `stage` | `hawatch-stage` | `stage-api`, `stage-web`, `stage-gateway` | `0.0.0.0:5050` |

Stage از دیتابیس واقعی production استفاده می‌کند: API stage فایل `/root/hawatch/.env` را می‌خواند و به همان network دیتابیس وصل می‌شود. داده‌ها کپی یا ناشناس‌سازی نمی‌شوند؛ هر قابلیتی که در API stage داده‌ای را تغییر دهد، روی دیتابیس مشترک اثر می‌گذارد. سرویس stage migration، seed، bootstrap یا ingest اجرا نمی‌کند و database، scheduler و maintenance تازه نمی‌سازد. خاموش‌کردن stage، دیتابیس اصلی و شبکهٔ production را نگه می‌دارد.

## آماده‌سازی روی سرور

روی سیستم توسعه، برنچ renameشده را بگیرید و فرمان را نصب کنید:

```bash
git fetch origin
git switch stage
git pull --ff-only origin stage
install -Dm755 scripts/deploy-hawatch "$HOME/.local/bin/deploy-hawatch"
```

برای هر سرور، نمونه را به‌عنوان فایل تنظیمات stage کپی کنید و IP، دامنه، مسیر فایل env و نام network دیتابیس را با همان سرور هماهنگ کنید:

```bash
scp infra/compose/stage.env.example hawatch:/root/hawatch-stage.env
ssh hawatch 'chmod 600 /root/hawatch-stage.env'
```

نمونه به‌صورت پیش‌فرض فعال است و پورت `5050` را روی همهٔ interfaceهای سرور منتشر می‌کند. روی سروری که نام SSH آن `hawatch` نیست، `HAWATCH_SSH_HOST` را هنگام اجرای wrapper مشخص کنید. مسیرهای غیرپیش‌فرض با `HAWATCH_SERVER_DIR`, `HAWATCH_STAGE_DIR`, `HAWATCH_STAGE_ENV_FILE`, `HAWATCH_SERVER_IP` و `HAWATCH_PUBLIC_HOST` قابل تنظیم‌اند.

سپس از checkout برنچ `stage`:

```bash
deploy-hawatch
```

Wrapper از `main`، main را push می‌کند و از هر دو branch محلی، ref برنچ `stage` را هم push می‌کند تا نسخهٔ stage روی سرور به‌روز باشد. سرور main و در صورت فعال‌بودن stage آن برنچ را deploy می‌کند. push به‌تنهایی deploy ایجاد نمی‌کند. خروجی موفق deploy پس از healthcheck پورت ۸۰ و در صورت فعال‌بودن stage، پورت ۵۰۵۰ چاپ می‌شود. شکست build stage سرویس‌های stage قبلی را نگه می‌دارد و به main دست نمی‌زند.

اولین اجرا checkout مستقل `/root/hawatch-stage` را می‌سازد. اگر checkout قدیمی `/root/hawatch-new-design` وجود داشته باشد، در صورت clean بودن به مسیر جدید و برنچ `stage` منتقل می‌شود؛ پروژهٔ Docker قدیمی `hawatch-new-design` پیش از اشغال پورت ۵۰۵۰ جمع می‌شود.

## روشن و خاموش‌کردن Stage

برای خاموش‌کردن فوری stage، اسکریپت `stage-down.sh` مقدار فعال‌بودن را در فایل تنظیمات روی صفر می‌گذارد و کانتینرها، network و volume لاگ stage و imageهای محلی stage را پاک می‌کند:

```bash
ssh hawatch 'HAWATCH_STAGE_ENV_FILE=/root/hawatch-stage.env bash /root/hawatch-stage/scripts/stage-down.sh'
```

فایل تنظیمات و checkout کد باقی می‌مانند تا راه‌اندازی دوباره ساده باشد. پس از آن هر اجرای `deploy-hawatch` فقط main را deploy می‌کند و پاک‌سازی stage را هم تکرار می‌کند.

برای فعال‌کردن دوباره:

```bash
ssh hawatch 'sed -i "s/^HAWATCH_STAGE_ENABLED=.*/HAWATCH_STAGE_ENABLED=1/" /root/hawatch-stage.env'
deploy-hawatch
```

اگر کلید در فایل وجود ندارد، خط `HAWATCH_STAGE_ENABLED=1` را به فایل اضافه کنید. تغییر مقدار فعال‌بودن در هر سرور مستقل است.

## متغیرهای فایل Stage

فایل `/root/hawatch-stage.env` secret دیتابیس ندارد؛ تنظیمات اتصال از `.env` فعلی production خوانده می‌شوند.

| متغیر | نقش |
|---|---|
| `HAWATCH_STAGE_ENABLED` | `1` برای deploy stage و `0` برای خاموش‌ماندن و پاک‌کردن منابع آن |
| `HAWATCH_PRODUCTION_ENV_FILE` | مسیر env دارای credentials دیتابیس production |
| `HAWATCH_PRODUCTION_NETWORK` | network Compose اصلی که دیتابیس روی آن است |
| `HAWATCH_PRODUCTION_DB_HOST` | alias دیتابیس روی network بالا، معمولاً `postgres` |
| `HAWATCH_STAGE_ALLOWED_HOSTS` | IP یا دامنه‌ای که با آن stage باز می‌شود |
| `HAWATCH_STAGE_ORIGIN` | آدرس کامل stage، شامل پورت ۵۰۵۰ |
| `HAWATCH_STAGE_BIND_IP` | پیش‌فرض `0.0.0.0`؛ فقط برای reverse proxy محلی آن را `127.0.0.1` کنید |
| `HAWATCH_STAGE_PORT` | باید `5050` باشد |
| `HAWATCH_PUBLIC_ORIGIN` | canonical دامنهٔ اصلی، پیش‌فرض `https://hawatch.ir` |

برای نمونه، اگر IP یا سرویس دیتابیس سرور دیگری دارید، همین مقادیر را در فایل همان سرور تنظیم کنید؛ لازم نیست در Compose یا کد برنامه IP ثابتی باشد. نام SSH میزبان و host/IP محلی را نیز با `HAWATCH_SSH_HOST` و `HAWATCH_SERVER_IP` به wrapper بدهید.

## HTTPS اختیاری

نمونهٔ `infra/compose/compose.stage-tls.yaml` یک listener مستقل روی پورت پیش‌فرض `5051` اضافه می‌کند و به listenerهای production روی ۸۰/۴۴۳ دست نمی‌زند. نام دامنهٔ stage باید به سرور اشاره کند و certificate معتبر با `fullchain.pem` و `privkey.pem` در مسیر certificate تنظیم‌شده موجود باشد. در `/root/hawatch-stage.env` مقدارهای زیر را تنظیم کنید:

```dotenv
HAWATCH_STAGE_ALLOWED_HOSTS=SERVER_IP,stage.example.test
HAWATCH_STAGE_ORIGIN=https://stage.example.test:5051
HAWATCH_STAGE_TLS_PORT=5051
HAWATCH_STAGE_CERT_DIR=/root/hawatch-stage-certs
```

اجرای TLS اختیاری به‌صورت دستی:

```bash
cd /root/hawatch-stage
docker compose --project-name hawatch-stage --env-file /root/hawatch-stage.env \
  -f infra/compose/compose.stage.yaml -f infra/compose/compose.stage-tls.yaml up -d
```

خاموش‌کردن stage با `stage-down.sh` سرویس TLS را نیز پاک می‌کند.

## بررسی

```bash
curl -i http://SERVER_IP:5050/healthz
curl -I http://SERVER_IP:5050/
ssh hawatch 'docker compose --project-name hawatch-stage --env-file /root/hawatch-stage.env -f /root/hawatch-stage/infra/compose/compose.stage.yaml ps'
```

همهٔ صفحه‌ها و APIهای stage noindex هستند؛ robots و sitemap نیز برای indexing عمومی بسته‌اند. سیاست SEO و سرویس production از checkout اصلی و تنظیمات خودش می‌آیند.
