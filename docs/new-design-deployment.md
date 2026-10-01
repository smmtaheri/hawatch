# QA مستقل طراحی جدید هواچ

این تغییر فقط برای برنچ `new-design` است. با اجرای دستی `deploy-hawatch`، checkout برنچ `main` روی gateway عادی production (پورت ۸۰ در تنظیم استاندارد) و checkout برنچ `new-design` هم‌زمان روی gateway مستقل پورت ۵۰۵۰ به‌روز می‌شوند. هیچ deploy، restart، migration، seed یا تغییر دیتابیس اصلی در جریان پیاده‌سازی این کار انجام نشده است؛ این کارها فقط پس از اجرای آگاهانهٔ فرمان توسط اپراتور رخ می‌دهند.

## ساختار دو نسخه

| نسخه | checkout سرور | Compose | پورت عمومی | منبع داده |
|---|---|---|---|---|
| production | `/root/hawatch`، برنچ `main` | `hawatch` و `infra/compose/compose.yaml` همان برنچ | پورت فعلی دامنه، معمولاً `80` | دیتابیس فعلی |
| staging/QA | `/root/hawatch-new-design`، برنچ `new-design` | `hawatch-new-design` و `infra/compose/compose.new-design.yaml` | `5050` | همان دیتابیس از طریق API مستقل QA |

QA فقط `qa-api`، `qa-web` و `qa-gateway` دارد؛ database، ingest، scheduler و maintenance جدید ندارد. API با Gunicorn مستقیم اجرا می‌شود و `entrypoint.sh` که migration/seed انجام می‌دهد اجرا نمی‌شود. دیتابیس و کلیدها از فایل موجود production به `env_file` داده می‌شوند؛ secrets در checkout QA کپی نمی‌شوند. تغییر schema و migration جدیدی لازم نیست. تصاویر، volume لاگ و network داخلی QA مستقل هستند؛ تنها اتصال مشترک، network دیتابیس فعلی `hawatch_default` است. Compose جدید پورت‌های ۸۰، ۴۴۳، ۸۰۰۰ یا پورت‌های Athlore را publish نمی‌کند.

## آماده‌سازی و اجرای دستی

دستورهای زیر برای اجرای خود اپراتور هستند؛ در این کار اجرا نشده‌اند. IP از `ssh -G hawatch` و تنظیم موجود استقرار تأیید شده است.

روی سیستم توسعه، پس از بررسی commitها:

```bash
git switch new-design
git push -u origin new-design
scp infra/compose/new-design.env.example hawatch:/root/hawatch-new-design.qa.env
ssh hawatch 'chmod 600 /root/hawatch-new-design.qa.env'
install -Dm755 scripts/deploy-hawatch "$HOME/.local/bin/deploy-hawatch"
export PATH="$HOME/.local/bin:$PATH"
deploy-hawatch
```

فایل فرمان قبلی خارج از ریپو در PATH یا فایل‌های shell قابل پیدا کردن نبود؛ نسخهٔ نصب‌پذیر داخل `scripts/deploy-hawatch` آماده شده است. فرمان قدیمی ریپو `scripts/publish-deploy.sh` حفظ شده است.

اجرای wrapper از `new-design` این برنچ را push می‌کند، production را از `origin/main` منتشرشده و با `scripts/deploy.sh` موجود در checkout اصلی به‌روز می‌کند، سپس QA را از checkout مستقل به پورت ۵۰۵۰ می‌رساند. اجرای wrapper از `main` نیز main را push می‌کند و سپس هر دو release را به‌روز می‌کند. frontend جدید وارد checkout production نمی‌شود. wrapper خودش stage، commit، reset، merge یا پاک‌کردن فایل‌های dirty انجام نمی‌دهد؛ checkout سرور dirty یا branch اشتباه باعث توقف می‌شود. قبل از شروع QA، مقدار `HAWATCH_QA_PORT` باید دقیقاً `5050` باشد. QA تا healthy شدن API، web و gateway صبر می‌کند و `/healthz` پورت ۵۰۵۰ را بررسی می‌کند؛ بنابراین خروجی موفق wrapper یعنی هر دو release واقعاً پاسخ‌گو هستند. ساخت QA پیش از جایگزینی کانتینرهای QA است و شکست build آن‌ها را نگه می‌دارد. push هیچ workflow استقرار خودکاری فعال نمی‌کند.

**رفتار قدیمی production:** فرمان `scripts/deploy.sh` برنچ اصلی، bootstrap/migration/sync قبلی خود را در اجرای دستی اپراتور حفظ می‌کند. این رفتار مربوط به production است؛ QA هیچ‌کدام را اجرا نمی‌کند.

نشانی پس از اجرای دستی موفق:

`http://202.133.89.120:5050`

برای به‌روزرسانی فقط QA، پس از push برنچ:

```bash
ssh hawatch 'HAWATCH_QA_DIR=/root/hawatch-new-design HAWATCH_QA_ENV_FILE=/root/hawatch-new-design.qa.env bash /root/hawatch-new-design/scripts/deploy-new-design.sh'
```

اولین clone مستقل QA را wrapper می‌سازد. اگر فقط QA را برای نخستین بار اجرا می‌کنید، ابتدا روی سرور:

```bash
git clone --branch new-design --single-branch https://github.com/smmtaheri/hawatch.git /root/hawatch-new-design
HAWATCH_QA_DIR=/root/hawatch-new-design HAWATCH_QA_ENV_FILE=/root/hawatch-new-design.qa.env bash /root/hawatch-new-design/scripts/deploy-new-design.sh
```

## متغیرها

فایل `/root/hawatch-new-design.qa.env` با الگوی versionشده ساخته می‌شود:

| متغیر | مقدار اولیه / نقش |
|---|---|
| `HAWATCH_PRODUCTION_ENV_FILE` | `/root/hawatch/.env`؛ فایل موجود secrets و اتصال همان دیتابیس |
| `HAWATCH_PRODUCTION_NETWORK` | `hawatch_default`؛ نام واقعی network Compose فعلی |
| `HAWATCH_PRODUCTION_DB_HOST` | `postgres`؛ alias سرویس دیتابیس موجود |
| `HAWATCH_QA_ALLOWED_HOSTS` | `202.133.89.120`؛ برای HTTPS نام QA را هم اضافه کنید |
| `HAWATCH_QA_ORIGIN` | `http://202.133.89.120:5050`؛ مرجع CSRF و Secure cookie |
| `HAWATCH_QA_BIND_IP` | `0.0.0.0`؛ در حالت reverse proxy محلی `127.0.0.1` |
| `HAWATCH_QA_PORT` | `5050` |
| `HAWATCH_PUBLIC_ORIGIN` | `https://hawatch.ir`؛ canonical اصلی، بدون IP QA |

فایل production باید `POSTGRES_DB`، `POSTGRES_USER`، `POSTGRES_PASSWORD` و `DJANGO_SECRET_KEY` فعلی را داشته باشد. تنظیمات allowlist ورود `DEMO_AUTH_ALLOWED_PHONE` و `DEMO_AUTH_FIXED_OTP` نیز همان پشتیبانی واقعی فعلی بکند را حفظ می‌کنند؛ این تغییر سرویس SMS یا مدل پرداخت جدید اضافه نمی‌کند. مقدار شماره/کد در build فرانت قرار نمی‌گیرد.

wrapper متغیرهای `HAWATCH_LOCAL_DIR`، `HAWATCH_SSH_HOST`، `HAWATCH_SERVER_DIR`، `HAWATCH_QA_DIR`، `HAWATCH_QA_ENV_FILE`، `HAWATCH_SERVER_IP` و `HAWATCH_PUBLIC_HOST` را برای مسیرهای غیرپیش‌فرض می‌پذیرد. `DOCKER_BUILD_RETRIES` برای build QA به‌صورت پیش‌فرض ۲ است.

`hawatch.config.settings.qa` نام cookieها را `hawatch_qa_session` و `hawatch_qa_csrf` قرار می‌دهد؛ session/CSRF مرورگر QA با دامنهٔ اصلی مخلوط نمی‌شود. درخواست‌ها same-origin و `/api/v1` هستند. proxy مقدار Host با پورت را برای بررسی CSRF نگه می‌دارد. در HTTP، Secure cookie غیرفعال است؛ با origin از نوع HTTPS خودکار فعال می‌شود. حساب‌ها و عضویت‌ها از دیتابیس اصلی خوانده می‌شوند؛ اقدام واقعی ورود/خروج اپراتور پس از انتشار، از مکانیزم session موجود استفاده می‌کند.

## HTTPS و اشتراک‌گذاری

[Web Share طبق استاندارد W3C](https://www.w3.org/TR/web-share/) به secure context و اقدام مستقیم کاربر نیاز دارد. [Clipboard.writeText](https://developer.mozilla.org/en-US/docs/Web/API/Clipboard/writeText) نیز secure context می‌خواهد. HTTP روی IP عمومی چنین زمینه‌ای ندارد. رابط در این حالت پیش‌نمایش PNG، لینک قابل کلیک، ذخیرهٔ تصویر و کپی با `execCommand('copy')` را دارد؛ اگر مرورگر کپی قدیمی را نیز نپذیرد، پیام انتخاب و کپی دستی لینک نمایش داده می‌شود. موفقیت کپی ساختگی گزارش نمی‌شود.

در HTTPS و مرورگر دارای `canShare({files})`، دکمهٔ «ارسال تصویر و لینک» داخل پیش‌نمایش native share sheet را از کلیک تازه باز می‌کند؛ تولید PNG در انتظار async، مجوز transient activation را مصرف نمی‌کند. لغو share خطا نمایش نمی‌دهد. انتخاب تلگرام، بله یا برنامهٔ دیگر را خود سیستم‌عامل انجام می‌دهد. پشتیبانی PNG + URL به مرورگر و برنامهٔ مقصد وابسته است؛ iOS/Android واقعی باید در QA اپراتور بررسی شوند.

برای HTTPS بدون دست‌زدن به listenerهای مشترک سرور، نمونهٔ `infra/compose/compose.new-design-tls.yaml` و `infra/nginx/new-design-tls.conf` فراهم شده است: فقط **پورت ۵۰۵۱** جدا و یک certificate معتبر مربوط به نام QA استفاده می‌شود. DNS نام QA باید به IP سرور اشاره کند. اپراتور گواهی را با DNS-01 از سرویس گواهی فعلی تهیه می‌کند؛ نیاز به اشغال ۸۰/۴۴۳ یا restart وب‌سرور production نیست. برای خود IP باید certificate معتبر با IP SAN داشته باشید؛ certificate نام دامنه برای IP معتبر نیست.

روی سرور، فایل QA را برای این حالت تنظیم کنید:

```dotenv
HAWATCH_QA_ALLOWED_HOSTS=202.133.89.120,qa.hawatch.ir
HAWATCH_QA_ORIGIN=https://qa.hawatch.ir:5051
HAWATCH_QA_TLS_PORT=5051
HAWATCH_QA_CERT_DIR=/root/hawatch-qa-certs
```

دو فایل گواهی `fullchain.pem` و `privkey.pem` باید داخل مسیر certificate موجود باشند. سپس اجرای دستی:

```bash
cd /root/hawatch-new-design
docker compose --project-name hawatch-new-design --env-file /root/hawatch-new-design.qa.env -f infra/compose/compose.new-design.yaml -f infra/compose/compose.new-design-tls.yaml up -d --build
```

HTTP پورت ۵۰۵۰ همچنان برای مشاهده باز می‌ماند؛ ورود و آزمون share در این حالت روی HTTPS انجام شود، چون cookie تنظیم‌شده Secure است. wrapper معمولی بعدی سرویس TLS موجود را حذف نمی‌کند، ولی برای به‌روزرسانی پیکربندی TLS همین دستور ترکیبی را دستی اجرا کنید. اگر reverse proxy موجود سازمان برای نام QA آماده است، می‌تواند HTTPS را به gateway ۵۰۵۰ وصل کند؛ ساخت vhost و reload آن فقط اقدام دستی اپراتور است.

## SEO و بررسی پس از انتشار

QA روی همهٔ پاسخ‌ها `X-Robots-Tag: noindex, nofollow, noarchive` دارد؛ head اولیهٔ SSR و SPA و metadata بعد از hydration نیز noindex می‌مانند. `/robots.txt` محیط QA همه‌چیز را disallow می‌کند؛ `/sitemap.xml` QA پاسخ ۴۰۴ دارد. canonicalها به `https://hawatch.ir` اشاره می‌کنند. robots، sitemap، SSR و سیاست دامنهٔ اصلی از checkout اصلی تغییر نمی‌کند. جزئیات نقطه/مسیر ناشناخته همچنان از Django پاسخ ۴۰۴ می‌گیرند. SSR فهرست جدید مسیرها فقط با `HAWATCH_NEW_DESIGN=True` فعال است؛ redirect قدیمی production در تنظیمات معمول محفوظ است.

بررسی‌های خواندنی اپراتور پس از اجرا:

```bash
curl -sS -D - -o /dev/null http://202.133.89.120:5050/points/tochal
curl http://202.133.89.120:5050/robots.txt
curl -sS -D - -o /dev/null http://202.133.89.120:5050/points/this-point-does-not-exist
curl -sS -D - -o /dev/null http://202.133.89.120:5050/sitemap.xml
curl -sS -D - -o /dev/null https://hawatch.ir/points/tochal
```

در DevTools، تغییر period/ساعت/سرعت پس از دریافت `forecast/day/` نباید درخواست تازهٔ هوا ایجاد کند. ورود/خروج باید cache و روزهای مجاز را عوض کند. تغییر روز یک درخواست دارد؛ برگشت به روز دریافت‌شده در عمر cache درخواست ندارد. وضعیت اصلی production و Athlore را قبل/بعد اجرای دستی مقایسه کنید. انتقال frontend جدید به دامنهٔ اصلی مرحلهٔ جداگانه پس از تأیید QA است.
