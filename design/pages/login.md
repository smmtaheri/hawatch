# مشخصات صفحهٔ Login (reference)

Login در درخواست جاری جزو صفحات forecast نیست؛ shell بصری آن برای navigation در دسترس است و flow واقعی احراز هویت همچنان خارج از scope است.

## ۱. هدف صفحه و تصمیم کاربر

Login برای ورود با شمارهٔ موبایل و دریافت کد ورود طراحی شده است. در این مرحله هدف ثبت reference بصری و فراهم‌کردن مسیر ورود است؛ احراز هویت واقعی در milestone اول implementation نمی‌شود.

## ۲. مسیر ورود و خروج

- ورود: کلیک «ورود» از Home، Destination یا Route.
- خروج موفق آینده: بازگشت به مقصدی که کاربر از آن آمده یا Home در صورت نبودن context.
- خروج دستی: کلیک برند برای Home یا back مرورگر.

## ۳. ترتیب دقیق بخش‌ها

۱. header با لوگو، theme toggle و وضعیت ورود.
۲. فضای آرام و خالی برای تمرکز.
۳. Login card.
۴. عنوان «ورود».
۵. input شمارهٔ موبایل با کد کشور.
۶. دکمهٔ «دریافت کد ورود».
۷. خطا یا راهنمای کوتاه در صورت نیاز.

## ۴. hierarchy کامپوننت‌ها

`LoginPage → PageShell → SiteHeader + LoginCard → LoginHeading + PhoneInput + RequestOtpButton + FeedbackMessage`.

## ۵. رفتار کنترل‌ها

- شمارهٔ موبایل: فقط فرمت معتبر موردنیاز را می‌پذیرد و خطا را نزدیک field نشان می‌دهد.
- دکمهٔ دریافت کد: در صورت معتبر بودن شماره، OTP flow آینده را شروع می‌کند.
- theme toggle و برند مانند سایر صفحه‌ها رفتار می‌کنند.
- در این milestone هیچ request، session یا OTP واقعی ساخته نمی‌شود.

## ۶. stateهای loading، ready، empty، error، stale و partial-data

- loading: دکمه disabled با label روشن.
- ready: input خالی یا مقدار کاربر و CTA فعال در صورت اعتبار.
- empty: راهنمای ورود شماره، نه خطای کلی صفحه.
- error: خطای validation یا ارسال کد با متن فارسی قابل اقدام.
- stale: کد منقضی‌شده در implementation آینده باید قابل درخواست دوباره باشد.
- partial-data: در صورت عدم دسترسی به profile، login موفق نباید به معنی شکست کل تجربه تلقی شود؛ رفتار redirect باز است.

## ۷. داده‌های موردنیاز

- شمارهٔ موبایل normalize‌شده.
- context بازگشت.
- state ارسال OTP و در آینده session/profile.

## ۸. APIهای آینده

- `POST /api/v1/auth/otp/request`
- `POST /api/v1/auth/otp/verify`
- `POST /api/v1/auth/logout`

قرارداد rate limit، expiry و روش session هنوز تصمیم‌گیری نشده است.

## ۹. تفاوت mobile و web

- mobile: card و input تقریباً تمام عرض امن viewport، بدون فشردگی و با CTA قابل لمس.
- web: card باریک‌تر و متمرکز، فضای اطراف بیشتر.
- هر دو حالت باید keyboard-friendly و بدون overflow باشند.

## ۱۰. تفاوت light و dark

- light: surface روشن روی زمینهٔ سبز-مه‌آلود.
- dark: surface آبی-سبز عمیق روی زمینهٔ dark، بدون black مطلق.
- focus و خطا در هر دو theme باید قابل مشاهده باشند.

## ۱۱. قواعد RTL و دسترسی‌پذیری

- label شماره و کد کشور از نظر RTL روشن باشند.
- autocomplete و input mode مناسب در implementation آینده انتخاب شود.
- خطا با متن، aria-live و نشانهٔ بصری اعلام شود.
- CTA حداقل hit area مناسب touch و focus keyboard داشته باشد.

## ۱۲. معیار پذیرش

- screenshotهای چهارگانه به‌عنوان reference ثبت شده و تغییر طراحی بدون تصمیم جدید انجام نشود.
- Login در milestone اول API، session یا OTP واقعی نداشته باشد؛ shell صفحه و navigation آن در دسترس باشد.
- جایگاه card، header، field و CTA در mobile/web و light/dark قابل مقایسه باشد.

## ۱۳. تصویر مرجع

- [light/mobile](../screens/login/light/mobile.png)
- [dark/mobile](../screens/login/dark/mobile.png)
- [light/web](../screens/login/light/web.png)
- [dark/web](../screens/login/dark/web.png)

## ۱۴. موارد نامشخص و تصمیم‌های باز

- OTP شش‌رقمی یا قالب دیگر، expiry و retry مشخص نشده است.
- session cookie یا token و نحوهٔ redirect نیازمند ADR جداست.
- نیاز واقعی به profile در milestoneهای اول هنوز معلوم نیست.
