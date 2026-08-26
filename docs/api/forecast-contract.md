# قرارداد forecast هواچ

timezone پیش‌فرض: `Asia/Tehran`.

بازهٔ قابل مشاهدهٔ این نسخه، مطابق screenshot و live inspection:

- ۷ روز: دیروز، امروز، و پنج روز بعد
- hourly: هر دو ساعت، ۶ کارت در هر بازه
- صبح: ۰۰، ۰۲، ۰۴، ۰۶، ۰۸، ۱۰
- بعدازظهر: ۱۲، ۱۴، ۱۶، ۱۸، ۲۰، ۲۲

اگر منبع دیگری بازهٔ متفاوت نشان دهد، همان ۷ روز و گام دوساعته مبنای UI است.

## envelope

```text
forecast
├── destination | route
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
- `valid_from` / `valid_to`

دادهٔ دمو به‌عنوان مشاهدهٔ واقعی معرفی نمی‌شود؛ `data_mode=demo` است.
