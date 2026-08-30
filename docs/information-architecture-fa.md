# معماری اطلاعات هواچ

## نقشهٔ سطح بالا

```text
Home /
├── Forecast Place (قالب مشترک)
│   ├── Destination role  /destination/{destinationSlug}
│   └── Point role        /points/{weatherPointSlug}
│       └── (اگر profile مقصد دارد → redirect به Destination)
├── Route /routes/{routeSlug}
├── Login /login (reference؛ خارج از milestone اول)
└── Share /share (آینده)
```

## context و مالکیت داده

- **WeatherPoint** حقیقت فیزیکی است: مختصات، ارتفاع، aliases، forecast.
- **Destination** نقش عمومی/محصولی صفر یا یک روی یک WeatherPoint است (slug عمومی، hero، محبوبیت) — نه موجودیت فیزیکی جدا.
- **Route** مجموعهٔ مرتب WeatherPointهاست با `origin_weather_point` و `target_weather_point`.
- **RoutePoint** فقط عضویت مسیر‌محور است: ترتیب و timing، `public_note` کوتاهِ تأییدشده برای UI، و `internal_note` برای evidence داخلی. `internal_note` هرگز public نمی‌شود.
- **Weather data** در backend normalize می‌شود؛ UI فقط envelope داخلی را مصرف می‌کند.

## navigation rules

- برند همیشه Home است.
- `/destination/*` و `/points/*` یک قالب React مشترک (`PlaceForecastPage`) دارند.
- تغییر theme global است اما day/period/route context را reset نمی‌کند.
- slugها پایدار و قابل اشتراک‌اند.
