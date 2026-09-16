# سناریوی پشتیبان‌گیری و بازیابی هواچ

این سند runbook عملیاتی برای سه وضعیت است: گرفتن پشتیبان کامل، به‌روزرسانی
پشتیبان‌ها، و بازیابی روی یک سرور جدید وقتی دسترسی به سرور فعلی از بین رفته
است. هدف این سند این است که سرویس با imageهای از قبل ذخیره‌شده و بدون وابستگی
به GitHub، Docker Hub یا build آنلاین دوباره بالا بیاید.

این راهنما هیچ commandی را خودکار اجرا نمی‌کند. مسیرهای نمونه را با مسیر واقعی
لپ‌تاپ و SSH alias خود عوض کنید. در نمونه‌های فعلی `hawatch` همان SSH alias سرور
است و root پروژه روی سرور `/root/hawatch` است.

## چه چیزهایی باید حفظ شوند

دیتابیس runtime منبع حقیقت هواچ است و باید با `pg_dump` در قالب custom ذخیره
شود. در snapshot فعلی، PostgreSQL 16/PostGIS 3، نقاط و مسیرها، forecastها،
حساب‌ها، تنظیمات دسترسی، proxyهای هواشناسی رمزگذاری‌شده، sessionها و آمار داخل
همین دیتابیس هستند.

فایل `.env` کنار dump ضروری است. مقدارهای زیر را بدون تغییر نگه دارید:

- `DJANGO_SECRET_KEY`؛ برای session و امضای Django؛
- `POSTGRES_DB`، `POSTGRES_USER` و `POSTGRES_PASSWORD`؛ برای اتصال و ساخت DB؛
- `WEATHER_PROXY_ENCRYPTION_KEY`؛ بدون آن URLهای proxy ذخیره‌شده در DB قابل
  خواندن نیستند؛
- `DEMO_AUTH_ALLOWED_PHONE` و `DEMO_AUTH_FIXED_OTP`؛ تا login آزمایشی همان
  سیاست قبلی را داشته باشد؛
- `HAWATCH_METRICS_TOKEN` و تنظیمات `OPEN_METEO_*`؛
- `DJANGO_ALLOWED_HOSTS`، `DJANGO_CSRF_TRUSTED_ORIGINS` و
  `HAWATCH_PUBLIC_ORIGIN` در صورت تغییر دامنه یا مبدأ.

این runbook encryption فایل backup را اجباری نمی‌کند. اگر فعلاً encryption
نمی‌خواهید، کل پوشهٔ backup را با permission `700` و فایل‌های داخل آن را با
permission `600` روی دیسک قابل‌اعتماد نگه دارید و از آن در دو محل جدا نسخه داشته
باشید. آن را در Git، پیام‌رسان یا فضای عمومی قرار ندهید. مقدارهای secret را در
log یا خروجی command چاپ نکنید.

فایل‌ها و stateهای دیگر:

| مورد | لازم برای restore؟ | روش نگهداری |
| --- | --- | --- |
| source و تاریخ commit | بله | `git bundle` یا archive از checkout local |
| imageهای نهایی API/web/worker/PostGIS/Nginx | بله برای restore بدون اینترنت | `docker save` و archive محلی |
| `tracks/` و GPX | برای runtime نه؛ برای ادامهٔ curation بله | archive جدا؛ هرگز داخل image یا DB نیست |
| `hawatch_staticfiles` | خیر | با `collectstatic` بازسازی می‌شود |
| `hawatch_logs` | خیر برای سرویس؛ اختیاری برای audit | archive اختیاری |
| TLS، DNS و CDN | روی این سرور نیست | export/screenshot و دسترسی پنل CDN/دامنه |

در حالت فعلی observability اختیاری اجرا نمی‌شود؛ اگر بعداً profileهای
OpenSearch/Prometheus/Grafana فعال شدند، volumeهای آن‌ها (`hawatch_opensearch`,
`hawatch_vector_data`, `hawatch_prometheus`, `hawatch_grafana`) نیز باید جداگانه
به فهرست backup اضافه شوند.

## سناریو ۱: پشتیبان‌گیری کامل اولیه

این سناریو را یک‌بار همین حالا و دوباره پیش از هر migration، تغییر بزرگ، جابه‌جایی
proxy یا deploy مهم انجام دهید. dump از PostgreSQL سازگار و بدون downtime است؛
در زمان dump سرویس را خاموش نکنید.

### ۱. ساخت پوشهٔ snapshot روی لپ‌تاپ

```bash
repo=/home/nobitex/Desktop/Tasks/Nobitex/hawatch
backup_root="$repo/backups"
stamp=$(date +%Y%m%d-%H%M%S)
target="$backup_root/$stamp"
mkdir -p "$target"
chmod 700 "$backup_root" "$target"
```

بک‌آپ عمداً داخل فولدر پروژه و در مسیر `backups/` ساخته می‌شود؛ این مسیر در
`.gitignore` است و هیچ dump، env یا imageای نباید وارد Git شود. مسیر `target` را
در تمام commandهای این snapshot ثابت نگه دارید. اگر commandی قطع شد، فایل
`.part` را backup کامل حساب نکنید.

### ۲. کپی env

```bash
scp hawatch:/root/hawatch/.env "$target/server.env"
chmod 600 "$target/server.env"
```

مقدار env را در ترمینال چاپ نکنید. قبل از استفاده بررسی کنید فایل non-empty و
permission آن `600` است.

### ۳. dump منطقی PostgreSQL/PostGIS

قالب `-Fc` برای restore انتخاب شده چون فشرده، قابل بررسی و مستقل از فایل‌های
داخلی volume است:

```bash
ssh hawatch \
  'docker exec hawatch-postgres-1 pg_dump -U hawatch -d hawatch -Fc --no-owner --no-acl' \
  > "$target/hawatch.dump.part"
mv "$target/hawatch.dump.part" "$target/hawatch.dump"
```

اگر نام DB یا role در env تغییر کرده است، به‌جای `hawatch` همان مقدارهای
`POSTGRES_DB` و `POSTGRES_USER` را استفاده کنید. این dump شامل schema، migration
state، catalog، forecast، proxyهای encrypted، حساب‌ها و analytics است؛ password
خام proxy در آن وجود ندارد و به `WEATHER_PROXY_ENCRYPTION_KEY` وابسته است.

### ۴. ذخیرهٔ source و ترک‌های local

در checkout local که commit موردنظر روی آن است:

```bash
git -C "$repo" bundle create "$target/hawatch.git.bundle" --all
git -C "$repo" archive --format=tar.gz --output="$target/hawatch-source.tar.gz" HEAD
tar -C "$repo" -czf "$target/hawatch-tracks.tar.gz" tracks
```

`tracks/` عمداً در Git و imageهای production نیست؛ آن را فقط برای evidence و
ادامهٔ onboarding نگه دارید.

### ۵. ذخیرهٔ imageهای نهایی برای restore بدون اینترنت

این archive برای `up --no-build` است. imageهای نهایی را ذخیره کنید، نه فقط
base imageها؛ در نتیجه restore به Docker Hub و package registry نیاز ندارد:

```bash
ssh hawatch \
  'docker save hawatch-api:latest hawatch-web:latest hawatch-ingest:latest hawatch-ingest-scheduler:latest hawatch-maintenance:latest postgis/postgis:16-3.5 nginx:1.27-alpine | gzip -1' \
  > "$target/hawatch-images.tar.gz.part"
mv "$target/hawatch-images.tar.gz.part" "$target/hawatch-images.tar.gz"
```

اگر بعداً قصد build آفلاین دارید، base imageهای `python:3.14-slim-bookworm` و
`node:22-bookworm-slim` و cacheهای apt/uv/pnpm هم لازم می‌شوند؛ صرفاً داشتن
base image build آفلاین را تضمین نمی‌کند. برای بازیابی سریع، imageهای نهایی
اولویت دارند.

### ۶. صحت‌سنجی و فهرست فایل‌ها

```bash
pg_restore --list "$target/hawatch.dump" >/dev/null
gzip -t "$target/hawatch-images.tar.gz"
sha256sum "$target"/* > "$target/SHA256SUMS"
chmod 600 "$target"/*
```

اگر `pg_restore --list` یا `gzip -t` خطا داد، snapshot ناقص است و باید دوباره
گرفته شود. حداقل دو کپی روی دو دیسک جدا نگه دارید. یک‌بار restore آزمایشی روی
PostGIS هم‌نسخه انجام دهید؛ داشتن فایل بدون تست restore پشتیبان قابل‌اعتماد
محسوب نمی‌شود.

## سناریو ۲: به‌روزرسانی پشتیبان‌ها

به‌روزرسانی باید incremental در سطح snapshot باشد، نه append کردن به dump قبلی.
هر snapshot پوشهٔ تاریخ‌دار مستقل دارد تا خرابی یک فایل، نسخه‌های قبلی را
خراب نکند.

### cadence پیشنهادی

- هر روز: dump جدید DB و کپی `.env`؛
- پیش از هر deploy، migration، `sync_catalog --apply`، تغییر proxy یا تغییر
  سیاست حساب: snapshot فوری؛
- با تغییر کد: `git bundle`/source archive جدید؛
- با تغییر image یا Dockerfile: image archive جدید؛
- حداقل ۷ snapshot روزانهٔ سبک و ۴ snapshot کامل هفتگی/انتشار را نگه دارید.

برای update بهینه، دو نوع snapshot داشته باشید:

1. snapshot روزانهٔ سبک فقط شامل `.env`، dump دیتابیس، `source-commit.txt` و
   checksum باشد؛ این snapshot برای تغییرات forecast و آمار مناسب است و imageها
   را دوباره کپی نمی‌کند.
2. snapshot کامل سناریوی اول پیش از هر deploy، migration، `sync_catalog --apply`،
   تغییر proxy، تغییر سیاست حساب، تغییر Dockerfile یا تغییر dependency گرفته
   شود. این snapshot مرجع source و imageهای قابل restore آفلاین است.

برای snapshot روزانهٔ سبک، این commandها را با timestamp جدید اجرا کنید:

```bash
repo=/home/nobitex/Desktop/Tasks/Nobitex/hawatch
backup_root="$repo/backups"
stamp=$(date +%Y%m%d-%H%M%S)
target="$backup_root/$stamp"
mkdir -p "$target"
chmod 700 "$backup_root" "$target"

scp hawatch:/root/hawatch/.env "$target/server.env"
chmod 600 "$target/server.env"

ssh hawatch \
  'docker exec hawatch-postgres-1 pg_dump -U hawatch -d hawatch -Fc --no-owner --no-acl' \
  > "$target/hawatch.dump.part"
mv "$target/hawatch.dump.part" "$target/hawatch.dump"

git -C "$repo" rev-parse HEAD > "$target/source-commit.txt"
printf 'database-env\n' > "$target/backup-kind.txt"
pg_restore --list "$target/hawatch.dump" >/dev/null
sha256sum "$target"/* > "$target/SHA256SUMS"
chmod 600 "$target"/*
```

در restore، `server.env` و dump را از جدیدترین snapshot معتبر بردارید، اما
source و image را از جدیدترین snapshot کاملِ هم‌دوره بردارید. `source-commit.txt`
باید با نسخهٔ source انتخاب‌شده سازگار باشد؛ snapshot روزانه را با image یا
sourceٔ قدیمی‌تر از آخرین deploy جفت نکنید. dump جدید نباید روی dump قبلی نوشته
شود. پس از انتقال، `pg_restore --list`، `gzip -t` و `sha256sum -c` را اجرا کنید.

برای اطمینان از اینکه snapshot واقعاً جدید است، این metadata را کنار آن ثبت
کنید:

```bash
git -C /home/nobitex/Desktop/Tasks/Nobitex/hawatch rev-parse HEAD \
  > "$target/source-commit.txt"
ssh hawatch 'docker compose --env-file /root/hawatch/.env -f /root/hawatch/infra/compose/compose.yaml ps' \
  > "$target/compose-ps.txt"
```

`compose-ps.txt` فقط برای audit است؛ شامل secret نیست. volume PostgreSQL را از
مسیر `/var/lib/docker/volumes` هنگام روشن بودن DB کپی نکنید؛ برای portability
همیشه `pg_dump` مرجع اصلی باشد. snapshot فیزیکی volume فقط به‌عنوان گزینهٔ
اضافی و با توقف کنترل‌شدهٔ PostgreSQL قابل اتکاست.

## سناریو ۳: قطع ناگهانی دسترسی و restore روی سرور جدید

فرض این سناریو این است که سرور قبلی دیگر قابل SSH نیست و Docker Hub/GitHub نیز
در دسترس نیستند. باید از archiveهای مرحلهٔ اول استفاده کنید.

### A. آماده‌سازی سرور جدید

سرور جدید را با معماری x86_64 و Docker Engine به‌همراه Compose v2 آماده کنید.
اگر اینترنت فقط داخلی است، Docker و Compose را از قبل روی سرور نصب یا package
آن‌ها را در شبکهٔ قابل‌دسترسی آماده کنید. `deploy.sh` برای نصب package و build
به شبکهٔ خارجی وابسته است و در این سناریو نباید مبنای restore باشد.

کد را در مسیر مورد انتظار قرار دهید:

```bash
mkdir -p /root/hawatch
tar -xzf hawatch-source.tar.gz -C /root/hawatch
cp server.env /root/hawatch/.env
chmod 600 /root/hawatch/.env
```

اگر archive منبع از `git bundle` استفاده می‌شود:

```bash
git clone /path/to/hawatch.git.bundle /root/hawatch
```

در `.env` مقدارهای رمزنگاری و secret را تغییر ندهید. فقط در صورت تغییر دامنه
یا origin، `DJANGO_ALLOWED_HOSTS`، `DJANGO_CSRF_TRUSTED_ORIGINS`،
`HAWATCH_PUBLIC_ORIGIN` و پورت‌ها را متناسب با سرور جدید تنظیم کنید.

### B. بارگذاری imageها

```bash
gzip -dc hawatch-images.tar.gz | docker load
```

سپس مطمئن شوید tagهای `hawatch-api:latest`، `hawatch-web:latest`,
`hawatch-maintenance:latest`، `hawatch-ingest-scheduler:latest`،
`hawatch-ingest:latest`، `postgis/postgis:16-3.5` و `nginx:1.27-alpine` وجود
دارند. اگر یکی وجود ندارد، `--no-build` را اجرا نکنید تا archive کامل تهیه شود.

### C. ساخت PostgreSQL خالی و restore قبل از بالا آوردن API

از ریشهٔ `/root/hawatch`:

```bash
docker compose --env-file .env -f infra/compose/compose.yaml \
  up -d --no-build postgres
```

صبر کنید `postgres` healthy شود:

```bash
docker compose --env-file .env -f infra/compose/compose.yaml ps postgres
```

سپس dump را روی DB تازه restore کنید. چون dump با `--no-owner --no-acl` گرفته
شده، role و رمز از `.env` سرور جدید خوانده می‌شوند:

```bash
docker compose --env-file .env -f infra/compose/compose.yaml exec -T postgres \
  pg_restore -U hawatch -d hawatch --clean --if-exists --no-owner --no-acl \
  < hawatch.dump
```

اگر DB/role نام دیگری دارد، همان مقدارهای env را جایگزین کنید. `--clean` فقط
objectهای موجود در مقصد را پاک می‌کند؛ روی سرور تازه معمولاً چیزی برای پاک‌کردن
وجود ندارد. قبل از این مرحله از اجرای API خودداری کنید تا bootstrap یا seed
ناخواسته روی DB خالی اجرا نشود.

### D. بالا آوردن سرویس‌ها با imageهای موجود

```bash
docker compose --env-file .env -f infra/compose/compose.yaml \
  up -d --no-build api web maintenance ingest-scheduler nginx
```

entrypoint API migration و `collectstatic` را اجرا می‌کند. چون DB restore شده و
نقاط فعال دارد، bootstrap خالی نباید catalog را جایگزین کند. سرویس one-shot
`ingest` را در شروع اضطراری اجرا نکنید؛ تا وقتی provider یا proxy قابل‌دسترسی
نیست، اجرای آن فقط شکست forecast جدید ایجاد می‌کند.

### E. smoke check و کنترل عدم تخریب

```bash
curl -fsS http://127.0.0.1/healthz
curl -fsS http://127.0.0.1:8000/api/v1/health/ready/
docker compose --env-file .env -f infra/compose/compose.yaml exec -T api \
  python manage.py validate_catalog --all --database --check-links --strict
docker compose --env-file .env -f infra/compose/compose.yaml exec -T api \
  python manage.py catalog_preflight
```

بعد از تأیید health، DNS/CDN را به origin جدید منتقل کنید. چون TLS فعلی بیرون
از سرور و در CDN terminate می‌شود، certificate و ruleهای CDN از dump DB بازسازی
نمی‌شوند و باید از قبل دسترسی پنل، origin، cache rule، DNS record و recovery
codeهای آن را داشته باشید.

### F. وضعیت forecast در قطع اینترنت بین‌الملل

restore، آخرین snapshotهای ذخیره‌شده را برمی‌گرداند اما دادهٔ جدید بدون دسترسی
به Open‑Meteo یا یک relay قابل‌دسترسی تولید نمی‌شود. proxyهای آمریکا/کانادا نیز
در اینترنت کاملاً داخلی قابل استفاده نیستند. برای تداوم forecast باید پیشاپیش
یکی از این‌ها را آماده کنید:

- relay یا mirror Open‑Meteo داخل شبکهٔ قابل‌دسترسی؛ یا
- provider جایگزین با endpoint داخلی که قرارداد پاسخ آن با ingest هواچ سازگار
  باشد.

`FORECAST_STALE_AFTER_HOURS` را برای پنهان کردن stale بودن داده بالا نبرید؛ این
کار فقط کهنگی forecast را مخفی می‌کند و دادهٔ جدید نمی‌سازد.

## کنترل‌های جلوگیری از اشتباه

- dump را مستقیماً روی نام نهایی ننویسید؛ ابتدا `.part` و بعد rename کنید؛
- هر snapshot باید `pg_restore --list`، `gzip -t` و checksum موفق داشته باشد؛
- پیش از restore، API را بالا نیاورید؛
- در restore آفلاین از `up --no-build` استفاده کنید؛ `deploy.sh` ممکن است برای
  build به registry خارجی نیاز داشته باشد؛
- `.env`، dump و image archive را در Git یا CDN عمومی قرار ندهید؛
- روی DB مقصد `--clean` را فقط وقتی اجرا کنید که مقصد، DB اختصاصی هواچ باشد؛
- هیچ backupی را تا قبل از یک restore آزمایشی معتبر تلقی نکنید؛
- بعد از انتقال DNS، health، یک Point، یک Route، login ادمین، Admin و sitemap
  را بررسی کنید؛
- اگر provider خارجی قطع است، ingest را متوقف نگه دارید و از آخرین forecast
  restore‌شده به‌عنوان دادهٔ موقت و دارای timestamp استفاده کنید.
