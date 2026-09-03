# بررسی read-only صفحهٔ Destination

زمان بررسی: 2026-08-25. URL: `https://hawatch-weather.admirer135.chatgpt.site/destination/touchal`

منبع labels: `[LIVE]` DOM/رفتار live، `[LIVE-BUNDLE]` assetهای JS/CSS live، `[SCREENSHOT]` تصاویر repository، `[PRODUCT]` درخواست محصول، `[BLOCKED]` منبع در دسترس‌نبوده.

## ۱. بخش‌های قابل مشاهده و ترتیب

ترتیب DOM و layout مشاهده‌شده:

۱. header کوچک با برند، ورود و theme toggle.
۲. `destination-hero` شامل تصویر توچال، breadcrumb/title، وضعیت فعلی و تغییر مهم.
۳. `weather-card`: عنوان forecast، توضیح، آخرین به‌روزرسانی، day tabs، کنترل مسیر mobile، period toggle و hourly forecast.
۴. `technical-card`: جزئیات تخصصی روز انتخاب‌شده.
۵. در web، aside شامل `top-routes-card` با heading «تصمیم بعدی / مسیرها».
۶. `destination-decision-card`: جمع‌بندی هواچ.
۷. footer با tagline.

در mobile، back link داخل hero قابل مشاهده است؛ در desktop breadcrumb جای آن را می‌گیرد. [LIVE]

## ۲. متن‌ها، عنوان‌ها، labelها و CTAها

| عنصر | متن دقیق مشاهده‌شده |
| --- | --- |
| breadcrumb | `مقصدها / قلهٔ توچال` |
| title | `قلهٔ توچال` |
| subtitle | `کوه · البرز مرکزی · ۳۹۶۴ متر` |
| current status | `☼ الان در قله ۹° · صاف` |
| alert | `! تغییر مهم: از ساعت ۱۴ برف و باد بیشتر` |
| forecast heading | `پیش‌بینی قلهٔ توچال` |
| forecast helper | `روز و ساعت را انتخاب کن تا تغییر شرایط مقصد و مسیرهایش را قبل از حرکت ببینی.` |
| updated | `آخرین به‌روزرسانی: امروز، ۰۵:۴۵` |
| period label | `بازهٔ نمایش هوا` |
| morning | `صبح / ۰۰ تا ۱۲` |
| after/noon | `بعدازظهر / ۱۲ تا ۲۴` |
| hourly heading | `تغییرات نیمهٔ اول روز · هر دو ساعت` |
| legend | `عادی`، `تغییر مهم`، `نقطه حساس` |
| technical heading | `جزئیات تخصصی امروز` |
| technical helper | `اطلاعات نمونه برای تصمیم‌گیری مسیر` |
| side heading | `تصمیم بعدی / مسیرها` |
| decision chip | `امروز · جمع‌بندی هواچ` |
| decision title | `صبح برای شروع برنامه مناسب‌تر است.` |
| decision text | `تا حدود ساعت ۱۰ شرایط آرام‌تر می‌ماند؛ بعد از آن باد در ارتفاعات بیشتر می‌شود و از ساعت ۱۴ احتمال برف بالا می‌رود.` |
| footer | `هوای مقصد، برنامهٔ مسیر` |

hourly صبح: `۰۰:۰۰ صاف ۷° باد ۷ km/h`، `۰۲:۰۰ صاف ۷° باد ۷ km/h`، `۰۴:۰۰ نیمه‌ابری ۹° باد ۱۳ km/h`، `۰۶:۰۰ نیمه‌ابری ۹° باد ۱۲ km/h`، `۰۸:۰۰ بادخیز ۱۲° باد ۲۸ km/h`، `۱۰:۰۰ بادخیز ۱۲° باد ۲۹ km/h`. [LIVE]

metrics دقیق: باد میانگین `۱۰ km/h / جنوب‌غربی`؛ تندباد قله `۳۹ km/h / بیشتر از ساعت ۱۲`؛ دید افقی `+۱۰ km / کاهش دید از ساعت ۱۴`؛ تراز صفر درجه `۴۲۵۰ m / بالاتر از قله`؛ پایهٔ ابر `۴۶۰۰ m / قله بدون ابر: ۷۰٪`؛ تابش فرابنفش `۷ · زیاد / برای بخش‌های باز مسیر`؛ بارش `۰٪ / تا ساعت ۱۳ · سپس برف`؛ طلوع/غروب `۰۵:۲۲ / ۱۹:۴۶ / برای زمان‌بندی برگشت`. [LIVE]

## ۳. لینک‌ها و navigation

| متن/نقش | href یا رفتار |
| --- | --- |
| هواچ | `/` |
| ورود | `/login` |
| بازگشت mobile | `/`، با aria-label `بازگشت به هوم` |
| breadcrumb مقصدها | `/#search-results` |
| دربند تا توچال | `/routes/touchal-darband` |
| ولنجک تا توچال | `/routes/touchal-welanjak` |
| کلکچال تا توچال | `/routes/touchal-kalkchal` |
| شهرستانک تا توچال | `/routes/touchal-shahrestanak` |
| آهار تا توچال | `/routes/touchal-ahar` |

هر route دو بار در DOM دیده می‌شود: یک بار mobile route picker و یک بار web side route card. [LIVE]

## ۴. رفتار دکمه‌ها، toggleها، tabها و cardها

- theme toggle مانند Home عمل می‌کند و localStorage key آن `hawatch-theme` است.
- day tabs با state عددی شروع از index ۱ (`امروز`) هستند؛ کلیک index جدید را active می‌کند و derived hourly/metrics/decision را تغییر می‌دهد. [LIVE-BUNDLE]
- `دیروز` class `past-day` و ظاهر کم‌رنگ‌تر دارد؛ state انتخابی با `aria-selected` اعلام می‌شود.
- period با دو button و `aria-pressed` کنترل می‌شود؛ state داخلی `morning` و `night` است، اما label دوم «بعدازظهر» است. [LIVE-BUNDLE]
- در morning headline «تغییرات نیمهٔ اول روز · هر دو ساعت» و در period دوم headline نیمهٔ دوم روز می‌شود.
- mobile route picker با aria-label `انتخاب مسیر` پنج route را نشان می‌دهد؛ route cardها navigation به Route هستند.
- hourly item قابل کلیک نیست؛ فقط وضعیت `normal/change/critical` و در حالت غیرعادی label `تغییر مهم` یا `احتیاط` دارد.
- technical metrics در live card تعاملی نیستند.
- side route card با class `recommended` و label «پیشنهاد هواچ» مسیر featured را مشخص می‌کند.

## ۵. بازگشت بین Home، Destination و Route

back mobile و برند به Home می‌روند. breadcrumb «مقصدها» به Home و route card به Route می‌رود. Route باید با back به همین Destination برگردد؛ این رفتار در Route live به‌صورت href `/destination/touchal` دیده شد. [LIVE]

## ۶. روز، صبح/بعدازظهر، ساعت شروع و سرعت

Destination فقط روز و period دارد. ساعت شروع و سرعت در Route است. Day tab روی Destination forecast و decision همان روز اثر می‌گذارد؛ period روی hourly cards و headline اثر می‌گذارد. [LIVE-BUNDLE]

## ۷. مسیرهای دیگر همان مقصد

برای Touchal پنج مسیر live است:

- featured: دربند تا توچال، `ترک کوه‌پیمایی · دربند · ۱۶٫۲ km · ۲۲۶۰ m صعود`.
- ولنجک تا توچال، `ترک پیاده‌روی · ولنجک · ۱۴٫۸ km · ۲۱۶۰ m صعود`.
- کلکچال تا توچال، `ترک فنی‌تر · پارک جمشیدیه · ۱۷٫۴ km · ۱۸۷۰ m صعود`.
- شهرستانک تا توچال، `ترک طبیعت‌گردی · شهرستانک · ۱۸٫۶ km · ۱۹۸۰ m صعود`.
- آهار تا توچال، `کوه‌پیمایی · آهار · ۱۸٫۶ km · ۲۰۵۰ m صعود`.

در live source اگر `g.length === 0` باشد route empty state با متن `هنوز ترکی برای این مقصد ثبت نشده` و توضیح `این صفحه فقط پیش‌بینی مقصد را نشان می‌دهد؛ به‌محض ثبت ترک پیاده‌روی، اینجا اضافه می‌شود.` render می‌شود؛ برای Touchal این branch فعال نیست. [LIVE-BUNDLE]

## ۸. هشدار، decision و نقاط مسیر

Destination hero دو status دارد: current teal و change amber. تصمیم پایین side/صفحه با chip، title و متن توضیحی می‌گوید صبح مناسب‌تر است و باد/برف بعدی چه زمانی افزایش می‌گیرد. Share و route points در Destination وجود ندارند و در Route ارائه می‌شوند. [LIVE]

## ۹. تفاوت mobile و desktop

| مورد | mobile 576px | desktop 1905px |
| --- | --- | --- |
| header | observed 548×62px | observed 1416×92px |
| hero | observed 548×116px، radius 16px، back link visible | observed 1416×250px، radius 25px، breadcrumb visible |
| route picker | در weather card و دو/چند ستون کوچک | aside چپ با route cardهای کامل |
| weather | cardها تقریباً full width، تراکم زیاد | weather card اصلی در content حدود 1080px و aside جدا |
| technical | grid فشردهٔ دو ستونهٔ mobile | grid بزرگ‌تر چندستونه |
| footer/scroll | صفحه بلند، root overflow افقی ندارد | layout دو ستون، root overflow افقی ندارد |

[LIVE] در چهار حالت measured `horizontalOverflow=false` بود. [SCREENSHOT] تصویرهای مرجع page height موبایل 1729px و web 1602px هستند.

## ۱۰. تفاوت light و dark

- light runtime body `rgb(201,220,218)`؛ hero image با overlay روشن، text `#173746`/`#102b3d`، teal حدود `#1d7f86`، amber change روشن.
- dark runtime body `#0b2732`؛ surfaceهای آبی-سبز، text `#edf7f4`، teal روشن حدود `#61c5c0`، amber حدود `#f0bd61` و coral حدود `#ed897b`.
- card light border `rgb(169,197,191)`، radius desktop 18px و mobile 14px؛ dark border translucent `rgba(190,225,221,.18)` و shadow تیره‌تر.
- current/change semantic در هر دو theme با متن و رنگ باقی می‌مانند. [LIVE CSS/DOM]

## ۱۱. اندازه، فاصله، border، radius، shadow و typography

- font target: `Estedad, "Noto Sans Arabic", Tahoma, Arial, sans-serif`، 16px، line-height 27.2px؛ live باید پس از انتشار دوباره تأیید شود. [LOCAL-IMPLEMENTATION]
- desktop hero: border 1px solid light `rgb(169,197,191)` یا dark `rgba(190,225,221,.18)`؛ radius 25px؛ shadow light حدود `0 14px 32px rgba(16,43,61,.09)` و dark حدود `0 16px 36px rgba(0,0,0,.2)`.
- first weather card observed desktop حدود 1080×568px با padding حدود `23px 25px`؛ mobile حدود 548×383px با padding 9px.
- theme toggle desktop 33px height و mobile 38px height؛ radius 999px.
- live CSS brand radius 18px، control radius حدود 10px، hero radius حدود 24–25px؛ computed mobile hero 16px است. [LIVE CSS/DOM]

## ۱۲. loading، empty، error و stale-data

- empty route: **CONDITIONAL / source-confirmed**؛ branch در bundle وجود دارد، اما Touchal route دارد و آن state در URL بررسی‌شده دیده نشد.
- loading forecast: **BLOCKED**؛ page-specific bundle loading UI ندارد و دادهٔ static server-rendered است.
- error forecast/API: **BLOCKED**؛ provider/API call یا page-specific error branch در bundle دیده نشد.
- stale: **BLOCKED**؛ فقط متن ثابت «آخرین به‌روزرسانی: امروز، ۰۵:۴۵» وجود دارد و freshness logic مشاهده نشد.

## ۱۳. داده‌ها و API آینده

- live: destination object از `site-data-DQ0UR-FX.js` شامل image، name، heroStatus، heroAlert، days، hours، metrics، routeSlugs و decision است؛ fetch provider/API ندارد. [LIVE-BUNDLE]
- future product API: destination catalog، current/hourly forecast، alerts و route catalog. [PRODUCT]
- endpointهای پیشنهادی مستندشده ولی not-live: `GET /api/v1/destinations/{slug}`، `GET /api/v1/destinations/{slug}/forecast?date=&period=`، `GET /api/v1/destinations/{slug}/routes`.

## ۱۴. محدودیت overflow و responsive

- mobile route list و day tabs باید داخل container خودشان بمانند؛ در live root scroll width برابر client width بود.
- شش hourly card در mobile در یک card داخلی فشرده می‌شوند؛ باید root را عریض نکنند.
- desktop می‌تواند two-column باشد؛ mobile side route/decision باید در ترتیب خواندن page قرار گیرد.
- title، status و image overlay نباید در عرض 576px روی هم بیفتند. [LIVE][SCREENSHOT]

## ۱۵. معیار پذیرش قابل تست

| بخش | معیار تست |
| --- | --- |
| hero | title `قلهٔ توچال`، elevation `۳۹۶۴ متر`، current status و alert در هر دو theme خوانا هستند. |
| day tabs | ابتدا امروز selected است؛ کلیک day دیگر `aria-selected=true` را جابه‌جا و دادهٔ derived را تغییر می‌دهد؛ دیروز کم‌رنگ است. |
| period | ابتدا صبح selected است؛ کلیک بعدازظهر `aria-pressed` و headline نیمهٔ دوم روز را تغییر می‌دهد. |
| routes | پنج route Touchal href و label درست دارند؛ route featured با «پیشنهاد هواچ» مشخص است. |
| hourly/metrics | شش ساعت صبح و هشت metric با واحد، condition و semantic state درست render می‌شوند. |
| responsive | در 576px route picker، day tabs و hourly cards root overflow ایجاد نمی‌کنند؛ در 1905px aside دو ستونه است. |
| state gaps | loading/error/stale تا قرارداد آیندهٔ داده و تصمیم محصول نهایی نشده‌اند، PASS تلقی نشوند. |

## منابع و محدودیت evidence

- live DOM، CSS computed style، screenshot و JS bundle: `[LIVE]`/`[LIVE-BUNDLE]`.
- images: `design/screens/destination/{light,dark}/{mobile,web}.png`. `[SCREENSHOT]`
- سورس local `/workspace/sites/hawatch-weather`: `[BLOCKED]`.
- Hawatch.docx: `[BLOCKED]`.
- ترتیب محصول، RTL، ممنوعیت implementation: `[PRODUCT]`.
