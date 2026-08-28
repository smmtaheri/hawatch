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

## Login reference

- `LoginCard`: surface متمرکز فرم.
- `PhoneInput`: کد کشور و شمارهٔ موبایل.
- `RequestOtpButton`: اقدام اصلی دریافت کد ورود.

## Destination

- `DestinationHero`: تصویر، عنوان، breadcrumb و وضعیت فعلی.
- `StatusPill`: حالت عادی یا تغییر مهم.
- `DayTabs`: انتخاب روز؛ دیروز کم‌رنگ‌تر از امروز.
- `RoutePicker`: انتخاب مسیرهای همان مقصد.
- `DaypartToggle`: صبح/بعدازظهر.
- `HourlyForecast`: شش کارت ساعتی و legend وضعیت.
- `TechnicalMetrics`: grid جزئیات تخصصی.
- `DecisionCard`: تفسیر قابل اقدام از forecast.

## Route

- `RouteHero`: نام مسیر، مقصد parent و هشدار برجسته.
- `SiblingRouteNav`: مسیرهای دیگر همان مقصد.
- `DayPicker`: انتخاب روز.
- `StartTimeGauge`: بازه و slider ساعت شروع.
- `SpeedSegmentedControl`: آرام/متوسط/سریع.
- `RoutePointAxis`: نقاط مسیر روی یک محور.
- `PointWeatherCard`: وضعیت متناظر با هر نقطه.
- `RouteDecisionCard`: زمان رسیدن، نقطهٔ حساس و پیشنهاد تصمیم.
- `ShareActions`: کپی لینک و اشتراک‌گذاری.
- `RouteStats`: مسافت، صعود، زمان و زمان رسیدن.

## Point (extension از Destination)

- `PointHero`: breadcrumb، نام، مختصات، status pill.
- `PointRouteBackLink`: CTA بازگشت به Route (فقط با navigation state).
- `PointWeatherCard`: day/period، current reading، hourly — بدون planner.
- `RelatedRoutesCard`: مسیرهای مرتبط وقتی standalone.

