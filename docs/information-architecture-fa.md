# معماری اطلاعات هواچ

## نقشهٔ سطح بالا

```text
Home /
├── Destination /destination/{destinationSlug}
│   └── Route /routes/{routeSlug}
├── Point (canonical) /points/{weatherPointSlug}
├── Login /login (reference؛ خارج از milestone اول)
└── Share /share (آینده)
```

## context و مالکیت داده

- **Destination** مالک catalog مقصد، مختصات تأییدشده، forecast مقصد و فهرست routeهای مرتبط است.
- **WeatherPoint** هویت canonical نقطهٔ هواشناسی مستقل است؛ `/points/{slug}`.
- **Route** مالک ترتیب نقاط، زمان‌بندی، speed profile و forecast متناسب با زمان عبور از نقطه است.
- **Weather data** در backend آینده normalize می‌شود؛ UI نباید provider response خام را مصرف کند.
- **Share** باید payload کمینه و قابل بازسازی route plan را نگه دارد؛ جزئیات ماندگاری باز است.

## navigation rules

- برند همیشه Home است.
- breadcrumb روی Destination و Route context را حفظ می‌کند.
- back در mobile باید به parent معنایی برگردد، نه فقط به آخرین URL تصادفی.
- تغییر theme global است اما day، period، route و plan context را reset نمی‌کند.
- destination slug و route slug باید پایدار و قابل استفاده در لینک باشند.

