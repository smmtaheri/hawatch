# رفتار Home

## قرارداد تعامل

- `/` نقطهٔ ورود محصول است.
- search با submit فرم و Enter فعال می‌شود.
- query باید trim و normalize شود و input پس از خطا حفظ بماند.
- نتیجهٔ مقصد با slug داخلی به Destination می‌رود.
- مقصد محبوب مستقیم به route مقصد لینک می‌شود.
- theme toggle global است.

## mobile و overflow

input و button نباید روی هم قرار بگیرند. grid مقصدها باید با عرض viewport سازگار باشد و root scrollbar افقی نداشته باشد. اگر تعداد نتیجه‌ها زیاد است، overflow فقط داخل result container و با label قابل فهم مجاز است.

## observability آینده

eventهای احتمالی: `destination_search_submitted`، `popular_destination_selected` و `theme_changed`. نام‌گذاری و حریم خصوصی باید پیش از instrumentation تصویب شود.

