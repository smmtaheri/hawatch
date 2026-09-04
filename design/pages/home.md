# مشخصات صفحهٔ Home

جزئیات استخراج‌شدهٔ read-only از سایت زنده در [بررسی live Home](../../docs/live-page-inspection/home.md) ثبت شده است؛ source محلی معرفی‌شده در handoff در این محیط در دسترس نبود.

## ۱. هدف صفحه و تصمیم کاربر

Home باید در چند ثانیه به کاربر بگوید هواچ برای دیدن هوای نقاط و برنامهٔ مسیر است. تصمیم اصلی کاربر انتخاب یک نقطهٔ هواشناسی برای بررسی است؛ از جست‌وجوی unified یا نقاط شاخص.

## ۲. مسیر ورود و خروج

- ورود: آدرس ریشهٔ محصول `/` یا لینک برند از هر صفحه.
- خروج اصلی: انتخاب نقطه → `/points/{weatherPointSlug}`.
- خروج ثانویه: کلیک روی «ورود» به Login reference.
- تغییر تم در همین صفحه باقی می‌ماند و انتخاب theme را برای session آینده نگه می‌دارد.

## ۳. ترتیب دقیق بخش‌ها

۱. header شامل لوگوی هواچ، ورود و theme toggle.
۲. hero copy با tagline «هوای مسیرت را ببین».
۳. جست‌وجوی unified (combobox): پیشنهاد نقطه‌های مسیر while typing؛ debounce ~۲۰۰ms؛ از ۲ کاراکتر.
۴. دکمهٔ «جست‌وجو» برای تکمیل جست‌وجوی unified.
۵. heading «نقاط شاخص».
۶. tileهای دسته‌بندی‌شدهٔ طبیعت: توچال، دماوند، دشت دریاسر، جنگل ابر، کویر مرنجاب و دریاچهٔ گهر.
۷. در صورت وجود نتیجهٔ جست‌وجو، نتیجه باید در همین ناحیه و بدون ایجاد overflow نمایش داده شود.

## ۴. hierarchy کامپوننت‌ها

`HomePage → SiteHeader + HeroCopy + SearchCombobox + SearchResultsList + PopularPoints → PointTile[]`.

## ۵. رفتار کنترل‌ها

- برند: لینک به Home و دارای accessible name.
- theme toggle: بین light و dark جابه‌جا می‌شود و state فعال را اعلام می‌کند.
- «ورود»: navigation به Login reference.
- input جست‌وجو: combobox با keyboard (↑↓ Enter Escape)، aria listbox؛ نتایج با type label (`نقطهٔ شاخص` / `نقطهٔ مسیر · {tile}`).
- دکمهٔ «جست‌وجو» و Enter هر دو همان endpoint unified را مصرف می‌کنند؛ با highlight انتخاب می‌کنند، با یک نتیجه مستقیم navigate می‌کنند و با چند نتیجه فهرست unified را نشان می‌دهند.
- در خطای جست‌وجو، پیام خطا و امکان retry نمایش داده می‌شود و متن ورودی حفظ می‌شود.
- point tile: به صفحهٔ نقطه متناسب با slug می‌رود.
- category tile: در milestone اول در همان point search یا catalog resolve می‌شود؛ semantics نهایی category هنوز باز است.

## ۶. stateهای loading، ready، empty، error، stale و partial-data

- loading: هنگام resolve نقطه، action و layout ثابت بمانند و tileها skeleton داشته باشند.
- ready: نقاط شاخص و نتیجهٔ جست‌وجو با نام و category نمایش داده شوند.
- empty: برای query ناشناخته پیام کوتاه و پیشنهاد جست‌وجوی دوباره یا انتخاب محبوب نشان داده شود.
- error: خطای catalog/search با retry و حفظ input نمایش داده شود.
- stale: اگر catalog محلی از آخرین sync قدیمی است، وضعیت به‌صورت کم‌اهمیت مشخص شود؛ Home نباید بی‌دلیل مسدود شود.
- partial-data: اگر category یا icon نقطه موجود نیست، نام نقطه و action حفظ و field ناقص label شود.

## ۷. داده‌های موردنیاز

- query جست‌وجو و normalized query.
- catalog نقطه‌ها: slug، نام، category، icon/asset، مختصات تأییدشده و وضعیت فعال‌بودن.
- فهرست نقاط شاخص با ترتیب محصول.
- theme فعلی و ترجیح کاربر.

## ۸. API و دادهٔ فعلی

- `GET /api/v1/points/` برای catalog نقطه‌ها.
- `GET /api/v1/search/suggestions/?q={query}` برای پیشنهادهای unified نقطه‌ها، با حداقل دو کاراکتر و تطبیق prefix.
- لینک نقطه به `/points/{weatherPointSlug}` می‌رود.

Home هرگز مستقیماً به provider هواشناسی وصل نمی‌شود؛ فقط catalog داخلی را مصرف می‌کند.

## ۹. تفاوت mobile و web

- mobile: hero به‌صورت عمودی، search input و button در ردیف/چیدمان جدا با فاصلهٔ امن؛ tileها دو ستونه یا stack خوانا.
- web: hero فضای بازتر و tileهای نقطه در یک ردیف فشرده‌تر؛ تصویر زمینه و whitespace بخش مهم composition هستند.
- در هر دو، کل صفحه نباید overflow افقی داشته باشد.

## ۱۰. تفاوت light و dark

- light: زمینهٔ مه‌آلود روشن، متن ink، tileهای نیمه‌شفاف روشن و teal برند.
- dark: زمینهٔ آبی-سبز عمیق، متن روشن، tileهای تیرهٔ شفاف و teal روشن.
- overlay hero و contrast متن باید در هر دو theme مستقل بازبینی شود.

## ۱۱. قواعد RTL و دسترسی‌پذیری

- root و متن‌ها RTL؛ برای اعداد، ساعت و واحدها نمایش خوانا و مستقل از جهت متن بررسی شود.
- input label قابل دسترس، submit با Enter و focus-visible برای همهٔ tileها.
- tile فقط با icon شناخته نشود؛ نام و category متناظر داشته باشد.
- theme toggle باید label و state قابل فهم برای screen reader داشته باشد.

## ۱۲. معیار پذیرش

- کاربر بتواند با input یا tile به نقطه برسد.
- در mobile دکمه روی input نیفتد.
- هیچ scrollbar افقی در viewport ایجاد نشود.
- چهار حالت reference از نظر ترتیب، رنگ، spacing و typography قابل مقایسه باشند؛ صفحهٔ Point از همان سیستم بصری مشترک استفاده می‌کند.
- empty و error، input کاربر را از بین نبرند.
- Home هیچ دادهٔ forecast را مستقیم از provider دریافت نکند.

## ۱۳. تصویر مرجع

- [light/mobile](../screens/home/light/mobile.png)
- [dark/mobile](../screens/home/dark/mobile.png)
- [light/web](../screens/home/light/web.png)
- [dark/web](../screens/home/dark/web.png)

## ۱۴. موارد نامشخص و تصمیم‌های باز

- رفتار category tile در برابر نتیجهٔ چند نقطه باید مشخص شود.
- منبع و cadence به‌روزرسانی catalog نقطه‌ها هنوز تعیین نشده است.
- جست‌وجوی fuzzy در این نسخه قرارداد ندارد؛ جست‌وجو prefix و normalize‌شده است.
- ماندگاری theme بین sessionها هنوز قرارداد محصولی مستقلی ندارد.
