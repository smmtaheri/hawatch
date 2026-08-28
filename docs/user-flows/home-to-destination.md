# Flow: Home تا Destination

## مسیر اصلی

```text
Home
  → autocomplete مقصد/نقطه یا انتخاب مقصد محبوب
  → resolve slug
  → Destination (/destination/{slug}) یا Point (/points/{slug})
  → نمایش forecast
```

## حالت‌های جایگزین

- query بدون نتیجه: input حفظ شود، empty message و مقصدهای محبوب نمایش داده شوند.
- query چند نتیجه: کاربر باید فهرست قابل تمایز بر اساس نام و category ببیند.
- catalog unavailable: Home قابل استفاده بماند و retry ارائه شود.
- مقصد inactive یا unknown در URL: پیام not found با بازگشت به Home.

## معیار flow

کاربر باید بدون دانستن slug بتواند مقصد را انتخاب کند و بعد از ورود به Destination، نام مقصد، وضعیت فعلی و مسیرهای قابل بررسی را ببیند.

