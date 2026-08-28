# مشخصات صفحهٔ Route

جزئیات استخراج‌شدهٔ read-only از سایت زنده در [بررسی live Route](../../docs/live-page-inspection/route.md) ثبت شده است؛ source محلی معرفی‌شده در handoff در این محیط در دسترس نبود.

## ۱. هدف صفحه و تصمیم کاربر

Route باید زمان شروع، سرعت حرکت، تغییر شرایط در نقاط مسیر و ریسک‌های مهم را کنار هم قرار دهد تا کاربر تصمیم بگیرد حرکت کند، زمان/سرعت را تغییر دهد یا در نقطه‌ای برگردد.

## ۲. مسیر ورود و خروج

- ورود: از route card صفحهٔ Destination با `/routes/touchal-darband` یا route slug.
- خروج: بازگشت به مقصد، انتخاب مسیر دیگر همان مقصد، کپی/اشتراک برنامه.
- تغییر روز، ساعت شروع، سرعت و بازه در query/state قابل بازسازی هستند؛ لینک نقطه canonical و تمیز است و context کامل planner را در navigation state نگه می‌دارد.

## ۳. ترتیب دقیق بخش‌ها

۱. header کوچک مسیر.
۲. بازگشت به مقصد.
۳. مسیرهای دیگر همان مقصد.
۴. انتخاب روز.
۵. بازهٔ شروع حرکت و سرعت حرکت در یک کادر جمع‌وجور.
۶. نقاط مهم مسیر.
۷. اطلاعات هوای هر نقطه.
۸. کارت تصمیم.
۹. اشتراک‌گذاری.
۱۰. اطلاعات فنی مسیر.

## ۴. hierarchy کامپوننت‌ها

`RoutePage → SiteHeader + RouteHero + SiblingRouteNav + RouteLayout → DayPicker + PlannerControls(StartTimeGauge, SpeedSegmentedControl) + RoutePointAxis + PointWeatherCards + RouteDecisionCard(ShareActions) + RouteStats`.

## ۵. رفتار کنترل‌ها

- back: به Destination parent برمی‌گردد.
- sibling route: route جدید همان destination را باز می‌کند.
- day: تمام زمان‌ها، weather points و decision summary را برای روز جدید refresh می‌کند.
- start-time gauge: زمان حرکت را تغییر می‌دهد و زمان رسیدن همهٔ نقاط را recompute می‌کند.
- speed segmented control: آرام/متوسط/سریع؛ زمان نقاط و کارت تصمیم به‌روزرسانی می‌شوند.
- morning/afternoon/night: یک کنترل مشترک سه‌گزینه‌ای برای route points و hourly forecast در mobile.
- point: جزئیات canonical در `/points/{weatherPointSlug}` باز می‌شود؛ `location.state.fromRoute` برای back CTA و بازگرداندن queryهای planner استفاده می‌شود.
- copy link: لینک بازسازی‌پذیر برنامه را کپی می‌کند و feedback کوتاه می‌دهد.
- share: لینک بازسازی‌پذیر فعلی را از queryهای planner آماده می‌کند؛ share server-side در این milestone ساخته نشده است.

## ۶. stateهای loading، ready، empty، error، stale و partial-data

- loading: axis، controls و card layout ثابت بمانند؛ مقدارها skeleton شوند.
- ready: زمان‌ها، نقاط، آب‌وهوا، هشدار و stats با timestamp معتبرند.
- empty: route یا forecast در تاریخ انتخابی موجود نیست؛ روز جایگزین و back پیشنهاد شود.
- error: failure در normalize/forecast با retry و توضیح اینکه کدام بخش unavailable است.
- stale: هشدار زمان داده و ممنوعیت تصمیم قطعی بدون acknowledge.
- partial-data: route geometry/catalog حتی اگر weather برخی نقاط ناقص است نمایش داده شود؛ نقطهٔ ناقص جدا label شود.

## ۷. داده‌های موردنیاز

- route: slug، origin، destination، distance، ascent، round-trip duration و نقاط مسیر.
- هر point: مختصات، elevation، ترتیب، زمان پایه، temperature، wind، condition، note و severity.
- start time، speed profile و محاسبهٔ arrival time.
- forecast hourly برای بازهٔ انتخابی؛ هر بازه چهار کارت دارد: صبح ۰۳، ۰۵، ۰۷، ۰۹؛ بعدازظهر ۱۱، ۱۳، ۱۵، ۱۷؛ شب ۱۹، ۲۱، ۲۳، ۰۱.
- decision summary، recommendations و share payload.

## ۸. API فعلی و مسیرهای توسعه

- `GET /api/v1/routes/{slug}/forecast/?date=&period=&start_time=&speed=` پاسخ فعلی route و forecast را می‌دهد.
- `GET /api/v1/routes/{route_slug}/points/{point_slug}/forecast/` قرارداد legacy سازگار را نگه می‌دارد.
- `GET /api/v1/points/{weather_point_slug}/forecast/?date=&period=` صفحهٔ مستقل نقطه را تغذیه می‌کند.
- endpointهای plan جدا و share server-side هنوز مسیر توسعه‌اند.

API plan باید idempotent/read-oriented باشد و provider را به frontend لو ندهد.

## ۹. تفاوت mobile و web

- mobile: کنترل‌ها کوچک و هم‌ارتفاع؛ ساعت و سرعت در یک ردیف؛ خط جداکنندهٔ عمودی حذف؛ فقط یک کنترل مشترک سه‌گزینه‌ای صبح/بعدازظهر/شب.
- نقاط مسیر و کارت آب‌وهوا روی یک محور خوانا بمانند؛ axis در صورت نیاز در container خودش scroll شود، نه root.
- گیج ساعت شروع بیش از حد بزرگ نشود.
- web: layout اصلی و side planner می‌توانند چندستونه باشند؛ route axis و point cards فضای بیشتری دارند.

## ۱۰. تفاوت light و dark

- light: surfaceهای روشن، route hero teal تیره، amber decision card و coral critical card.
- dark: hero و cardها در طیف آبی-سبز عمیق، teal روشن، amber و coral روشن‌تر.
- statusهای مسیر باید با متن و label در هر دو theme قابل تشخیص باشند.

## ۱۱. قواعد RTL و دسترسی‌پذیری

- متن و navigation RTL؛ axis از origin به destination از نظر معنایی واضح و با label ابتدا/انتها مشخص باشد.
- slider ساعت label، value و keyboard step داشته باشد؛ جهت فیزیکی slider نباید کاربر RTL را گمراه کند.
- سرعت و period با role مناسب و state اعلام‌شده پیاده شوند.
- کارت decision هشدار را با heading و متن توضیحی ارائه کند؛ coral به‌تنهایی کافی نیست.

## ۱۲. معیار پذیرش

- ترتیب ده‌گانهٔ Route در mobile و web رعایت شود.
- تغییر start time یا speed زمان همهٔ نقاط و کارت تصمیم را هماهنگ به‌روزرسانی کند.
- mobile یک کنترل مشترک period داشته باشد و جداکنندهٔ عمودی نداشته باشد.
- نقاط مسیر و کارت‌های weather روی یک محور معنایی بمانند.
- root overflow افقی نداشته باشد؛ هر scroll احتمالی scoped باشد.
- کپی لینک، queryهای `date`، `period`، `start_time` و `speed` را برای بازسازی برنامه منتقل می‌کند.

## ۱۳. تصویر مرجع

- [light/mobile](../screens/route/light/mobile.png)
- [dark/mobile](../screens/route/dark/mobile.png)
- [light/web](../screens/route/light/web.png)
- [dark/web](../screens/route/dark/web.png)

## ۱۴. موارد نامشخص و تصمیم‌های باز

- مدل دقیق route geometry و اینکه axis جایگزین map است یا مکمل آن مشخص نشده است.
- تابع زمان‌بندی بر اساس speed و elevation نیازمند تعریف domain است.
- share link دائمی یا کوتاه‌عمر و حریم خصوصی برنامه باید تعیین شود.
- threshold تصمیم برگشت و مسئولیت محتوای safety copy باید با مالک محصول نهایی شود.
