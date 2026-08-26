# Flow: Destination تا Route

```text
Destination
  → انتخاب مسیر از بخش «مسیرها»
  → Route با مقصد parent و route slug
  → مشاهدهٔ نقاط مسیر و وضعیت هوا
```

مسیر انتخابی باید از نظر نام، origin و destination برای کاربر واضح باشد. Route باید امکان برگشت مستقیم به Destination و انتخاب مسیر دیگر همان مقصد را حفظ کند.

اگر route data ناقص باشد، catalog route و علت نقص جدا نمایش داده شوند؛ صفحه نباید با دادهٔ ساختگی تصمیم قطعی بسازد.

