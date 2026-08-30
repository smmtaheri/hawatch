# فهرست componentها

## shell و navigation

- `SiteHeader`: برند/لوگو، ورود و تغییر تم.
- `BrandLogo`: wordmark کامل + mark رسمی؛ در dark از `hawatch-logo-light.svg` و در light از `hawatch-logo-dark.svg` استفاده می‌کند.
- `ThemeToggle`: تغییر light/dark با label و state فعال.
- `Breadcrumb`: context مقصد و مسیر.
- `BackNavigation`: دکمهٔ بازگشت ساده به صفحهٔ قبلی با fallback به Home در ورود مستقیم.

## Home

- `HeroCopy`: tagline و معرفی تصمیم.
- `SearchCombobox`: autocomplete مقصد و WeatherPoint؛ keyboard و debounce.
- `PopularDestinations`: heading و grid مقصدهای محبوب.
- `DestinationTile`: نام، دستهٔ طبیعت، icon و navigation.
- `SearchResultsList`: فهرست unified نتیجه‌های مقصد و نقطه بعد از submit.

## Login reference

- `LoginCard`: surface متمرکز فرم.
- `PhoneInput`: کد کشور و شمارهٔ موبایل.
- `RequestOtpButton`: اقدام اصلی دریافت کد ورود.

## Destination / Forecast Place

- `PlaceForecastPage`: قالب مشترک `/destination/:slug` و `/points/:slug`.
- `DestinationHero`: تصویر (یا fallback سطح)، عنوان، breadcrumb و وضعیت فعلی.
- `StatusPill`: حالت عادی یا تغییر مهم.
- `DayTabs`: انتخاب روز؛ دیروز کم‌رنگ‌تر از امروز.
- `RoutePicker` / related routes card: مسیرهای مرتبط با عنوان متناسب kind.
- `PeriodToggle`: صبح/بعدازظهر/شب؛ period کاملاً گذشته dim می‌شود.
- `HourlyForecast`: چهار کارت دوساعته در هر بازه و legend وضعیت.
- `TechnicalMetrics`: grid جزئیات تخصصی با `SpecialistMetricIcon` و sprite رسمی شاخص‌ها.
- `DecisionCard`: تفسیر قابل اقدام از forecast.

## Route

- `RouteHero`: نام مسیر، مقصد parent و هشدار برجسته.
- `SiblingRouteNav`: مسیرهای دیگر همان مقصد.
- `DayPicker`: انتخاب روز.
- `StartTimeGauge`: بازه و slider ساعت شروع (RTL، step پیکربندی‌شده).
- `SpeedSegmentedControl`: آرام/متوسط/سریع.
- `RoutePointAxis`: نقاط مسیر روی یک محور.
- `PointWeatherCard` / route point weather cards: خلاصهٔ رسیدن‌محور؛ وقتی timing pending، حالت «زمان‌بندی در دسترس نیست».
- `RouteDecisionCard`: زمان رسیدن، نقطهٔ حساس و پیشنهاد تصمیم.
- `ShareActions`: کپی لینک و اشتراک‌گذاری.
- `RouteStats`: مسافت، صعود، زمان و زمان رسیدن.
- `RoutePointSummaryGrid`: خلاصهٔ point-level برای هر نقطه.
- `RouteTimeline`: بدون دمای تکراری زیر marker.

## Point

قالب جداگانه ندارد؛ به Forecast Place مراجعه شود. `design/pages/point.md` فقط redirect مستند است.
