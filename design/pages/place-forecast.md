# مشخصات قالب مشترک Forecast Place

> **تصمیم محصول:** قالب بصری جداگانه‌ای برای Point وجود ندارد. Destination و Point هر دو همان صفحهٔ React، همان component tree، همان responsive layout و همان theme را رندر می‌کنند. فقط داده و wording ممکن است فرق کند.

## ۱. هدف

کاربر باید بتواند پیش‌بینی یک مکان فیزیکی (WeatherPoint) را ببیند — چه آن نقطه نقش مقصد عمومی داشته باشد (`/destination/{slug}`) و چه نقطهٔ عادی مسیر (`/points/{slug}`).

## ۲. هویت domain

| مفهوم | نقش |
| --- | --- |
| **WeatherPoint** | موجودیت فیزیکی: مختصات، ارتفاع، forecast، aliases |
| **Destination (profile)** | نقش عمومی/محصولی صفر یا یک برای یک WeatherPoint (تصویر، عنوان، محبوبیت، slug عمومی) |
| **Route** | مجموعهٔ مرتب WeatherPointها با origin/target |
| **RoutePoint** | عضویت مسیر‌محور: ترتیب، timing، note — نه حقیقت فیزیکی |

## ۳. URL و قالب

| URL | قالب React | تفاوت محتوا |
| --- | --- | --- |
| `/destination/{destinationSlug}` | `PlaceForecastPage` (`kind=destination`) | عنوان/هero از profile؛ sidebar: «مسیرهای منتهی به {مقصد}» |
| `/points/{weatherPointSlug}` | همان `PlaceForecastPage` (`kind=point`) | عنوان/مختصات نقطه؛ sidebar: «مسیرهای عبوری از این نقطه» |

- اگر WeatherPoint دارای Destination profile باشد، `/points/{slug}` به `/destination/{profileSlug}` resolve می‌شود (مثلاً `tochal_summit` → `touchal`).
- تصاویر مرجع Destination در `design/screens/destination/` baseline بصری برای **همهٔ** Forecast Placeها هستند — از جمله نقاط عادی مثل سربند.
- صفحهٔ جدا با namespaceهای `.point-page` / `.point-shell` / `.point-hero` **بازنشسته** شده است.

## ۴. ترتیب بخش‌ها (همان Destination)

۱. header  
۲. (اختیاری) CTA «بازگشت به مسیر …» فقط در slot اکشن hero (نه جایگزین sidebar)  
۳. hero تصویر + overlay + breadcrumb + عنوان + status/alert  
۴. day selector («انتخاب روز») + period toggle + **mobile route picker** (برای هر دو kind)  
۵. hourly forecast (کارت‌ها + legend؛ بدون نمایش `period.headline`)  
۶. جزئیات تخصصی (metrics) — همیشه همان `technical-card`؛ اگر متریک نبود EmptyState پایدار  
۷. sidebar مسیرهای مرتبط + decision card (و همان mobile route-picker برای هر دو kind)  
۸. footer مشترک محصول: «هوای مقصد، برنامهٔ مسیر»

برچسب مسیرها:

- destination: «مسیرهای منتهی به …»
- point: «مسیرهای عبوری از این نقطه»

## ۴٫۱ قرارداد API و URL

- قرارداد اول: `subject` / `hero` / `forecast.{days,period,current,hourly,meta}` / `metrics` / `decision` / `related_routes`
- aliasهای ریشه فقط سازگاری backend هستند؛ frontend از `forecast.*` می‌خواند
- URL تمیز بدون `date`/`period` می‌ماند تا کاربر صریحاً روز/بازه را عوض کند؛ بعد هر دو kind با هم sync می‌شوند
- `fromRoute` فقط برای دکمهٔ بازگشت است و planner مقصد/نقطه را seed نمی‌کند
- redirect قله (`/points/tochal_summit` → `/destination/touchal`) فقط `date` و `period` را نگه می‌دارد؛ `start_time`/`speed` وارد URL عمومی نمی‌شود

## ۵. stateها

loading / ready / empty / partial / error / stale — یکسان برای هر دو URL.  
timestamp خام ISO و `timing_pending` در متن UI نمایش داده نمی‌شود.

## ۶. acceptance

- [ ] `/points/sarband` و `/destination/touchal` از یک template و کلاس‌های destination shell استفاده می‌کنند
- [ ] dark/light و mobile/desktop بدون drift بصری بین دو URL
- [ ] بدون overflow افقی
- [ ] بدون کلاس/CSS اختصاصی point-page
- [ ] نقطهٔ مقصدی به destination canonical هدایت می‌شود

## ۷. تصویر مرجع

همان چهار تصویر Destination:

- [light/mobile](../screens/destination/light/mobile.png)
- [dark/mobile](../screens/destination/dark/mobile.png)
- [light/web](../screens/destination/light/web.png)
- [dark/web](../screens/destination/dark/web.png)

Fallback بدون تصویر تأیید‌شده: سطح گرادیان مستند (`destination-hero--fallback`) — asset جدید اضافه نمی‌شود.
