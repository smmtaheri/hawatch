# استقرار سریع Hawatch روی سرور

این مسیر برای pilot سبک است: PostgreSQL/PostGIS، API، frontend production، Nginx gateway و maintenance بالا می‌آیند. Redis و observability سنگین (`OpenSearch`، Dashboards، Vector، Prometheus و Grafana) به‌صورت پیش‌فرض اجرا نمی‌شوند.

اسکریپت `scripts/deploy.sh` روی Linux این کارها را انجام می‌دهد:

- نصب `ca-certificates`، `curl`، `git` و `openssl` در توزیع‌های Debian/Ubuntu، RHEL/Fedora یا Alpine؛
- نصب Docker Engine و Compose v2 plugin در صورت نبودن Docker؛
- clone یا fast-forward کردن فقط checkout مورد انتظار Hawatch؛
- ساخت `.env` با permission `600` و secret تصادفی فقط وقتی `.env` وجود ندارد؛
- تنظیم حالت production/live، آدرس browser API و پورت‌ها؛
- اجرای `docker compose config`، build/up، health check، scheduler داخلی ingest و یک ingest اولیهٔ live؛
- همگام‌سازی atomic همهٔ catalogهای versioned با دیتابیس موجود پیش از smoke check؛
- توقف کامل containerهای همان Compose project با `down --remove-orphans` و سپس بالا آوردن همهٔ سرویس‌های انتخاب‌شده با `--force-recreate`؛ volumeهای نام‌دار، به‌ویژه دیتابیس، حفظ می‌شوند؛
- نمایش status و URLهای قابل تست.

اسکریپت root می‌خواهد و اگر checkout موجود dirty باشد، remote ناشناخته باشد، یا `.env` موجود placeholder داشته باشد متوقف می‌شود. `.env` موجود را جایگزین نمی‌کند و secretهای موجود را overwrite نمی‌کند؛ فقط تنظیمات runtime لازم برای deploy را به‌روزرسانی می‌کند. هیچ فایل یا volumeای را حذف نمی‌کند و firewall را تغییر نمی‌دهد. قبل از اجرای ingest، migration و seed کاتالوگ طبق entrypoint فعلی API اجرا می‌شوند.

## اجرای مستقیم روی یک سرور تازه

حداقل پیش‌نیاز برای گرفتن خود اسکریپت، دسترسی root و `curl` است. روی Debian/Ubuntu:

```bash
apt-get update && apt-get install -y ca-certificates curl
curl -fsSL https://raw.githubusercontent.com/smmtaheri/hawatch/main/scripts/deploy.sh -o /root/hawatch-deploy.sh
chmod 700 /root/hawatch-deploy.sh
PUBLIC_HOST=SERVER_IP /root/hawatch-deploy.sh
```

`SERVER_IP` را با IP یا دامنهٔ واقعی، بدون `http://`، جایگزین کنید. اگر repository خصوصی است یا سرور به HTTPS GitHub دسترسی احراز‌شده دارد، URL را صریح بدهید:

```bash
HAWATCH_REPO_URL='git@github.com:smmtaheri/hawatch.git' \
PUBLIC_HOST=SERVER_IP /root/hawatch-deploy.sh
```

در این حالت کلید SSH کاربر root باید از قبل برای GitHub آماده باشد. مسیر پیش‌فرض checkout `/root/hawatch` است؛ می‌توان آن را تغییر داد:

```bash
HAWATCH_DIR=/srv/hawatch PUBLIC_HOST=SERVER_IP /root/hawatch-deploy.sh
```

## کنترل ingest اولیه و پورت‌ها

برای بالا آوردن سرویس‌ها بدون تماس اولیه با Open-Meteo:

```bash
RUN_INITIAL_INGEST=0 PUBLIC_HOST=SERVER_IP /root/hawatch-deploy.sh
```

پورت‌های پیش‌فرض host عبارت‌اند از gateway=`80`، frontend مستقیم=`5173` و API=`8000`. frontend به‌صورت پیش‌فرض API هم‌مبدأ `/api/v1` را صدا می‌زند؛ gateway فعلی HTTP است و HTTPS را terminate نمی‌کند. برای HTTPS باید یک TLS proxy یا CDN بیرونی جلوی gateway قرار گیرد؛ در آن حالت همچنان API هم‌مبدأ `/api/v1` را استفاده کنید. اگر API جداگانه‌ای دارید، می‌توانید آن را صریح تنظیم کنید:

```bash
VITE_API_BASE_URL='https://api.example.com/api/v1' \
PUBLIC_HOST=SERVER_IP /root/hawatch-deploy.sh
```

اسکریپت firewall یا cloud security group را باز نمی‌کند؛ در صورت نیاز فقط پورت‌های انتخابی را در firewall سرور/provider مجاز کنید. برای مصرف کمتر معمولاً فقط gateway را عمومی کنید و API/frontend مستقیم را در شبکهٔ خصوصی یا با rule محدود نگه دارید.

## بررسی و توقف

```bash
cd /root/hawatch
docker compose --env-file .env -f infra/compose/compose.yaml ps
curl -fsS http://127.0.0.1/healthz
curl -fsS http://127.0.0.1:8000/api/v1/health/ready/
curl -fsS -H "Authorization: Bearer $(awk -F= '$1=="HAWATCH_METRICS_TOKEN" {sub(/^[^=]*=/, ""); print; exit}' .env)" \
  http://127.0.0.1:8000/api/v1/health/status/
docker compose --env-file .env -f infra/compose/compose.yaml logs --tail=100 api ingest
```

نقاط شاخص Home در دیتابیس تنظیم می‌شوند و `sync_catalog` آن‌ها را در deployهای
بعدی بازنشانی نمی‌کند. برای ارتقای یک دیتابیس قدیمی که فقط توچال را در Home
دارد، یک‌بار از روی local یا با SSH این انتخاب را اعمال کنید:

```bash
docker compose --env-file .env -f infra/compose/compose.yaml exec -T api \
  python manage.py set_popular_points \
  --slugs tochal,damavand,alamkuh,tar-lake
```

### ورود به گزارش analytics

Admin از مسیر `/admin/` روی gateway به Django وصل می‌شود و فقط superuserهای
فعال اجازهٔ مشاهدهٔ گزارش analytics را دارند. برای ساخت superuser روی سرور:

```bash
cd /root/hawatch
docker compose --env-file .env -f infra/compose/compose.yaml exec api \
  python manage.py createsuperuser
```

این command کاربر را ایجاد می‌کند و `is_staff` و `is_superuser` را برای او
تنظیم می‌کند؛ کاربرهای موجود حذف یا بازنشانی نمی‌شوند. گزارش از مسیر زیر
قابل مشاهده است:

`https://<PUBLIC_HOST>/admin/analytics/pageviewevent/overview/`

اگر دامنهٔ دیگری استفاده می‌شود، آن را در `DJANGO_ALLOWED_HOSTS` و
`DJANGO_CSRF_TRUSTED_ORIGINS` (با scheme کامل `https://`) در `.env` قرار دهید و
دوباره deploy کنید؛ در غیر این صورت login پشت HTTPS با خطای CSRF رد می‌شود.

توقف بدون حذف volumeها:

```bash
cd /root/hawatch
docker compose --env-file .env -f infra/compose/compose.yaml down
```

سرویس `ingest-scheduler` اجرای دوره‌ای را بدون cron یا systemd خارجی انجام می‌دهد: هر روز در ساعت‌های ۰۰:۰۰، ۰۶:۰۰، ۱۲:۰۰ و ۱۸:۰۰ به وقت تهران. اجرای دستی one-shot همچنان ممکن است:

```bash
cd /root/hawatch
docker compose --env-file .env -f infra/compose/compose.yaml run --rm ingest
```

لاگ زمان‌بندی و نتیجهٔ هر اجرا:

```bash
docker compose --env-file .env -f infra/compose/compose.yaml logs --tail=100 ingest-scheduler
```

فعال‌سازی observability فقط با تصمیم جداگانه و روی سرور بزرگ‌تر انجام شود:

```bash
ENABLE_OBSERVABILITY=1 PUBLIC_HOST=SERVER_IP /root/hawatch-deploy.sh
```

این profile برای pilot سبک لازم نیست.
