# معماری اطلاعات هواچ

## نقشهٔ سطح بالا

```text
Home /
├── Points /points/{pointSlug}
│   └── WeatherPoint با پروفایل و forecast خودش؛ مسیرهای مرتبط
├── Route /routes/{routeSlug}
├── Login /login?returnTo=... (route-backed overlay؛ ورود آزمایشی شمارهٔ مجاز و کد ثابت)
└── Share /share (آینده)
```

## context و مالکیت داده

- **WeatherPoint** تنها موجودیت نقطه است و هم‌زمان حقیقت فیزیکی، هویت عمومی، پروفایل و forecast را نگه می‌دارد؛ `kind=primary|route_point|shared` فقط ویژگی همین رکورد است.
- **Route** مجموعهٔ مرتب WeatherPointهاست با `origin_weather_point` و `target_weather_point`.
- **RoutePoint** فقط عضویت مسیر‌محور است: ترتیب و timing، `public_note` کوتاهِ تأییدشده برای UI، و `internal_note` برای evidence داخلی. `internal_note` هرگز public نمی‌شود.
- **Weather data** در backend normalize می‌شود؛ UI فقط envelope داخلی را مصرف می‌کند.

## navigation rules

- برند همیشه Home است.
- همهٔ `/points/*`ها یک قالب React مشترک (`PlaceForecastPage`) دارند.
- تغییر theme global است اما day/period/route context را reset نمی‌کند.
- slugها پایدار و قابل اشتراک‌اند.
