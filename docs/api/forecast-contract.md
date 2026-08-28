# قرارداد forecast هواچ

timezone محصول: `Asia/Tehran` (زمان رسمی ایران، مستقل از timezone مرورگر یا سرور).

بازهٔ قابل مشاهدهٔ این نسخه:

- ۷ روز: دیروز، امروز، و پنج روز بعد
- hourly: هر دو ساعت؛ هر بازه دقیقاً چهار کارت دارد.
- سه بازهٔ غیرهم‌پوشان (نسخهٔ قبلی با دو بازهٔ ۰۰–۱۲ / ۱۲–۲۴ **جایگزین شده**):

| `period` | برچسب | پنجرهٔ منطقی | کارت‌ها |
| --- | --- | --- | --- |
| `morning` | صبح | ۰۳:۰۰–۱۱:۰۰ | ۰۳، ۰۵، ۰۷، ۰۹ |
| `afternoon` | بعدازظهر | ۱۱:۰۰–۱۹:۰۰ | ۱۱، ۱۳، ۱۵، ۱۷ |
| `night` | شب | ۱۹:۰۰–۰۳:۰۰ روز بعد | ۱۹، ۲۱، ۲۳، ۰۱ |

## معنای تاریخ برای `night`

برای `period=night`، `date` یعنی **شبِ همان روز** (شروع از ۱۹:۰۰). مثال:

`date=2026-08-28&period=night` → ۱۹:۰۰، ۲۱:۰۰، ۲۳:۰۰ در ۲۸ اوت + ۰۱:۰۰ در ۲۹ اوت.

فیلتر با پنجرهٔ timezone-aware انجام می‌شود؛ نباید فقط با یک تاریخ تقویمی فیلتر شود.

## انتخاب پیش‌فرض (بدون query صریح)

| ساعت محلی تهران | `selected_period` | `selected_date` |
| --- | --- | --- |
| ۰۰:۰۰–۰۲:۵۹ | `night` | دیروز |
| ۰۳:۰۰–۱۰:۵۹ | `morning` | امروز |
| ۱۱:۰۰–۱۸:۵۹ | `afternoon` | امروز |
| ۱۹:۰۰–۲۳:۵۹ | `night` | امروز |

اگر کاربر `date` یا `period` را صریح بفرستد، API همان را برمی‌گرداند و frontend بعد از load آن را overwrite نمی‌کند. در بار اول بدون query، frontend نباید `period=morning` بفرستد؛ backend مقدار را در `meta` برمی‌گرداند.

## past / current / future

flagها از **timestamp واقعی** هر reading (`forecast_at`) نسبت به `current_local_time` محاسبه می‌شوند. ساعت‌های گذشته dim می‌شوند؛ ساعت جاری مشخص است؛ دادهٔ cross-midnight در `night` همین قواعد را دارد.

## envelope

```text
forecast
├── destination | route | point
├── days[]
├── current?
├── hourly[]
├── alerts?/hero
├── decision
├── freshness / meta
```

هر reading شامل temperature، apparent temperature، condition/code، wind speed/gust/direction، precipitation، visibility، cloud cover، UV در صورت وجود، و flagهای:

- `is_yesterday`
- `is_today`
- `is_past`
- `is_current`
- `is_future`

تمام timestampهای public (`forecast_at`، `valid_from`، `valid_to`، `generated_at` و `current_local_time`) با offset `Asia/Tehran` برمی‌گردند؛ timestamp UTC در قرارداد frontend نمایش داده نمی‌شود.

## metadata

- `data_mode`
- `provider` / `source`
- `generated_at`
- `current_local_time`
- `timezone`
- `seed_version`
- `freshness` (`ready` | `stale` | `partial`)
- `selected_date` / `selected_period`
- `valid_from` / `valid_to`

دادهٔ دمو به‌عنوان مشاهدهٔ واقعی معرفی نمی‌شود؛ `data_mode=demo` است.

## route planner

- `start_time` در هر period به بازهٔ همان period محدود می‌شود.
- برای `night`، `00:00`–`02:30` به‌عنوان ادامهٔ همان شب تفسیر می‌شود؛ `03:00` متعلق به `morning` است.
- وقتی `timing_pending=true` است، arrival/ETA ساخته نمی‌شود.
- وقتی `timing_pending=true` است، برای خلاصهٔ هر point فقط دادهٔ همان point و همان period انتخاب‌شده قابل نمایش است؛ fallback ثابت ساعت ۱۲ برای همهٔ periodها معتبر نیست و نباید استفاده شود. زمان point/ETA در این حالت `null` است.
- `timing_pending` یک flag قراردادی برای client است و نباید عیناً در متن کاربر نمایش داده شود؛ UI باید پیام فارسی قابل فهم ارائه کند.

## نقطهٔ canonical (standalone WeatherPoint)

- `GET /api/v1/points/{weather_point_slug}/forecast/?date=&period=`
- URL frontend: `/points/{weather_point_slug}` — مثال `/points/pas_ghaleh`
- envelope: `point` (slug، name، aliases، مختصات، elevation، status، provenance)، `related_destinations[]`، `related_routes[]` (dedup)، `days`، `current`/`weather`، `hourly`، `hero`، `empty`/`partial`، `meta`
- **بدون** `arrival_minutes`، ETA، ascent، speed، یا timing مسیر
- نقاط بدون WeatherPoint فعال صفحهٔ standalone ندارند

## legacy route-point (سازگاری موقت)

- `GET /api/v1/routes/{route_slug}/points/{point_slug}/forecast/?date=&period=`
- پاسخ شامل `canonical_href` و `weather_point_slug` برای resolve به URL تمیز. اگر WeatherPoint از نوع `destination` باشد و به Destination متصل باشد، `canonical_href` باید `/destination/{destinationSlug}` باشد؛ در غیر این صورت `/points/{weather_point_slug}`.
- frontend legacy `/routes/.../points/...` را redirect می‌کند؛ `start_time`/`speed` از URL حذف می‌شوند

## جست‌وجوی پیشنهاد (Home)

- `GET /api/v1/search/suggestions/?q=...`
- حداقل ۲ کاراکتر normalize‌شده؛ prefix match؛ حداکثر ۸ نتیجه
- انواع: `destination` → `/destination/{slug}`؛ `point` → `/points/{weather_point_slug}`
- label نمونه: `قلهٔ توچال — مقصد` · `پس‌قلعه — نقطهٔ مسیر · توچال`

## slider commit

در Route، مقدار gauge بلافاصله با state محلی به‌روز می‌شود؛ commit به URL/API فقط در پایان تعامل (pointer/touch release، blur، Enter/Space) یا debounce کوتاه (~۳۰۰ms) انجام می‌شود.

## contract بصری مشترک

- `meta.current_local_time` تنها مرجع تعیین بازهٔ جاری/گذشته در timezone رسمی ایران است.
- UI باید periodهای کاملاً گذشته را کم‌رنگ کند و period جاری/آینده را عادی نگه دارد.
- فیلد `updated_label` برای نمایش عمومی deprecated است؛ timestamp خام ISO نباید در UI رندر شود.
- Route نباید `hourly` مقصد را به‌عنوان weather pointهای مسیر نمایش دهد؛ کارت‌های point باید از دادهٔ point-level همان point ساخته شوند.
