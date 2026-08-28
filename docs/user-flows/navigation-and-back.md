# Flow: navigation و back

## قواعد

- کلیک برند: همیشه Home.
- Destination back: Home یا contextی که از آن آمده، با اولویت parent معنایی.
- Route back: Destination همان route.
- Point back: فقط وقتی `fromRoute` در navigation state باشد → همان Route؛ وگرنه بدون back گمراه‌کننده.
- breadcrumb Point: `مقصدها / {نام نقطه}` — بدون زنجیرهٔ مسیر.
- WeatherPoint نوع destination، مثل `tochal_summit`، صفحهٔ standalone جدا ندارد و به Destination canonical هدایت می‌شود.
- browser back: state قابل بازسازی باید تا حد امکان حفظ شود؛ Route queryهای برنامه‌ریزی را نگه می‌دارد.

## حالت‌های deep link

اگر کاربر مستقیم وارد `/destination/touchal` یا `/routes/touchal-darband` شد، صفحه باید بدون نیاز به Home context حداقلی را فراهم کند: نام مقصد، parent و back path.

Destination و Route با `date` و `period` کار می‌کنند و Route علاوه بر آن `start_time` و `speed` را در URL نگه می‌دارد. لینک Route به point عادی فقط `/points/{slug}` است؛ context کامل Route در `location.state.fromRoute` ذخیره می‌شود تا CTA بازگشت همان queryها را restore کند. لینک قلهٔ توچال به `/destination/touchal` می‌رود. ورود مستقیم یا refresh روی Point دکمهٔ بازگشت مسیر ندارد.
