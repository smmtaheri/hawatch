# بررسی read-only صفحهٔ Home

زمان بررسی: 2026-08-25. URL: `https://hawatch-weather.admirer135.chatgpt.site/`

برچسب منابع: `[LIVE]` یعنی DOM/رفتار سایت زنده، `[LIVE-BUNDLE]` یعنی asset JavaScript/CSS منتشرشدهٔ همان سایت، `[SCREENSHOT]` یعنی تصویر مرجع repository، `[PRODUCT]` یعنی درخواست صریح محصول، `[BLOCKED]` یعنی منبع معرفی‌شده در دسترس نبود.

## ۱. بخش‌های قابل مشاهده و ترتیب

ترتیب در هر چهار حالت live یکسان است:

۱. `site-header`: برند «هواچ»، لینک «ورود»، و theme toggle.
۲. hero copy با متن «هوای مسیرت را ببین».
۳. فرم `search-box` شامل input و CTA «جست‌وجو».
۴. heading مقصدها که در حالت عادی «مقصدهای محبوب» و پس از جست‌وجو «نتایج مرتبط» است.
۵. grid مقصدها؛ در حالت عادی شش tile: توچال، دماوند، دشت دریاسر، جنگل ابر، کویر مرنجاب، دریاچه گهر.

[LIVE] فقط `home-hero` در main وجود دارد و Home footer یا section جداگانهٔ دیگری ندارد.

## ۲. متن‌ها، عنوان‌ها، labelها و CTAها

| عنصر | متن دقیق |
| --- | --- |
| document title | `هواچ &#124; هوای مقصد، برنامهٔ مسیر` |
| description | `هواچ؛ هوای مسیرت را ببین.` |
| brand aria-label | `هواچ، خانه` |
| header link | `ورود` |
| theme dark | `☼ روشن` |
| theme light | `◐ تیره` |
| hero eyebrow | `هوای مسیرت را ببین` |
| search aria-label | `جست‌وجوی مقصد` |
| search placeholder | `مثلاً توچال، دماوند یا دریاسر` |
| search CTA | `جست‌وجو` |
| default heading | `مقصدهای محبوب` |
| search heading | `نتایج مرتبط` |
| empty result | `مقصد مرتبطی پیدا نشد؛ نام مقصد دیگری را امتحان کن.` |
| result hint | `برای دیدن پیش‌بینی، روی مقصد موردنظرت بزن.` |

نام و category tileها: `توچال / کوه`، `دماوند / آتشفشان`، `دشت دریاسر / دشت`، `جنگل ابر / جنگل`، `کویر مرنجاب / کویر`، `دریاچه گهر / دریاچه`. [LIVE-BUNDLE]

## ۳. لینک‌ها و navigation

| متن | href |
| --- | --- |
| هواچ | `/` |
| ورود | `/login` |
| توچال | `/destination/touchal` |
| دماوند | `/destination/damavand` |
| دشت دریاسر | `/destination/daryasar` |
| جنگل ابر | `/destination/jangal-abr` |
| کویر مرنجاب | `/destination/maranjab` |
| دریاچه گهر | `/destination/gahar` |

هر tile یک icon طبیعت و arrow `←` نیز دارد. [LIVE]

## ۴. رفتار کنترل‌ها

- برند به Home برمی‌گردد.
- «ورود» به `/login` می‌رود.
- theme toggle با کلیک، `data-theme` و `color-scheme` را عوض می‌کند و مقدار `hawatch-theme` را در localStorage می‌نویسد. [LIVE-BUNDLE]
- input با `onChange` مقدار را تغییر می‌دهد و search result visibility را reset می‌کند.
- search مقدار را trim و به lowercase تبدیل می‌کند و `ي/ی` و `ك/ک` را normalize می‌کند؛ query را در `name + type` مقصدها جست‌وجو می‌کند. [LIVE-BUNDLE]
- submit فرم فقط نتیجه را آشکار می‌کند؛ provider یا API فراخوانی نمی‌شود.
- نتیجه حداکثر شش مقصد است. در query معتبر، hint قابل مشاهده و tile قابل کلیک است.

## ۵. بازگشت بین Home، Destination و Route

Home نقطهٔ شروع است. tile مقصد مستقیماً به Destination می‌رود. Home back control ندارد؛ بازگشت از Destination با brand یا back link مقصد انجام می‌شود و بازگشت از Route با parent destination. [LIVE][PRODUCT]

## ۶. انتخاب روز، صبح/بعدازظهر، ساعت شروع و سرعت

این کنترل‌ها در Home وجود ندارند و برای Destination/Route هستند. [LIVE]

## ۷. مسیرهای دیگر همان مقصد

در Home مسیر نمایش داده نمی‌شود؛ کاربر ابتدا باید مقصد را انتخاب کند. [LIVE]

## ۸. کارت تصمیم، هشدار، اشتراک‌گذاری و نقاط مسیر

در Home کارت تصمیم، هشدار forecast، share و نقاط مسیر وجود ندارد. [LIVE]

## ۹. تفاوت mobile و desktop

| مورد | mobile، viewport مرجع 576px | desktop، viewport مرجع 1905px |
| --- | --- | --- |
| header | عرض observed برابر 544px و ارتفاع 76px | max-width observed برابر 1500px و ارتفاع 89px |
| search | 544×62px، یک composition فشرده | 610×74px در مرکز hero |
| tiles | دو ستون، هر tile حدود 268.5×54px | یک ردیف شش‌تایی، هر tile حدود 95×58px |
| hero | تصویر عمودی و tileها بالاتر از landscape | تصویر full viewport با whitespace بیشتر و tile row فشرده |
| overflow | document/body width برابر 576 و overflow ندارد | document/body width برابر 1905 و overflow ندارد |

[LIVE] mobile و desktop از یک DOM و CSS responsive استفاده می‌کنند؛ mobile صرفاً desktop فشرده‌شدهٔ افقی نیست و grid آن دو ستونه می‌شود.

## ۱۰. تفاوت light و dark

- light: body observed `rgb(201, 220, 218)`، متن ink، search با زمینهٔ `rgb(213, 229, 225)`، tile با زمینهٔ نیمه‌شفاف `rgba(210, 226, 222, .86)`.
- dark: body/main observed `#071d28`، search سفید نیمه‌شفاف `rgba(255,255,255,.97)`، tile تیره و translucent با border روشن.
- theme toggle در light «◐ تیره» و در dark «☼ روشن» است؛ aria-label هر دو `تغییر تم` است.
- در dark hero تصویر sunset/night و در light hero تصویر کوهستان روز استفاده می‌شود. [SCREENSHOT][LIVE]

## ۱۱. اندازه، فاصله، رنگ، border، radius، shadow و typography

- font computed: `Vazirmatn, "Noto Sans Arabic", Tahoma, Arial, sans-serif`، 16px، line-height 27.2px. [LIVE]
- theme toggle: radius `999px`؛ desktop ارتفاع 33px و mobile ارتفاع 38px؛ padding desktop `7px 12px` و mobile `6px 9px`.
- search: radius `14px`؛ light border `1px solid rgb(169,197,191)`؛ desktop shadow حدود `0 10px 24px rgba(16,43,61,.12)` و dark desktop `0 18px 45px rgba(0,0,0,.24)`.
- destination tile: radius `13px`؛ light border `rgb(169,197,191)`؛ light shadow حدود `0 8px 20px rgba(16,43,61,.07)`؛ dark بدون shadow محسوس و border روشن translucent.
- layout بر پایهٔ 1500px max-width در header desktop و padding responsive انجام شده است. [LIVE CSS/DOM]

## ۱۲. loading، empty، error و stale-data

- empty: **PASS / مشاهده شد**؛ query ناموجود heading را به «نتایج مرتبط» تغییر می‌دهد و پیام دقیق empty را نشان می‌دهد.
- loading: **BLOCKED**؛ Home page-specific loading component یا متن loading در live page bundle دیده نشد و server-rendered page تقریباً آماده تحویل می‌شود.
- error: **BLOCKED**؛ error UI برای search/catalog در page bundle وجود ندارد؛ error boundary عمومی framework به‌تنهایی evidence محصولی محسوب نمی‌شود.
- stale-data: **BLOCKED**؛ Home فقط catalog static دارد و timestamp/freshness/stale marker ندارد.

این موارد حدس زده نمی‌شوند و در `docs/open-questions.md` ثبت شده‌اند. [LIVE-BUNDLE]

## ۱۳. داده‌ها و API آینده

- رفتار فعلی: array ثابت مقصدها در `page-C3o0Of17.js`؛ هیچ `fetch`، `/api`، Open-Meteo یا geolocation در page-specific bundle دیده نشد. [LIVE-BUNDLE]
- قرارداد آیندهٔ موردنیاز محصول: catalog مقصدهای محبوب و query search داخلی. [PRODUCT]
- API پیشنهادی برای آینده: `GET /api/v1/destinations/popular` و `GET /api/v1/destinations?query=...`؛ این‌ها رفتار فعلی نیستند.

## ۱۴. محدودیت overflow و responsive

- در هر چهار حالت observed، `document.scrollWidth === clientWidth` و `body.scrollWidth === clientWidth` بود. [LIVE]
- input و CTA در mobile در یک search box کنترل‌شده قرار دارند و overlap observed نشد.
- grid باید در mobile دو ستون و در desktop شش ستون باشد؛ tileها نباید width ثابت desktop را به mobile منتقل کنند.

## ۱۵. معیار پذیرش قابل تست

| بخش | معیار تست |
| --- | --- |
| header | brand به `/`، ورود به `/login` و theme toggle به theme دیگر می‌روند. |
| search | submit با `توچال` فقط tile توچال را می‌دهد و query ناموجود empty message دقیق را نشان می‌دهد. |
| tile | هر شش مقصد href درست و نام/category درست دارد. |
| responsive | در 576px search overlap و root horizontal overflow وجود ندارد؛ در 1905px شش tile در row قابل مشاهده‌اند. |
| theme | بعد از toggle، text/search/tile contrast و label روشن/تیره تغییر می‌کند و context از بین نمی‌رود. |
| state gaps | loading/error/stale تا زمان تصمیم محصول implementation نهایی‌شده تلقی نشوند. |

## منابع و محدودیت evidence

- live DOM، computed style، interaction و asset bundle: `[LIVE]` و `[LIVE-BUNDLE]`.
- screenshotهای هم‌نام repository: `design/screens/home/{light,dark}/{mobile,web}.png`. `[SCREENSHOT]`
- `/workspace/sites/hawatch-weather`: `[BLOCKED]` و در این محیط موجود نبود.
- `Hawatch.docx`: `[BLOCKED]` و در این محیط موجود نبود.
- الزام RTL، product name و منع implementation: `[PRODUCT]`.
