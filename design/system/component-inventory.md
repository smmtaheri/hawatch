# فهرست componentها

## shell و navigation

- `SiteHeader`: برند/لوگو، ورود و تغییر تم.
- `BrandMark`: دو خط صعودی و سه نقطه؛ لینک خانه.
- `ThemeToggle`: تغییر light/dark با label و state فعال.
- `Breadcrumb`: context مقصد و مسیر.
- `MobileBackLink`: بازگشت به context قبلی در mobile.

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
- `TechnicalMetrics`: grid جزئیات تخصصی.
- `DecisionCard`: تفسیر قابل اقدام از forecast.
- `RouteBackLink`: CTA بازگشت به Route (فقط با navigation state)؛ مشترک بین destination و point.

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
