# مشخصات صفحهٔ Destination

جزئیات استخراج‌شدهٔ read-only از سایت زنده در [بررسی live Destination](../../docs/live-page-inspection/destination.md) ثبت شده است؛ source محلی معرفی‌شده در handoff در این محیط در دسترس نبود.

## ۱. هدف صفحه و تصمیم کاربر

صفحهٔ مقصد باید به کاربر کمک کند بفهمد شرایط فعلی مقصد چیست، چه تغییری در طول روز رخ می‌دهد و کدام مسیر/بازه برای برنامه‌ریزی مناسب‌تر است. تصمیم اصلی، انتخاب روز، بازه و مسیر برای رفتن به Route یا اصلاح برنامه است.

## ۲. مسیر ورود و خروج

- ورود: از Home با `/destination/touchal` یا slug مقصد.
- خروج: بازگشت به Home، انتخاب مسیر به `/routes/{routeSlug}`، تغییر مقصد از breadcrumb یا انتخاب route دیگر.
- theme و navigation context باید هنگام تغییر day/period حفظ شوند.

## ۳. ترتیب دقیق بخش‌ها

۱. header کوچک.
۲. دکمهٔ بازگشت به Home.
۳. تصویر و عنوان مقصد.
۴. وضعیت فعلی.
۵. هشدار یا تغییر مهم.
۶. label «انتخاب روز» و انتخاب روز.
۷. بخش مسیرها.
۸. انتخاب صبح/بعدازظهر/شب؛ بازهٔ جاری پررنگ و بازه‌های کاملاً گذشته کم‌رنگ.
۹. پیش‌بینی ساعتی با چهار کارت دوساعته در هر بازه (صبح ۰۳، ۰۵، ۰۷، ۰۹؛ بعدازظهر ۱۱، ۱۳، ۱۵، ۱۷؛ شب ۱۹، ۲۱، ۲۳، ۰۱).
۱۰. جزئیات تخصصی.
۱۱. در web، decision card و خلاصهٔ مسیر در جایگاه side قرار می‌گیرند؛ در mobile به ترتیب خواندن تصمیم نزدیک داده می‌مانند.

## ۴. hierarchy کامپوننت‌ها

`PlaceForecastPage → Header + DestinationHero + DaySelector + related routes + PeriodToggle + HourlyForecast + StatsGrid + DecisionCard`.

هر دو URL `/destination/:slug` و `/points/:slug` همین درخت را رندر می‌کنند. مشخصات مشترک: [place-forecast.md](./place-forecast.md).

## ۵. رفتار کنترل‌ها

- back: به Home و context قبلی می‌رود.
- breadcrumb: مقصدها به Home، نام مقصد current و غیرقابل کلیک.
- day tabs: forecast و route recommendations را برای روز انتخابی refresh می‌کند.
- مسیرها: مسیر انتخابی را active می‌کند و به Route می‌برد یا data context صفحه را تغییر می‌دهد.
- صبح/بعدازظهر/شب: hourly forecast و وضعیت نقاط مرتبط را عوض می‌کند.
- در ورود بدون query، روز و بازهٔ فعلی تهران انتخاب می‌شوند. بازه‌های کاملاً سپری‌شده با opacity/saturation کمتر نمایش داده می‌شوند؛ بازهٔ انتخاب‌شده حتی اگر گذشته باشد باید خوانا و قابل تشخیص بماند.
- مبنای بازهٔ جاری فقط `meta.current_local_time` با timezone `Asia/Tehran` است؛ هیچ ساعت نمونه‌ای مثل ۱۰:۳۰ قاعدهٔ ویژه ندارد.
- cardهای route: detail route را باز می‌کنند.
- theme toggle: theme را تغییر می‌دهد، بدون reset کردن destination/day/period.

## ۶. stateهای loading، ready، empty، error، stale و partial-data

- loading: hero می‌تواند اطلاعات پایه را حفظ کند و weather card skeleton داشته باشد.
- ready: status، روزها، مسیرها، ساعت‌های بازهٔ انتخابی و metrics کامل نمایش داده شوند.
- empty: برای روز یا مسیر بدون forecast پیام و جایگزین قابل اقدام نمایش داده شود.
- error: شکست provider یا API داخلی با retry، زمان آخرین موفقیت و back path.
- stale: هشدار stale و در صورت نیاز زمان انسانی‌شده؛ timestamp خام ISO یا عبارت «آخرین به‌روزرسانی: ...» در صفحه نمایش داده نمی‌شود.
- partial-data: مثلاً hourly موجود ولی wind gust ناقص است؛ بخش موجود نمایش داده شود و metric ناقص به‌وضوح مشخص شود.

## ۷. داده‌های موردنیاز

- مقصد: slug، نام، category، مختصات، elevation و hero asset.
- وضعیت فعلی: condition، temperature، wind، visibility و fetched/valid times.
- forecast روزانه و hourly با بازه‌های صبح ۰۳–۱۱، بعدازظهر ۱۱–۱۹ و شب ۱۹–۰۳ روز بعد.
- route catalog همان مقصد.
- metrics تخصصی مثل gust، freezing level، cloud base، UV، precipitation و sunrise/sunset.
- هشدارها با severity normal/change/critical.

## ۸. API فعلی و مسیرهای توسعه

- `GET /api/v1/destinations/{slug}/`
- `GET /api/v1/destinations/{slug}/forecast/?date={date}&period={period}`
- فهرست routeهای مقصد در پاسخ destination برمی‌گردد.
- alert و metricهای provider-specific در صورت وجود از envelope forecast خوانده می‌شوند؛ endpoint جدا برای آن‌ها فعلاً وجود ندارد.

تمام این‌ها API داخلی‌اند و backend provider را پشت خود پنهان می‌کند. endpointهای توسعهٔ آینده نباید frontend را مستقیم به provider وصل کنند.

## ۹. تفاوت mobile و web

- mobile: روزها با label «انتخاب روز» قبل از کنترل هوا باشند؛ مسیرهای مرتبط/مقصد در کارت‌های فشرده و بدون کشیدگی باشند. هر route card فقط نام مسیر و دو خط facts دارد: «ارتفاع‌گیری» و «مسافت»؛ trail/origin تکراری زیر نام نمی‌آید. نشان «پیشنهاد هواچ» از icon مسیر فاصلهٔ ثابت دارد. کنترل سه‌گزینه‌ای صبح/بعدازظهر/شب در یک ردیف مستقل و خوانا باشد؛ cardها فقط در container خودشان scroll شوند.
- web: weather card و side route summary می‌توانند دو ستون باشند؛ کارت‌های هر بازه متناسب با تعدادشان در یک ردیف خوانا بمانند.
- timeline و cardها در mobile باید به ترتیب تصمیم خوانده شوند، نه بر اساس grid desktop.

## ۱۰. تفاوت light و dark

- light: زمینهٔ سبز-مه‌آلود، کارت روشن، teal action، amber change و coral critical.
- dark: زمینهٔ آبی-سبز عمیق، surfaceهای raised، teal روشن و semanticهای روشن. period toggle و route card نباید به surface سفید generic برگردند.
- overlay تصویر مقصد در هر theme باید title/status را خوانا کند.

## ۱۱. قواعد RTL و دسترسی‌پذیری

- breadcrumb، day tabs و metric labels RTL باشند؛ ساعت و واحدها خوانا و consistent باقی بمانند.
- tabs با role و `aria-selected`، toggle با `aria-pressed` و route links با نام کامل.
- legend رنگ‌ها متن داشته باشد.
- timestamp و stale بودن برای screen reader نیز قابل فهم باشد.

## ۱۲. معیار پذیرش

- ترتیب ده‌گانهٔ بخش‌ها در mobile و desktop با reference سازگار باشد.
- label بالای day tabs دقیقاً «انتخاب روز» باشد و heading/description تکراری forecast حذف شود.
- periodهای کاملاً گذشته از نظر بصری مثل ساعت‌های گذشته کم‌رنگ باشند؛ period جاری و بازهٔ آینده خوانایی عادی داشته باشند.
- عبارت و timestamp خام «آخرین به‌روزرسانی: ...» در UI وجود نداشته باشد.
- روزها قبل از weather controls در mobile قرار بگیرند.
- route picker/related routes فشرده، خوانا و بدون overflow باشد.
- forecast چهار‌تایی، metrics و هشدارها برای ready و partial-data قابل خواندن باشند.
- انتخاب روز/بازه state را حفظ و دادهٔ مرتبط را به‌روزرسانی کند.
- کاربر بتواند از route card به Route برسد و از آنجا context مقصد را از دست ندهد.

## ۱۳. تصویر مرجع

- [light/mobile](../screens/destination/light/mobile.png)
- [dark/mobile](../screens/destination/dark/mobile.png)
- [light/web](../screens/destination/light/web.png)
- [dark/web](../screens/destination/dark/web.png)

## ۱۴. موارد نامشخص و تصمیم‌های باز

- تعریف دقیق «آخرین به‌روزرسانی»، timezone و cadence provider باید قرارداد شود.
- ترتیب recommendation مسیرها و منطق «پیشنهاد هواچ» هنوز محصولی نشده است.
- مدل severity و thresholdهای باد/برف/دید نیازمند تصمیم domain است.
- نمایش route summary در mobile: قبل یا بعد از metrics باید با تست کاربر نهایی شود.
