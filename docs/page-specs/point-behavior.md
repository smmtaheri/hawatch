# رفتار صفحهٔ Point (محتوای Point Forecast)

مرجع بصری: [design/pages/place-forecast.md](../../design/pages/place-forecast.md) — **همان قالب Point**؛ screenshot جدا وجود ندارد.

## ورود

- Home autocomplete → `/points/{slug}`
- Route timeline/card → `/points/{slug}` + `state.fromRoute`
- URL مستقیم / share / refresh
- لینک هر نقطه از مسیر مستقیماً به `/points/{slug}` ساخته می‌شود؛ endpoint
  و URL legacy برای سازگاری نگه‌داری نمی‌شود.

## API

`GET /api/v1/points/{weather_point_slug}/forecast/?date=&period=`

قرارداد اول: `subject` / `hero` / `forecast.{days,period,current,hourly,meta}` / `metrics` / `decision` / `related_routes`.
aliasهای ریشه و `point` / `weather` فقط سازگاری‌اند.

## هویت و ظاهر

- root class: `point-page` (نه `point-page`)
- sidebar در desktop و دو مسیر برتر + bottom sheet در mobile از همان قالب مشترک استفاده می‌کنند؛ عنوان: «مسیرهای عبوری از این نقطه»
- technical-card همیشه (EmptyState اگر متریک نبود)
- با `fromRoute`، CTA بازگشت فقط در hero؛ planner از `fromRoute` seed نمی‌شود
- footer مشترک: «هوای نقطه، برنامهٔ مسیر»
- headline بازه (`period.headline`) در UI نمایش داده نمی‌شود؛ فقط کارت‌های ساعتی و legend

## controls

day/period مانند Point (URL بعد از انتخاب صریح sync می‌شود)؛ بدون planner gauge.

پنجره‌ها ثابت و غیرهم‌پوشان‌اند: بامداد ۰۰–۰۶، صبح ۰۶–۱۲، ظهر ۱۲–۱۸ و شب ۱۸–۲۴؛ هر پنجره سه برش دوساعته دارد. بازهٔ کاملاً گذشته نسبت به `meta.current_local_time` در `Asia/Tehran` کم‌رنگ است، اما بازهٔ انتخاب‌شده همچنان خوانا می‌ماند. بدون query صریح، API بر اساس ساعت تهران `date` و `period` پیش‌فرض برمی‌گرداند.

## محتوای انتخاب روز و mobile

- بالای day tabs فقط label «انتخاب روز» نمایش داده می‌شود؛ heading و توضیح تکراری حذف می‌شوند.
- روزها قبل از کنترل هوا قرار می‌گیرند. در موبایل دو مسیر برتر قبل از کنترل روز/هوا نمایش داده می‌شوند و مسیرهای باقی‌مانده از bottom sheet انتخاب می‌شوند.
- route card فقط نام مسیر و دو fact جداگانهٔ «ارتفاع‌گیری» و «مسافت» دارد؛ `trail_label` و `origin` زیر نام تکرار نمی‌شوند.
- کارت «جزئیات تخصصی» دو metric اول را inline نشان می‌دهد و بقیه را در sheet نیم‌صفحه‌ای قابل‌بستن نمایش می‌دهد. هیچ card یا grid نباید root را عریض‌تر کند.
- stale باید با هشدار قابل فهم نمایش داده شود؛ timestamp خام ISO و عبارت «آخرین به‌روزرسانی: ...» در UI نمایش داده نمی‌شود.

## خطا و دادهٔ ناقص

اگر forecast provider بخشی از داده را ندهد، مقدار موجود با timestamp نمایش داده شود و fieldهای ناقص `در دسترس نیست` یا معادل مشخص داشته باشند؛ از پرکردن silently با صفر خودداری شود.

## acceptance

- [ ] همان shell نقطه
- [ ] نقطهٔ توچال فقط از `/points/tochal` قابل دسترسی عمومی است
- [ ] dark/light route cards روی surface مشترک
- [ ] بدون overflow
