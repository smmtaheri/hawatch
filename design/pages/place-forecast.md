# مشخصات قالب مشترک Point Forecast

> **تصمیم محصول:** قالب بصری جداگانه‌ای برای Point وجود ندارد. همهٔ نقطه‌ها همان صفحهٔ React، همان component tree، همان responsive layout و همان theme را رندر می‌کنند. فقط داده و wording ممکن است فرق کند.

## ۱. هدف

کاربر باید بتواند پیش‌بینی یک مکان فیزیکی (WeatherPoint) را ببیند؛ همهٔ مکان‌ها از `/points/{slug}` قابل دسترسی‌اند.

## ۲. هویت domain

| مفهوم | نقش |
| --- | --- |
| **WeatherPoint** | تنها موجودیت نقطه: مختصات، ارتفاع، هویت، پروفایل، forecast و aliases |
| **kind/importance** | ویژگی همان WeatherPoint برای تشخیص نقطهٔ شاخص، مسیر یا نقطهٔ مشترک؛ موجودیت جدا نیست |
| **Route** | مجموعهٔ مرتب WeatherPointها با origin/target |
| **RoutePoint** | عضویت مسیر‌محور: ترتیب، timing، note — نه حقیقت فیزیکی |

## ۳. URL و قالب

| URL | قالب React | تفاوت محتوا |
| --- | --- | --- |
| `/points/{slug}` | `PlaceForecastPage` (`kind=point`) | عنوان/hero و مختصات از همان WeatherPoint؛ sidebar مسیرهای مرتبط |

- همهٔ WeatherPointها صفحهٔ مستقل `/points/{slug}` دارند (مثلاً `tochal`).
- تصاویر مرجع Point در `design/screens/point/` baseline بصری برای همهٔ Point Forecastها هستند.
- صفحهٔ جدا و template موازی بازنشسته شده است؛ همهٔ pointها از shell مشترک
  `.point-page` / `.point-shell` / `.point-hero` استفاده می‌کنند.

## ۴. ترتیب بخش‌ها (همان Point)

۱. header  
۲. (اختیاری) CTA «بازگشت به مسیر …» فقط در slot اکشن hero (نه جایگزین sidebar)  
۳. hero تصویر + overlay + breadcrumb + عنوان + status/alert  
۴. در موبایل، دو مسیر برتر + دکمهٔ انتخاب همه در bottom sheet؛ در desktop مسیرهای مرتبط در sidebar
۵. day selector («انتخاب روز») + period toggle چهارگزینه‌ای
۶. hourly forecast (کارت‌ها + legend؛ بدون نمایش `period.headline`؛ کارت جاری در موبایل خودکار در viewport قرار می‌گیرد)
۷. جزئیات تخصصی (metrics) — همیشه همان `technical-card`؛ اگر متریک نبود EmptyState پایدار
۸. sidebar مسیرهای مرتبط + decision card
۹. footer مشترک محصول: «هوای نقطه، برنامهٔ مسیر»

جزئیات تخصصی از آیکون‌های رسمی `apps/web/public/icons/specialist/` استفاده می‌کند. هر
متریک یک نام معنایی مثل `wind-average` یا `visibility` از API می‌گیرد و component
`SpecialistMetricIcon` آن را از sprite رندر می‌کند؛ glyphهای موقت داخل متن متریک
استفاده نمی‌شوند. رنگ آیکون با `color` متریک برای حالت‌های عادی، مهم و بحرانی هماهنگ
می‌شود و label/value متنی همیشه باقی می‌ماند.

برچسب مسیرها:

- point: «مسیرهای متصل به …»
- point: «مسیرهای عبوری از این نقطه»

در موبایل فقط دو مسیر اول با اولویت `featured` به‌صورت inline دیده می‌شوند. باقی مسیرها در یک bottom sheet دسترس‌پذیر با بستن از طریق دکمه، backdrop، Escape یا swipe-down باز می‌شوند. انتخاب مسیر مستقیماً به route می‌رود و به forecast فعلی request اضافه‌ای نمی‌کند.

## ۴٫۱ قرارداد API و URL

- قرارداد اول: `subject` / `hero` / `forecast.{days,period,current,hourly,meta}` / `metrics` / `decision` / `related_routes`
- aliasهای ریشه فقط سازگاری backend هستند؛ frontend از `forecast.*` می‌خواند
- URL تمیز بدون `date`/`period` می‌ماند تا کاربر صریحاً روز/بازه را عوض کند؛ بعد هر دو kind با هم sync می‌شوند
- `fromRoute` فقط برای دکمهٔ بازگشت است و planner نقطه را seed نمی‌کند
- برای قلهٔ اصلی نیز لینک canonical `/points/tochal` ساخته می‌شود؛ نام‌های قدیمی
  فقط در migrationهای تاریخی برای upgrade دیتابیس دیده می‌شوند و route عمومی یا
  redirect/back-compat جداگانه ندارند.

## ۵. stateها

loading / ready / empty / partial / error / stale — یکسان برای هر دو URL.  
timestamp خام ISO و `timing_pending` در متن UI نمایش داده نمی‌شود.

## ۶. acceptance

- [ ] `/points/tochal-sarband-square` و `/points/tochal` از یک template و کلاس‌های point shell استفاده می‌کنند
- [ ] dark/light و mobile/desktop بدون drift بصری بین دو URL
- [ ] بدون overflow افقی
- [ ] موبایل فقط دو مسیر برتر را inline نشان می‌دهد و بقیه را در bottom sheet باز می‌کند
- [ ] سه period button هم‌اندازه و در یک ردیف موبایل نمایش داده می‌شوند
- [ ] در موبایل کارت ساعتی جاری یا اولین کارت بازهٔ انتخاب‌شده خودکار در viewport قرار می‌گیرد
- [ ] shell مشترک `.point-page` استفاده می‌شود؛ زبان بصری جداگانه‌ای برای نقطه ساخته نمی‌شود
- [ ] نقطهٔ اصلی و نقطهٔ مسیر هر دو به canonical point URL هدایت می‌شوند

## ۷. تصویر مرجع

همان چهار تصویر Point:

- [light/mobile](../screens/point/light/mobile.png)
- [dark/mobile](../screens/point/dark/mobile.png)
- [light/web](../screens/point/light/web.png)
- [dark/web](../screens/point/dark/web.png)

Fallback بدون تصویر تأیید‌شده: سطح گرادیان مستند (`point-hero--fallback`) — asset جدید اضافه نمی‌شود. در mobile، hero همهٔ Placeها عمداً به همین سطح کوتاه و بدون تصویر تبدیل می‌شود؛ breadcrumb تکراری پنهان است و عنوان و statusها در ارتفاع hero مرکز می‌گیرند.
