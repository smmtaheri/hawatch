# Flow: navigation و back

## قواعد

- کلیک برند: همیشه Home.
- Destination back: Home یا contextی که از آن آمده، با اولویت parent معنایی.
- Route back: Destination همان route.
- breadcrumb: context قابل فهم؛ current page لینک نیست.
- browser back: state قابل بازسازی باید تا حد امکان حفظ شود.

## حالت‌های deep link

اگر کاربر مستقیم وارد `/destination/touchal` یا `/routes/touchal-darband` شد، صفحه باید بدون نیاز به Home context حداقلی را فراهم کند: نام مقصد، parent و back path.

رفتار query برای date، period، start و speed در implementation آینده باید در یک قرارداد navigation ثبت شود.

