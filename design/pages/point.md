# مشخصات صفحهٔ Point (Standalone WeatherPoint)

> **توجه:** برای این صفحه screenshot مرجع جداگانه در `design/screens` وجود ندارد. طراحی بصری این صفحه **همان الگوی Destination** با محتوای نقطه است؛ تصویر جدید بدون منبع معتبر ساخته یا جایگزین ۱۶ asset مرجع نمی‌شود.

## ۱. هدف صفحه و تصمیم کاربر

کاربر باید بتواند یک نقطهٔ هواشناسی مستقل (مثل «پس‌قلعه» یا «شیرپلا») را بدون ورود اجباری به یک مسیر خاص ببیند: وضعیت فعلی، پیش‌بینی روز/بازه، و در صورت نیاز مسیرهای مرتبط.

## ۲. هویت canonical

- URL عمومی: `/points/{weatherPointSlug}` — مثال: `/points/pas_ghaleh`؛ برای WeatherPointای که `kind=destination` دارد، canonical navigation باید به `/destination/{destinationSlug}` resolve شود.
- API: `GET /api/v1/points/{weather_point_slug}/forecast/?date=&period=`
- breadcrumb: برای نقطهٔ مستقل `مقصدها / {نام نقطه}` — **بدون** زنجیرهٔ مقصد→مسیر→نقطه؛ نقطه‌ای که هویت مقصد دارد باید خود صفحهٔ مقصد canonical را باز کند.
- لینک‌های timeline/cards مسیر باید URL تمیز `/points/{slug}` بدهند؛ بدون `date`/`period`/`start_time`/`speed` فقط برای حفظ planner context

## ۳. ترتیب بخش‌ها

۱. header
۲. (اختیاری) CTA بازگشت به مسیر — فقط وقتی از Route آمده
۳. breadcrumb و hero نقطه (نام، ارتفاع، مختصات)
۴. status pill خلاصه
۵. کارت پیش‌بینی هم‌خانواده با Destination: label «انتخاب روز»، day selector، period toggle، current reading، hourly
۶. (اختیاری) «مسیرهای مرتبط» به‌صورت لیست کارت‌های فشرده و تک‌ستونه وقتی مستقیم/refresh/share از Home آمده
۷. footer

## ۴. navigation و back

- از Route: `بازگشت به مسیر {route.title}` با `location.state.fromRoute` شامل مسیر و query کامل برنامه‌ریزی
- مستقیم/refresh/share/Home: بدون دکمهٔ back گمراه‌کنندهٔ مسیر؛ در صورت وجود، بخش «مسیرهای مرتبط»
- URL legacy `/routes/{route}/points/{point}` به canonical resolve/redirect می‌شود؛ `start_time` و `speed` در URL عمومی نقطه نمی‌آیند، اما برای back context نگه داشته می‌شوند.

## ۵. stateها

- loading / ready / empty / partial / error / stale — هم‌تراز Destination
- متن خام timestamp و عبارت داخلی `timing_pending` در UI نمایش داده نمی‌شود.
- نقطه بدون WeatherPoint فعال: بدون صفحهٔ standalone ساختگی

## ۶. light / dark و responsive

- کلاس‌های `point-page` / `point-shell` باید از token و componentهای Destination استفاده کنند.
- dark نباید به کارت سفید generic برگردد؛ کارت‌های مسیر مرتبط نیز باید surface و contrast همان theme را داشته باشند.
- اندازهٔ کارت‌های مسیر مرتبط نباید با grid سه‌ستونه در sidebar باریک و بلند شود.
- بدون overflow افقی در mobile/desktop
- RTL برای فارسی، مختصات، زمان، واحدها

## ۷. acceptance criteria

- [ ] URL canonical تمیز
- [ ] breadcrumb بدون route chain
- [ ] back CTA فقط با navigation state
- [ ] shared WeatherPoint یک صفحهٔ عمومی
- [ ] WeatherPoint مقصدی به صفحهٔ standalone موازی نرود و به Destination canonical هدایت شود
- [ ] ظاهر، رنگ، period controls و day selection با Destination یکسان باشد
- [ ] related routes compact و تک‌ستونه باشد
- [ ] label انتخاب روز جایگزین heading/description تکراری شود
- [ ] بدون ETA/ascent/speed/start-time روی صفحهٔ standalone
- [ ] theme dark/light درست
- [ ] بدون root overflow
