# رنگ‌ها

رنگ در هواچ فقط تزئینی نیست؛ برای انتقال وضعیت و کمک به تصمیم استفاده می‌شود. teal وضعیت عادی و اقدام اصلی را نشان می‌دهد، amber تغییر مهم را و coral نقطهٔ حساس یا هشدار را.

## رنگ‌های برند

| token | مقدار | کاربرد |
| --- | --- | --- |
| `brand.ink` | `#102b3d` | متن اصلی و کنتراست در light |
| `brand.teal` | `#1d7f86` | هویت، لینک، CTA و انتخاب فعال در light |
| `brand.tealBright` | `#61c5c0` | teal در dark و accent روشن |
| `brand.mist` | `#e5efec` | زمینهٔ مه‌آلود و سطح نرم |
| `brand.line` | `#cbdedb` | خطوط ظریف |
| `brand.muted` | `#62777a` | متن کم‌اهمیت |
| `brand.amber` | `#d09a35` | تصمیم و تغییر مهم |
| `brand.coral` | `#d9584c` | هشدار و وضعیت حساس |

## light و dark

light باید روشن، طبیعی و غیراداری باشد؛ سفید خالص فقط برای surfaceهای مشخص استفاده می‌شود. در runtime live، زمینهٔ دیده‌شدهٔ shell/hero حدود `#c9dcda` است و page token داخلی light نیز `#f0f6f4` را برای لایهٔ محتوای light تعریف می‌کند. dark باید عمیق و آرام باشد، اما مشکی کامل نباشد؛ زمینهٔ pageهای محتوایی `#0b2732` و زمینهٔ Home حدود `#071d28` مشاهده شد.

سطح‌ها در هر theme از `background`، `surface`، `surfaceRaised` و `surfaceSoft` تشکیل می‌شوند. borderها ظریف‌اند و نباید به خطوط سنگین یا grid بصری غالب تبدیل شوند.

## قواعد کاربرد

- رنگ باید همراه با label، icon یا متن باشد؛ وضعیت فقط با رنگ منتقل نشود.
- teal برای دادهٔ عادی، انتخاب فعال، لینک و اقدام اصلی است.
- amber برای «تغییر مهم» و تصمیم نیازمند توجه است، نه خطای قطعی.
- coral برای «نقطهٔ حساس»، احتیاط و وضعیت پرریسک است.
- در dark از نسخه‌های روشن‌تر semantic استفاده شود تا کنتراست با surface حفظ شود.
- عکس‌های hero باید با overlay خوانایی متن را حفظ کنند.

مقادیر runtime، ابعاد و selectorهای مشاهده‌شده در [بررسی live Home](../../docs/live-page-inspection/home.md)، [بررسی live Destination](../../docs/live-page-inspection/destination.md) و [بررسی live Route](../../docs/live-page-inspection/route.md) ثبت شده‌اند.
