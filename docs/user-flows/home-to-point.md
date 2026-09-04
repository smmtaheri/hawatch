# Flow: Home تا Point

## مسیر اصلی

```text
Home
  → autocomplete نقطه/نقطه یا انتخاب نقطه محبوب
  → resolve slug
  → Point (/points/{slug}) یا Point (/points/{slug})
  → نمایش forecast
```

## حالت‌های جایگزین

- query بدون نتیجه: input حفظ شود، empty message و نقاطی محبوب نمایش داده شوند.
- query چند نتیجه: کاربر باید فهرست قابل تمایز بر اساس نام و category ببیند.
- catalog unavailable: Home قابل استفاده بماند و retry ارائه شود.
- نقطه inactive یا unknown در URL: پیام not found با بازگشت به Home.

## معیار flow

کاربر باید بدون دانستن slug بتواند نقطه را انتخاب کند و بعد از ورود به Point، نام نقطه، وضعیت فعلی و مسیرهای قابل بررسی را ببیند.
