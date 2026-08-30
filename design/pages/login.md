# مشخصات ورود هواچ

## هدف و محدودهٔ فعلی

ورود از هر صفحهٔ عمومی آغاز می‌شود، اما کاربر نباید از صفحه‌ای که در آن برنامه‌ریزی می‌کرد جدا شود. در این نسخه فقط UI ورود آماده است؛ API احراز هویت، ارسال پیامک، session و OTP واقعی هنوز وجود ندارند. به همین دلیل CTA دریافت کد عمداً disabled است و پیام «ورود پیامکی هنوز فعال نشده است.» را نشان می‌دهد.

## الگوی نمایش

- کلیک عادی روی «ورود»: URL به `/login?returnTo={current-path-and-query}` تغییر می‌کند و route قبلی زیر لایهٔ ورود حفظ می‌شود.
- موبایل: لایهٔ ورود تمام‌صفحه، با backdrop محوِ صفحهٔ قبلی، logo و دکمهٔ بستن مستقل است.
- دسکتاپ: dialog جمع‌وجور و متمرکز روی backdrop محو نمایش داده می‌شود.
- ورود مستقیم یا refresh روی `/login`: همان فرم به‌صورت صفحهٔ کامل render می‌شود تا URL، Back و refresh پایدار بمانند.
- بستن با ×، backdrop (فقط dialog)، Escape یا Back مرورگر کاربر را به همان صفحه و query قبلی برمی‌گرداند. `returnTo` فقط مسیر داخلی امن می‌پذیرد.

## ترتیب محتوا

۱. لوگوی هواچ و بستن.
۲. برچسب «ورود امن».
۳. عنوان «ورود به هواچ» و توضیح کوتاه.
۴. نشانگر دو مرحله‌ای؛ مرحلهٔ شمارهٔ موبایل فعال است.
۵. label، کد `+98` و یک input شمارهٔ موبایل با `type=tel` و `autocomplete=tel`.
۶. CTA «دریافت کد ورود» و پیام واضحِ غیرفعال بودن سرویس.

## جریان آیندهٔ OTP

بعد از افزوده‌شدن API:

۱. شمارهٔ موبایل معتبر → `POST /api/v1/auth/otp/request`.
۲. انتقال به مرحلهٔ کد پیامکی.
۳. OTP باید پنج خانهٔ بصری داشته باشد، اما فقط **یک input واقعی** پشت آن قرار بگیرد تا paste و SMS autofill درست کار کنند.
۴. `POST /api/v1/auth/otp/verify` → ایجاد session → `navigate(returnTo)` و ادامهٔ عملی که کاربر پیش از ورود آغاز کرده بود.

validation، rate limit، expiry، retry و قرارداد session قبل از فعال‌شدن CTA باید مشخص و تست شوند؛ UI فعلی هیچ‌یک را شبیه‌سازی نمی‌کند.

## دسترسی‌پذیری و RTL

- dialog در حالت overlay دارای `role=dialog`، `aria-modal` و title قابل‌ارجاع است.
- focus اولیه روی dialog قرار می‌گیرد؛ Escape آن را می‌بندد و اسکرول body تا بسته‌شدن آن قفل است.
- شماره با جهت LTR و بقیهٔ محتوا RTL است.
- close، field و CTA focus-visible قابل مشاهده دارند. CTA disabled علتِ غیرفعال بودن سرویس را با متن در دسترس اعلام می‌کند.

## حالت‌های visual

- dark: surface سبزـآبی عمیق، backdrop تیره و blur.
- light: surface روشن و سایهٔ ملایم، با همان hierarchy و رنگ accent.
- mobile: edge-to-edge، بدون popup کوچک و با safe area.
- desktop: حداکثر عرض ۴۶۰px، بدون شلوغی صفحهٔ مستقل در ورود عادی.

## تصاویر مرجع

تصاویر اولیهٔ login برای compatibility همچنان حفظ شده‌اند:

- [light/mobile](../screens/login/light/mobile.png)
- [dark/mobile](../screens/login/dark/mobile.png)
- [light/web](../screens/login/light/web.png)
- [dark/web](../screens/login/dark/web.png)

مرجع‌های تازهٔ flow (داده‌شده توسط محصول و بدون بازفشرده‌سازی) مسیر overlay و مرحلهٔ آیندهٔ OTP را ثبت می‌کنند:

- [mobile phone step](../screens/login/reference/mobile-phone-step.png)
- [mobile OTP step](../screens/login/reference/mobile-otp-step.png)

## معیار پذیرش

- Login از Home، Place و Route یک overlay باز کند، نه صفحهٔ مستقل عادی.
- موبایل تمام‌صفحه و desktop dialog متمرکز باشد.
- URL مستقیم `/login?returnTo=...` قابل refresh و بستن باشد.
- هیچ request یا ورود ساختگی تا آماده‌شدن backend انجام نشود؛ عدم فعال‌بودن OTP قابل مشاهده باشد.
- OTP آینده یک input واقعی و پنج خانهٔ نمایشی خواهد داشت.
