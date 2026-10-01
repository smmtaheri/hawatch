# وضعیت محیط Stage هواچ

طراحی جدید برنچ `stage` در `main` ادغام شده است. از این پس
`scripts/deploy-hawatch` فقط برنچ `main` را روی سرویس اصلی deploy می‌کند؛ این
فرمان هیچ checkout، image یا container مربوط به stage را build یا اجرا نمی‌کند.

ابزارهای `scripts/deploy-stage.sh` و `scripts/deploy-stage-hawatch` برای سابقه و
فعال‌سازی احتمالی آینده در repository باقی مانده‌اند، اما نباید در نصب معمول
wrapper یا فرایند production استفاده شوند.

## خاموش‌کردن Stage موجود

بعد از deploy نسخهٔ جدید main، این فرمان را از سیستم توسعه اجرا کنید تا stage
فعال روی سرور خاموش شود و منابع Docker آن پاک شود؛ production روی پورت ۸۰ دست‌نخورده
می‌ماند:

```bash
ssh hawatch 'HAWATCH_STAGE_ENV_FILE=/root/hawatch-stage.env bash /root/hawatch/scripts/stage-down.sh'
```

این cleanup مقدار `HAWATCH_STAGE_ENABLED=0` را در فایل تنظیمات stage می‌نویسد و
projectهای `hawatch-stage` و `hawatch-new-design`، containerها، networkها، volume
لاگ و imageهای محلی همان stack را حذف می‌کند. فایل تنظیمات و checkout کد حذف
نمی‌شوند تا در صورت نیاز بتوان stage را بعداً دوباره بررسی کرد.

اگر مسیر checkout production یا فایل env روی سرور متفاوت است، command را با همان
مسیرها تغییر دهید:

```bash
ssh hawatch 'HAWATCH_STAGE_ENV_FILE=/PATH/TO/hawatch-stage.env bash /root/hawatch/scripts/stage-down.sh'
```

## Deploy production

از checkout محلی `main`، wrapper جدید را نصب و اجرا کنید:

```bash
git switch main
git pull --ff-only origin main
install -Dm755 scripts/deploy-hawatch "$HOME/.local/bin/deploy-hawatch"
rehash 2>/dev/null || hash -r 2>/dev/null || true
deploy-hawatch
```

اگر نام SSH یا مسیر سرور متفاوت است، متغیرهای `HAWATCH_SSH_HOST` و
`HAWATCH_SERVER_DIR` را هنگام اجرای `deploy-hawatch` تنظیم کنید. wrapper فقط
`origin/main` را push می‌کند، checkout `/root/hawatch` را fast-forward می‌کند و
`scripts/deploy.sh` production را اجرا می‌کند.
