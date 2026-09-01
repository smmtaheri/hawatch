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
۷. کارت خلاصهٔ هوای هر نقطه در بازهٔ انتخاب‌شده.
۸. کارت تصمیم.
۹. اشتراک‌گذاری.

آمار کلی تکراری مسیر (مسافت، صعود، زمان تخمینی و ساعت پایان) در انتهای صفحهٔ Route نمایش داده نمی‌شود؛ این اطلاعات در کارت‌ها و خلاصه‌های بالاتر، جایی که برای تصمیم کاربر لازم است، ارائه می‌شوند.

محور نقاط فقط نام، ترتیب و marker را نشان می‌دهد؛ دمای تکراری زیر markerها بخشی از محور نیست. forecast عمومی مقصد/قله نباید به‌جای خلاصهٔ pointهای مسیر در این بخش نمایش داده شود.

## ۴. hierarchy کامپوننت‌ها

`RoutePage → SiteHeader + RouteHero + SiblingRouteNav + RouteLayout → DayPicker + PlannerControls(StartTimeGauge, SpeedSegmentedControl) + RoutePointAxis + PointWeatherCards + RouteDecisionCard(ShareActions, GearRecommendations) + RouteStats`.

## ۵. رفتار کنترل‌ها

- back: به Destination parent برمی‌گردد.
- sibling route: route جدید همان destination را باز می‌کند.
- day: تمام زمان‌ها، weather points و decision summary را برای روز جدید refresh می‌کند.
- start-time gauge: در ورود بدون start_time، برای تاریخ/بازهٔ جاری روی زمان فعلی `Asia/Tehran` قرار می‌گیرد؛ برای تاریخ‌های دیگر از default همان بازه استفاده می‌شود. قسمت قبل از زمان فعلی کم‌رنگ و قسمت آینده عادی است. بعد از تغییر، در صورت آماده‌بودن timing، زمان رسیدن نقاط recompute می‌شود.
- speed segmented control: آرام/متوسط/سریع؛ زمان نقاط و کارت تصمیم به‌روزرسانی می‌شوند.
- morning/afternoon/night: یک کنترل مشترک سه‌گزینه‌ای برای route points و hourly forecast در mobile.
- point: جزئیات canonical در `/points/{weatherPointSlug}` باز می‌شود؛ اما WeatherPoint مقصدی مثل `tochal_summit` باید به `/destination/touchal` برود. `location.state.fromRoute` فقط برای back CTA و بازگرداندن queryهای planner استفاده می‌شود.
- copy link: لینک بازسازی‌پذیر برنامه را کپی می‌کند و feedback کوتاه می‌دهد.
- share: لینک بازسازی‌پذیر فعلی را از queryهای planner آماده می‌کند؛ share server-side در این milestone ساخته نشده است.

## ۶. stateهای loading، ready، empty، error، stale و partial-data

- loading: axis، controls و card layout ثابت بمانند؛ مقدارها skeleton شوند.
- ready: نقاط، خلاصهٔ آب‌وهوا، هشدار و stats با timestamp معتبرند؛ هر کارت point متعلق به همان point است.
- empty: route یا forecast در تاریخ انتخابی موجود نیست؛ روز جایگزین و back پیشنهاد شود.
- error: failure در normalize/forecast با retry و توضیح اینکه کدام بخش unavailable است.
- stale: هشدار زمان داده و ممنوعیت تصمیم قطعی بدون acknowledge.
- partial-data: route geometry/catalog حتی اگر weather برخی نقاط ناقص است نمایش داده شود؛ نقطهٔ ناقص جدا label شود.
- timing pending: عبارت داخلی `timing pending` نمایش داده نمی‌شود؛ متن فارسی روشن نشان می‌دهد زمان‌بندی/ETA آماده نیست و هیچ ETA، زمان نقطه یا مسافت ساختگی تولید نمی‌شود.

## ۷. داده‌های موردنیاز

- route: slug، origin، destination، distance، ascent، `one_way_minutes` (صعود یک‌طرفهٔ متوسط) و نقاط مسیر. `round_trip_minutes` برای زمان صعود یک‌طرفه استفاده نمی‌شود.
- هر point: نام، ترتیب، زمان رسیدن تقریبی (`حدود …`)، آیکون/شرط/دما/باد/severity همان نقطه در نزدیک‌ترین ساعت به رسیدن (±۹۰ دقیقه)، و نشان `تخمینی · ±N دقیقه` وقتی timing estimated و uncertainty موجود است. عنوان period عمومی بالای هر نقطه نمایش داده نمی‌شود. severity کارت فقط از forecast همان نقطه می‌آید.
- اگر timing pending/unusable است (از جمله estimated ناقص بدون cumulative کامل)، کارت نباید ETA یا weather ساختگی نشان دهد؛ متن فارسی «زمان‌بندی در دسترس نیست» کافی است و رشتهٔ خام `timing_pending` نمایش داده نمی‌شود.
- start time، speed profile (ضریب زمان آرام/متوسط/سریع) و محاسبهٔ arrival.
- forecast point-level برای زمان رسیدن محاسبه شده؛ period انتخابی فقط پنجرهٔ حرکت را محدود می‌کند.
- decision summary، `decision.gear[]` و share payload؛ `gear[]` کلیدهای معنایی
  تجهیزات است و کارت share فقط نام و آیکون تجهیزات را در پایین خود نشان می‌دهد.
  `recommendations[]` برای سازگاری API نگه داشته می‌شود اما متن توضیحی آن در
  کارت نمایش داده نمی‌شود. برای timing estimated یادآوری‌ها همچنان در منطق
  تصمیم API وجود دارند؛ تخمین‌های فعلی catalog-level v1 هستند نه موتور
  per-segment کالیبره‌شده.

## ۸. API فعلی و مسیرهای توسعه

- `GET /api/v1/routes/{slug}/forecast/?date=&period=&start_time=&speed=` پاسخ فعلی route و forecast را می‌دهد؛ برای Tochal v1 شامل `timing_status=estimated`، provenance/confidence/uncertainty و arrival-aware point weather است.
- `GET /api/v1/routes/{route_slug}/points/{point_slug}/forecast/` قرارداد legacy سازگار را نگه می‌دارد.
- `GET /api/v1/points/{weather_point_slug}/forecast/?date=&period=` صفحهٔ مستقل نقطه را تغذیه می‌کند.
- endpointهای plan جدا و share server-side هنوز مسیر توسعه‌اند.

API plan باید idempotent/read-oriented باشد و provider را به frontend لو ندهد.

## ۹. تفاوت mobile و web

- mobile: hero مسیر هم‌اندازهٔ hero فشردهٔ مقصد و بدون breadcrumb تکراری است؛ عنوان و status در دو سوی hero و در مرکز ارتفاع آن می‌مانند. «مسیرهای دیگر» فقط trigger فشردهٔ پایین hero است و siblingها را در bottom sheet باز می‌کند؛ grid دسکتاپ siblingها در mobile دیده نمی‌شود. اولین کارت بعد از hero، label انتخاب روز و کنترل مشترک سه‌گزینه‌ای صبح/بعدازظهر/شب را در یک ردیف و tabهای روز را در ردیف بعد دارد. کنترل‌ها کوچک و هم‌ارتفاع؛ ساعت و سرعت در یک ردیف؛ خط جداکنندهٔ عمودی حذف.
- نقاط مسیر و کارت خلاصهٔ هوای همان نقاط روی یک محور و scroll-owner مشترک
  بمانند؛ در web حداکثر شش نقطه هم‌زمان دیده شود و بقیه افقی scroll شوند.
  در mobile نیز همین owner مشترک با اندازهٔ فشرده‌تر حفظ شود، نه دو اسکرول
  جداگانه.
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
- تغییر start time یا speed زمان همهٔ نقاط و کارت تصمیم را هماهنگ به‌روزرسانی کند و ممکن است forecast ساعتی متفاوتی برای هر نقطه انتخاب شود.
- پنج مسیر توچال بعد از seed دیگر timing-pending نیستند و ETA تقریبی نشان می‌دهند (نه قطعی).
- mobile یک کنترل مشترک period داشته باشد و جداکنندهٔ عمودی نداشته باشد.
- نقاط مسیر و کارت خلاصهٔ weather همان نقاط روی یک محور معنایی بمانند.
- دمای زیر markerهای محور حذف شده باشد.
- عبارت «تغییرات شب · هر دو ساعت» از Route حذف شده باشد.
- کارت‌های weather زیر محور برای هر RoutePoint ساخته شوند، نه forecast عمومی قله؛ بدون fallback قله برای نقطهٔ بدون داده.
- در timing pending، fallback ثابت ظهر برای periodهای دیگر استفاده نشود.
- قلهٔ توچال از Route به صفحهٔ canonical مقصد می‌رود.
- gauge در ورود به Route زمان فعلی تهران را نشان می‌دهد و بخش گذشته dim است.
- root overflow افقی نداشته باشد؛ هر scroll احتمالی scoped باشد.
- کپی لینک، queryهای `date`، `period`، `start_time` و `speed` را برای بازسازی برنامه منتقل می‌کند.
- در web برای routeهای بیش از شش نقطه، شش point اول در viewport قرار دارند و
  point/weather card متناظر با یک `scrollLeft` مشترک حرکت می‌کند.
- پایین share card فقط تجهیزات پیشنهادی دارای `GearIcon` و نام وسیله دیده می‌شود؛
  متن‌های بلند recommendation در این بخش render نمی‌شوند.

## ۱۳. تصویر مرجع

- [light/mobile](../screens/route/light/mobile.png)
- [dark/mobile](../screens/route/dark/mobile.png)
- [light/web](../screens/route/light/web.png)
- [dark/web](../screens/route/dark/web.png)

## ۱۴. موارد نامشخص و تصمیم‌های باز

- مدل دقیق route geometry و اینکه axis جایگزین map است یا مکمل آن مشخص نشده است.
- زمان‌بندی Tochal v3: Darband/Velenjak/Ahar با پروفایل GPX؛ کلکچال هندسهٔ کامل GPX با timestamp مصنوعی؛ شهرستانک برآورد ترکیبی estimated (نه curated). GPX فقط evidence داخلی است و در runtime parse نمی‌شود.
- share link دائمی یا کوتاه‌عمر و حریم خصوصی برنامه باید تعیین شود.
- threshold تصمیم برگشت و مسئولیت محتوای safety copy باید با مالک محصول نهایی شود.
