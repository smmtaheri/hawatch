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
۶. انتخاب روز.
۷. بخش مسیرها.
۸. انتخاب صبح/بعدازظهر.
۹. پیش‌بینی ساعتی شش‌تایی.
۱۰. جزئیات تخصصی.
۱۱. در web، decision card و خلاصهٔ مسیر در جایگاه side قرار می‌گیرند؛ در mobile به ترتیب خواندن تصمیم نزدیک داده می‌مانند.

## ۴. hierarchy کامپوننت‌ها

`DestinationPage → SiteHeader + DestinationHero(StatusPill[]) + DestinationLayout → WeatherCard(DayTabs, RoutePicker, DaypartToggle, HourlyForecast) + TechnicalMetrics + RouteSummary/DecisionCard`.

## ۵. رفتار کنترل‌ها

- back: به Home و context قبلی می‌رود.
- breadcrumb: مقصدها به Home، نام مقصد current و غیرقابل کلیک.
- day tabs: forecast و route recommendations را برای روز انتخابی refresh می‌کند.
- مسیرها: مسیر انتخابی را active می‌کند و به Route می‌برد یا data context صفحه را تغییر می‌دهد.
- صبح/بعدازظهر: hourly forecast و وضعیت نقاط مرتبط را عوض می‌کند.
- cardهای route: detail route را باز می‌کنند.
- theme toggle: theme را تغییر می‌دهد، بدون reset کردن destination/day/period.

## ۶. stateهای loading، ready، empty، error، stale و partial-data

- loading: hero می‌تواند اطلاعات پایه را حفظ کند و weather card skeleton داشته باشد.
- ready: status، روزها، مسیرها، شش ساعت و metrics کامل نمایش داده شوند.
- empty: برای روز یا مسیر بدون forecast پیام و جایگزین قابل اقدام نمایش داده شود.
- error: شکست provider یا API داخلی با retry، زمان آخرین موفقیت و back path.
- stale: timestamp و stale badge؛ تصمیم حساس نباید بدون هشدار از دادهٔ قدیمی نتیجه‌گیری کند.
- partial-data: مثلاً hourly موجود ولی wind gust ناقص است؛ بخش موجود نمایش داده شود و metric ناقص به‌وضوح مشخص شود.

## ۷. داده‌های موردنیاز

- مقصد: slug، نام، category، مختصات، elevation و hero asset.
- وضعیت فعلی: condition، temperature، wind، visibility و fetched/valid times.
- forecast روزانه و hourly شش‌تایی.
- route catalog همان مقصد.
- metrics تخصصی مثل gust، freezing level، cloud base، UV، precipitation و sunrise/sunset.
- هشدارها با severity normal/change/critical.

## ۸. APIهای آینده

- `GET /api/v1/destinations/{slug}`
- `GET /api/v1/destinations/{slug}/forecast?date={date}&period={period}`
- `GET /api/v1/destinations/{slug}/routes`
- `GET /api/v1/destinations/{slug}/alerts?date={date}`

تمام این‌ها API داخلی‌اند و backend آینده provider را پشت خود پنهان می‌کند.

## ۹. تفاوت mobile و web

- mobile: روزها قبل از کنترل هوا باشند؛ مسیرها دو ستونه و کوچک؛ عنوان بخش فقط «مسیرها»؛ کنترل morning/afternoon کوتاه؛ cardها viewport را overflow ندهند.
- web: weather card و side route summary می‌توانند دو ستون باشند؛ شش ساعت در یک ردیف خوانا بماند.
- timeline و cardها در mobile باید به ترتیب تصمیم خوانده شوند، نه بر اساس grid desktop.

## ۱۰. تفاوت light و dark

- light: زمینهٔ سبز-مه‌آلود، کارت روشن، teal action، amber change و coral critical.
- dark: زمینهٔ آبی-سبز عمیق، surfaceهای raised، teal روشن و semanticهای روشن.
- overlay تصویر مقصد در هر theme باید title/status را خوانا کند.

## ۱۱. قواعد RTL و دسترسی‌پذیری

- breadcrumb، day tabs و metric labels RTL باشند؛ ساعت و واحدها خوانا و consistent باقی بمانند.
- tabs با role و `aria-selected`، toggle با `aria-pressed` و route links با نام کامل.
- legend رنگ‌ها متن داشته باشد.
- timestamp و stale بودن برای screen reader نیز قابل فهم باشد.

## ۱۲. معیار پذیرش

- ترتیب ده‌گانهٔ بخش‌ها در mobile و desktop با reference سازگار باشد.
- روزها قبل از weather controls در mobile قرار بگیرند.
- route picker دو ستونه و بدون overflow باشد.
- forecast شش‌تایی، metrics و هشدارها برای ready و partial-data قابل خواندن باشند.
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
