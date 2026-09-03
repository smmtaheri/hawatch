# رفتار صفحهٔ Point (محتوای Forecast Place)

مرجع بصری: [design/pages/place-forecast.md](../../design/pages/place-forecast.md) — **همان قالب Destination**؛ screenshot جدا وجود ندارد.

## ورود

- Home autocomplete → `/points/{slug}`
- Route timeline/card → `/points/{slug}` + `state.fromRoute`
- URL مستقیم / share / refresh
- لینک نقطهٔ مقصد از مسیر مستقیماً به `/destination/{slug}` ساخته می‌شود؛ endpoint
  و URL legacy برای سازگاری نگه‌داری نمی‌شود.

## API

`GET /api/v1/points/{weather_point_slug}/forecast/?date=&period=`

قرارداد اول: `subject` / `hero` / `forecast.{days,period,current,hourly,meta}` / `metrics` / `decision` / `related_routes`.
aliasهای ریشه و `point` / `weather` فقط سازگاری‌اند.

## هویت و ظاهر

- root class: `destination-page` (نه `point-page`)
- sidebar در desktop و دو مسیر برتر + bottom sheet در mobile از همان قالب مشترک استفاده می‌کنند؛ عنوان: «مسیرهای عبوری از این نقطه»
- technical-card همیشه (EmptyState اگر متریک نبود)
- با `fromRoute`، CTA بازگشت فقط در hero؛ planner از `fromRoute` seed نمی‌شود
- footer مشترک: «هوای مقصد، برنامهٔ مسیر»
- headline بازه (`period.headline`) در UI نمایش داده نمی‌شود؛ فقط کارت‌های ساعتی و legend

## controls

day/period مانند Destination (URL بعد از انتخاب صریح sync می‌شود)؛ بدون planner gauge.

## acceptance

- [ ] همان shell مقصد
- [ ] نقطهٔ مقصد توچال فقط از `/destination/tochal` قابل دسترسی عمومی است
- [ ] dark/light route cards روی surface مشترک
- [ ] بدون overflow
