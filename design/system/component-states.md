# stateهای component و صفحه

## stateهای داده

- `loading`: skeleton یا placeholder با حفظ layout؛ از پرش محتوا جلوگیری شود.
- `ready`: دادهٔ معتبر با timestamp به‌روزرسانی و منبع/اعتبار مشخص.
- `empty`: پیام روشن، توضیح کوتاه و action جایگزین؛ کارت خالی بدون راهنما نمایش داده نشود.
- `error`: علت قابل فهم، retry و مسیر برگشت؛ خطا فقط با coral نشان داده نشود.
- `stale`: دادهٔ قدیمی با زمان آخرین به‌روزرسانی و هشدار ملایم مشخص شود.
- `partial-data`: بخش معتبر نمایش داده شود و قسمت ناقص با label و توضیح جدا بماند.

## stateهای تعاملی

- `default`: border و surface عادی.
- `hover`: تغییر محدود در border/surface و حرکت بسیار نرم.
- `focus-visible`: outline واضح و قابل مشاهده.
- `selected`: teal، متن خوانا و `aria-selected` یا `aria-pressed` متناسب.
- `disabled`: کم‌رنگ اما قابل تشخیص؛ بدون از بین‌بردن context.
- `pressed`: برای toggle و actionهای موقتی قابل بازشناسی.

## semantic weather states

- `normal`: teal؛ شرایط عادی.
- `change`: amber؛ تغییر مهم که نیاز به توجه دارد.
- `critical`: coral؛ نقطهٔ حساس یا ریسک جدی.

هر state باید حداقل با دو نشانه منتقل شود: رنگ + متن یا icon. Stateهای forecast باید در light و dark از نظر کنتراست و خوانایی بازبینی شوند.

