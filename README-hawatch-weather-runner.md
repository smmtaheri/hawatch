# Runner جمع‌آوری هوای هواچ

`hawatch_weather_runner.py` یک جمع‌کنندهٔ کم‌مصرف و production-like برای Open‑Meteo است. این نسخه فقط داده جمع می‌کند و هیچ تغییری در UI یا دیپلوی سایت هواچ نمی‌دهد.

## رفتار اصلی

- فقط نقاطی را می‌خواند که در کاتالوگ `weather_sampling_enabled=true` و مختصات معتبر دارند.
- هر نقطه همچنان با `latitude` و `longitude` واقعی خودش درخواست می‌شود.
- ارتفاع کاتالوگ برای نقاط دارای ارتفاع ارسال می‌شود؛ نقاط فاقد ارتفاع در batch جداگانه با DEM پیش‌فرض Open‑Meteo خوانده می‌شوند.
- از یک مدل `best_match`، `cell_selection=land` و ده متغیر hourly استفاده می‌کند.
- retry محدود، exponential backoff، `Retry-After` و تشخیص rate limitهای minutely/hourly/daily/monthly دارد.
- batch موفق، checkpoint، manifest اجرای کامل، JSONL log و `latest.json` را اتمیک می‌نویسد.
- `latest.json` فقط بعد از کامل شدن همهٔ batchها عوض می‌شود؛ اجرای ناقص آن را لمس نمی‌کند.
- با `SIGTERM` و `SIGINT` در فاصلهٔ بین درخواست‌ها و sleepها graceful shutdown می‌کند.

## اجرای دستی

اول کاتالوگ را validate و برنامه را ببین:

```bash
python3 hawatch_weather_runner.py \
  --catalog /opt/hawatch-weather/hawatch_route_points_catalog.json \
  --data-dir /opt/hawatch-weather/data \
  --state-dir /opt/hawatch-weather/state \
  --logs-dir /opt/hawatch-weather/logs \
  --batch-size 100 \
  --pause-seconds 10 \
  --forecast-hours 72 \
  --dry-run
```

یک چرخهٔ واقعی:

```bash
python3 hawatch_weather_runner.py \
  --catalog /opt/hawatch-weather/hawatch_route_points_catalog.json \
  --data-dir /opt/hawatch-weather/data \
  --state-dir /opt/hawatch-weather/state \
  --logs-dir /opt/hawatch-weather/logs \
  --batch-size 100 \
  --pause-seconds 10 \
  --forecast-hours 72 \
  --once
```

اجرای طولانی‌مدت با خود اسکریپت هم ممکن است، ولی برای سرور systemd timer پیشنهاد می‌شود:

```bash
python3 hawatch_weather_runner.py ... --daemon --interval-seconds 14400
```

## خروجی‌ها

```text
data/
  latest.json
  runs/<run-id>.json
  runs/<run-id>.partial.json
  batches/<run-id>/batch-0001.json
state/
  checkpoint.json
  hawatch-weather.lock
logs/
  hawatch-weather.jsonl
  hawatch-weather-error.jsonl
```

بررسی سلامت چرخه‌ها:

```bash
tail -f logs/hawatch-weather.jsonl | jq -c .
jq -c 'select(.event == "run_completed" or .event == "run_incomplete")' logs/hawatch-weather.jsonl
jq -c 'select(.event == "batch_attempt" and .http_status == 429)' logs/hawatch-weather.jsonl
jq -s 'map(select(.event == "run_completed")) | map(.summary.duration_seconds) | add / length' logs/hawatch-weather.jsonl
jq '{run_id, retrieved_at_utc, points: (.points | length), model: .request.model_requested}' data/latest.json
```

## واحدهای systemd

`hawatch-weather.service` و `hawatch-weather.timer` نمونهٔ آماده‌اند. قبل از نصب، مسیر `/opt/hawatch-weather` و کاربر `hawatch` را با مسیر واقعی سرور عوض کن.

```bash
sudo cp hawatch-weather.service hawatch-weather.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now hawatch-weather.timer
systemctl status hawatch-weather.timer
journalctl -u hawatch-weather.service -f
```

## نکتهٔ API و دقت

Open‑Meteo خروجی مدل عددی و downscaling است، نه اندازه‌گیری ایستگاه محلی. در `latest.json` برای هر نقطه این موارد کنار هم باقی می‌مانند:

- مختصات و ارتفاع درخواست‌شده از کاتالوگ؛
- مختصات سلول برگشتی API؛
- ارتفاع سلول برگشتی؛
- زمان دریافت و `generationtime_ms`؛
- مدل درخواستی و نسخهٔ مدل در صورت برگشت از API.

مدل/نسخهٔ واقعی در پاسخ فعلی `best_match` برنگشت؛ بنابراین runner آن را جعل نمی‌کند و `model_versions_observed` را خالی نگه می‌دارد.

منابع رسمی:

- [مستندات Forecast API](https://open-meteo.com/en/docs)
- [قیمت‌گذاری و محدودیت‌های Free API](https://open-meteo.com/en/pricing)
- [Terms و ملاحظات دقت/دسترس‌پذیری](https://open-meteo.com/en/terms)
- [ریپوی رسمی Open‑Meteo](https://github.com/open-meteo/open-meteo)
