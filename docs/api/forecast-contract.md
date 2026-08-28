# قرارداد forecast هواچ

timezone پیش‌فرض: `Asia/Tehran`.

بازهٔ قابل مشاهدهٔ این نسخه:

- ۷ روز: دیروز، امروز، و پنج روز بعد
- hourly: هر دو ساعت، **۴ کارت** در هر بازهٔ زمانی
- سه بازهٔ غیرهم‌پوشان (نسخهٔ قبلی با دو بازهٔ ۰۰–۱۲ / ۱۲–۲۴ **جایگزین شده**):

| `period` | برچسب | پنجرهٔ منطقی | کارت‌ها |
| --- | --- | --- | --- |
| `morning` | صبح | ۰۲:۰۰–۱۰:۰۰ | ۰۲، ۰۴، ۰۶، ۰۸ |
| `afternoon` | بعدازظهر | ۱۰:۰۰–۱۸:۰۰ | ۱۰، ۱۲، ۱۴، ۱۶ |
| `night` | شب | ۱۸:۰۰–۰۲:۰۰ روز بعد | ۱۸، ۲۰، ۲۲، ۰۰ |

## معنای تاریخ برای `night`

برای `period=night`، `date` یعنی **شبِ همان روز** (شروع از ۱۸:۰۰). مثال:

`date=2026-08-28&period=night` → ۱۸:۰۰، ۲۰:۰۰، ۲۲:۰۰ در ۲۸ اوت + ۰۰:۰۰ در ۲۹ اوت.

فیلتر با پنجرهٔ timezone-aware انجام می‌شود؛ نباید فقط با یک تاریخ تقویمی فیلتر شود.

## انتخاب پیش‌فرض (بدون query صریح)

| ساعت محلی تهران | `selected_period` | `selected_date` |
| --- | --- | --- |
| ۰۰:۰۰–۰۱:۵۹ | `night` | دیروز |
| ۰۲:۰۰–۰۹:۵۹ | `morning` | امروز |
| ۱۰:۰۰–۱۷:۵۹ | `afternoon` | امروز |
| ۱۸:۰۰–۲۳:۵۹ | `night` | امروز |

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
- برای `night`، `00:00`–`01:30` به‌عنوان ادامهٔ همان شب تفسیر می‌شود؛ `02:00` متعلق به `morning` است.
- وقتی `timing_pending=true` است، arrival/ETA ساخته نمی‌شود.

## نقطهٔ مسیر (point detail)

- `GET /api/v1/routes/{route_slug}/points/{point_slug}/forecast/?date=&period=`
- لینک frontend: `/routes/{route_slug}/points/{point_slug}`
- Back از صفحهٔ نقطه به مسیر مبدأ با حفظ `date`، `period`، `start_time`، `speed` (در صورت وجود در URL).

## slider commit

در Route، مقدار gauge بلافاصله با state محلی به‌روز می‌شود؛ commit به URL/API فقط در پایان تعامل (pointer/touch release، blur، Enter/Space) یا debounce کوتاه (~۳۰۰ms) انجام می‌شود.
