# محیط Stage هواچ

برنچ `stage` نسخهٔ پیش‌نمایش هواچ را روی پورت `5050` اجرا می‌کند. اجرای بدون آرگومان `deploy-hawatch` همیشه checkout برنچ `main` را روی ورودی اصلی به‌روز می‌کند و سپس مقدار `HAWATCH_STAGE_ENABLED` را از فایل تنظیمات همان سرور می‌خواند. با مقدار `1`، برنچ `stage` هم build و deploy می‌شود؛ با مقدار `0` یا نبود فایل تنظیمات، فقط main اجرا می‌شود و منابع کانتینری stage پاک می‌شوند.

## سرویس‌ها و داده

| محیط | checkout | Compose project | سرویس‌ها | ورودی |
|---|---|---|---|---|
| Production | `/root/hawatch`، برنچ `main` | Compose اصلی | سرویس‌های production | پورت معمول سایت، پیش‌فرض `80` |
| Stage | `/root/hawatch-stage`، برنچ `stage` | `hawatch-stage` | `stage-api`, `stage-web`, `stage-gateway` | `0.0.0.0:5050` |

سه سرویس stage اجزای مستقل اپ هستند: API به داده وصل می‌شود، web فایل‌های
frontend را سرو می‌کند، و gateway هر دو را پشت یک ورودی `:5050` به‌هم وصل
می‌کند. Stage دیتابیس، scheduler یا maintenance جداگانه‌ای بالا نمی‌آورد.

Stage از دیتابیس واقعی production استفاده می‌کند: API stage فایل `/root/hawatch/.env` را می‌خواند و به همان network دیتابیس وصل می‌شود. داده‌ها کپی یا ناشناس‌سازی نمی‌شوند؛ هر قابلیتی که در API stage داده‌ای را تغییر دهد، روی دیتابیس مشترک اثر می‌گذارد. تنظیم API صریحاً demo data و bootstrap را خاموش می‌کند و سرویس stage migration، seed یا ingest اجرا نمی‌کند؛ پیش‌بینی‌های زنده را از همان دیتابیس production می‌خواند. خاموش‌کردن stage، دیتابیس اصلی و network production را نگه می‌دارد.

## آماده‌سازی روی سرور

روی سیستم توسعه، برنچ renameشده را بگیرید و فرمان را نصب کنید:

```bash
git fetch origin
git switch stage
git pull --ff-only origin stage
install -Dm755 scripts/deploy-hawatch "$HOME/.local/bin/deploy-hawatch"
install -Dm755 scripts/deploy-stage-hawatch "$HOME/.local/bin/deploy-stage-hawatch"
```

برای هر سرور، نمونه را به‌عنوان فایل تنظیمات stage کپی کنید و IP، دامنه، مسیر فایل env و نام network دیتابیس را با همان سرور هماهنگ کنید. این فایل فقط تنظیمات اتصال stage دارد و credential دیتابیس را از env اصلی می‌خواند:

```bash
scp infra/compose/stage.env.example hawatch:/root/hawatch-stage.env
ssh hawatch 'chmod 600 /root/hawatch-stage.env'
```

نمونه به‌صورت پیش‌فرض فعال است و پورت `5050` را روی همهٔ interfaceهای سرور منتشر می‌کند. روی سروری که نام SSH آن `hawatch` نیست، target و مشخصات همان سرور را هنگام deploy بدهید. فرمان را از checkout محلی اجرا کنید؛ برای مسیر غیرمعمول checkout از `HAWATCH_LOCAL_DIR` استفاده کنید. مسیرهای غیرپیش‌فرض سرور هم با `HAWATCH_SERVER_DIR`, `HAWATCH_STAGE_DIR`, `HAWATCH_STAGE_ENV_FILE`, `HAWATCH_SERVER_IP` و `HAWATCH_PUBLIC_HOST` قابل تنظیم‌اند:

```bash
HAWATCH_SSH_HOST=root@SERVER_IP \
HAWATCH_SERVER_IP=SERVER_IP \
HAWATCH_PUBLIC_HOST=SERVER_DOMAIN_OR_IP \
deploy-hawatch
```

اگر پروژه روی آن سرور در مسیر دیگری است یا network نام دیگری دارد، همان مسیر را
در `HAWATCH_SERVER_DIR` و نام دقیق network دیتابیس را در
`HAWATCH_PRODUCTION_NETWORK` بگذارید. مقدار `HAWATCH_PRODUCTION_ENV_FILE` هم باید
به `.env` واقعی همان checkout production اشاره کند.

سپس از checkout برنچ `stage`:

```bash
deploy-hawatch
```

برای deploy فقط stage، بدون pull، build یا restart کردن production، از فرمان
مستقل زیر استفاده کنید:

```bash
deploy-stage-hawatch
```

این فرمان فقط commitهای branch `stage` را push می‌کند و checkout stage را روی
همان سرور build و healthcheck می‌کند. اگر stage خاموش باشد، عمداً متوقف می‌شود
تا خاموش‌بودن stage با یک فرمان ناخواسته دور زده نشود.

Wrapper از branch فعلی `main`، commitهای main را push می‌کند. branch `stage` فقط وقتی push می‌شود که در فایل سرور فعال باشد یا فرمان `stage-on` اجرا شود؛ بنابراین وقتی stage خاموش است حتی branch آن هم deploy/push نمی‌شود. تغییرات uncommitted هیچ‌وقت stage یا commit نمی‌شوند. سرور همیشه `origin/main` را deploy می‌کند و فقط وقتی stage فعال باشد `origin/stage` را build/deploy می‌کند. push به‌تنهایی deploy ایجاد نمی‌کند. قبل از حذف preview قدیمی، imageهای جدید stage ساخته می‌شوند؛ شکست build، preview قبلی را نگه می‌دارد. پس از بالا آمدن سرویس‌ها، healthcheck هر سه container و درخواست‌های gateway به API readiness، Home، catalog زنده و forecast واقعی Open-Meteo بررسی می‌شوند. `deploy-hawatch` فقط وقتی موفق اعلام می‌شود که این بررسی‌ها بگذرند.

اولین اجرا checkout مستقل `/root/hawatch-stage` را می‌سازد. اگر checkout قدیمی `/root/hawatch-new-design` وجود داشته باشد، در صورت clean بودن به مسیر جدید و برنچ `stage` منتقل می‌شود؛ پروژهٔ Docker قدیمی `hawatch-new-design` پیش از اشغال پورت ۵۰۵۰ جمع می‌شود.

## روشن و خاموش‌کردن Stage

برای خاموش‌کردن فوری و پایدار stage:

```bash
deploy-hawatch stage-off
```

این فرمان روی سرور `HAWATCH_STAGE_ENABLED=0` می‌گذارد و containerها، network،
volume لاگ و imageهای محلی هر دو نام پروژهٔ stage را حذف می‌کند. فایل تنظیمات و
checkout کد باقی می‌مانند تا روشن‌کردن دوباره ساده باشد. Production دست‌نخورده
می‌ماند. پس از آن هر اجرای بدون آرگومان `deploy-hawatch` فقط main را deploy
می‌کند و پاک‌سازی stage را هم تکرار می‌کند.

برای فعال‌کردن دوباره و deploy هم‌زمان main و stage:

```bash
deploy-hawatch stage-on
```

این فرمان مقدار را روی `1` می‌گذارد، main را deploy می‌کند و stage را هم روی
`5050` بالا می‌آورد. برای تغییر دستی نیز مقدار `HAWATCH_STAGE_ENABLED` در فایل
تنظیمات همان سرور کافی است؛ هر سرور مستقل از بقیه فعال/غیرفعال می‌شود.

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

برای سرور دیگری، این مقادیر را در فایل تنظیمات همان سرور بنویسید؛ IP سرور در
Compose یا کد برنامه hardcode نشده است. نام SSH میزبان و host/IP را هم به wrapper
می‌دهید، پس همان فرمان روی سرور انتخاب‌شده عمل می‌کند.

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
