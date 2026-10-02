# فهرست componentها

## shell و navigation

- `SiteHeader`: برند/لوگو، ورود و تغییر تم.
- `Logo`: نشان خطی ابر و کوه از `brandMark.svg` با `currentColor`؛ در HTML اولیهٔ SSR نسخه‌های عمومی هم‌هندسهٔ `brand/v2/logo-light.svg` و `brand/v2/logo-dark.svg` نمایش داده می‌شوند.
- `ThemeToggle`: تغییر light/dark با label و state فعال.
- `Breadcrumb`: context نقطه و مسیر.
- `BackNavigation`: دکمهٔ بازگشت ساده به صفحهٔ قبلی با fallback به Home در ورود مستقیم.

## Home

- `HeroCopy`: tagline و معرفی تصمیم.
- `SearchCombobox`: autocomplete نقطه و WeatherPoint؛ keyboard و debounce.
- `PopularPoints`: heading و grid نقاط شاخص.
- `PointTile`: نام، دستهٔ طبیعت، icon و navigation.
- `SearchResultsList`: فهرست unified نتیجه‌های نقطه بعد از submit.

## ورود

- `LoginOverlay`: route-backed layer؛ تمام‌صفحه در mobile و dialog متمرکز در desktop.
- `PhoneInput`: کد کشور و شمارهٔ موبایل با input واقعی و جهت LTR.
- `RequestOtpButton`: CTA دریافت کد؛ تا آماده‌شدن API disabled و همراه علت.
- `OtpCodeInput` (آینده): پنج خانهٔ بصری روی یک input واقعی برای paste و SMS autofill.

## Point Forecast

- `PlaceForecastPage`: قالب `/points/:slug`.
- `PointHero`: تصویر (یا fallback سطح)، عنوان، breadcrumb و وضعیت فعلی.
- `StatusPill`: حالت عادی یا تغییر مهم.
- `DayTabs`: انتخاب روز؛ دیروز کم‌رنگ‌تر از امروز.
- `RoutePicker` / related routes card: مسیرهای مرتبط با عنوان متناسب kind.
- `PeriodToggle`: بامداد/صبح/ظهر/شب؛ period کاملاً گذشته dim می‌شود.
- `HourlyForecast`: سه کارت دوساعته در هر بازه و legend وضعیت.
- `TechnicalMetrics`: grid جزئیات تخصصی با `SpecialistMetricIcon` و sprite رسمی شاخص‌ها. هشت نام معنایی (`wind-average`، `wind-gust`، `visibility`، `freezing-level`، `cloud-base`، `uv-index`، `precipitation` و `sunrise-sunset`) فقط از `apps/web/public/icons/specialist/` می‌آیند؛ اندازهٔ پایه ۲۴px و داخل metric card برابر ۲۸px است.
- `DecisionCard`: تفسیر قابل اقدام از forecast.

## Route

- `RouteHero`: نام مسیر، نقطهٔ target و هشدار برجسته.
- `SiblingRouteNav`: مسیرهای دیگر متصل به همان نقطه.
- `DayPicker`: انتخاب روز.
- `StartTimeGauge`: بازه و slider ساعت شروع (RTL، step پیکربندی‌شده).
- `SpeedSegmentedControl`: آرام/متوسط/سریع.
- `RoutePointAxis`: نقاط مسیر روی یک محور.
- `PointWeatherCard` / route point weather cards: خلاصهٔ رسیدن‌محور؛ وقتی timing pending، حالت «زمان‌بندی در دسترس نیست».
- `RouteDecisionCard`: زمان رسیدن، نقطهٔ حساس و پیشنهاد تصمیم.
- `ShareActions`: کپی لینک و اشتراک‌گذاری.
- `GearIcon` / `GearRecommendations`: آیکون‌های معنایی تجهیزات از
  `apps/web/public/icons/gear/` و نام وسیله‌های پیشنهادی در پایین share card؛
  متن recommendation در این بخش نمایش داده نمی‌شود.
- `RouteStats`: مسافت، صعود، زمان و زمان رسیدن.
- `RoutePointSummaryGrid`: خلاصهٔ point-level برای هر نقطه.
- `RouteTimeline`: بدون دمای تکراری زیر marker.

## Point

قالب جداگانه ندارد؛ از Point Forecast مشترک استفاده می‌کند. همهٔ نقطه‌ها از مسیر
canonical خودشان لینک می‌شوند.
