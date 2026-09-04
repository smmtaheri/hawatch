# Flow: navigation و back

## قواعد

- کلیک برند: همیشه Home.
- Point back: Home یا contextی که از آن آمده، با اولویت parent معنایی.
- Route back: Point همان route.
- Point back: فقط وقتی `fromRoute` در navigation state باشد → همان Route؛ وگرنه بدون back گمراه‌کننده.
- breadcrumb Point: `نقاط / {نام نقطه}` — بدون زنجیرهٔ مسیر.
- WeatherPoint شاخص، مثل `tochal`، از ابتدا با لینک canonical `/points/tochal`
  نمایش داده می‌شود.
- sidebar نقطه حذف نمی‌شود حتی اگر از Route آمده باشد.
- browser back: state قابل بازسازی باید تا حد امکان حفظ شود؛ Route queryهای برنامه‌ریزی را نگه می‌دارد.

## حالت‌های deep link

اگر کاربر مستقیم وارد `/points/tochal` یا `/routes/tochal-darband` شد، صفحه باید بدون نیاز به Home context حداقلی را فراهم کند: نام نقطه، parent و back path.

Point و Route با `date` و `period` کار می‌کنند و Route علاوه بر آن `start_time` و `speed` را در URL نگه می‌دارد. لینک Route به point عادی فقط `/points/{slug}` است؛ context کامل Route در `location.state.fromRoute` ذخیره می‌شود تا CTA بازگشت همان queryها را restore کند. لینک قلهٔ توچال به `/points/tochal` می‌رود. ورود مستقیم یا refresh روی Point دکمهٔ بازگشت مسیر ندارد.
