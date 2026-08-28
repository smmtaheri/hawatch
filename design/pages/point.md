# مشخصات صفحهٔ Point (Standalone WeatherPoint)

> **توجه:** برای این صفحه screenshot مرجع جداگانه در `design/screens` وجود ندارد. طراحی بصری این صفحه **extension محصول** از design system صفحهٔ Destination است، نه ادعای تطابق با تصویر مرجع موجود.

## ۱. هدف صفحه و تصمیم کاربر

کاربر باید بتواند یک نقطهٔ هواشناسی مستقل (مثل «پس‌قلعه» یا «شیرپلا») را بدون ورود اجباری به یک مسیر خاص ببیند: وضعیت فعلی، پیش‌بینی روز/بازه، و در صورت نیاز مسیرهای مرتبط.

## ۲. هویت canonical

- URL عمومی: `/points/{weatherPointSlug}` — مثال: `/points/pas_ghaleh`
- API: `GET /api/v1/points/{weather_point_slug}/forecast/?date=&period=`
- breadcrumb: `مقصدها / {نام نقطه}` — **بدون** زنجیرهٔ مقصد→مسیر→نقطه
- لینک‌های timeline/cards مسیر باید URL تمیز `/points/{slug}` بدهند؛ بدون `date`/`period`/`start_time`/`speed` فقط برای حفظ planner context

## ۳. ترتیب بخش‌ها

۱. header
۲. (اختیاری) CTA بازگشت به مسیر — فقط وقتی از Route آمده
۳. breadcrumb و hero نقطه (نام، ارتفاع، مختصات)
۴. status pill خلاصه
۵. کارت پیش‌بینی: day selector، period toggle، current reading، hourly
۶. (اختیاری) «مسیرهای مرتبط» وقتی مستقیم/refresh/share از Home آمده
۷. footer

## ۴. navigation و back

- از Route: `بازگشت به مسیر {route.title}` با React Router `location.state.fromRoute`
- مستقیم/refresh/share/Home: بدون دکمهٔ back گمراه‌کنندهٔ مسیر؛ در صورت وجود، بخش «مسیرهای مرتبط»
- URL legacy `/routes/{route}/points/{point}` باید به canonical resolve/redirect شود؛ planner params (`start_time`, `speed`) حذف شوند

## ۵. stateها

- loading / ready / empty / partial / error / stale — هم‌تراز Destination
- نقطه بدون WeatherPoint فعال: بدون صفحهٔ standalone ساختگی

## ۶. light / dark و responsive

- کلاس‌های `point-page` / `point-shell` با theme parity
- dark نباید به کارت سفید generic برگردد
- بدون overflow افقی در mobile/desktop
- RTL برای فارسی، مختصات، زمان، واحدها

## ۷. acceptance criteria

- [ ] URL canonical تمیز
- [ ] breadcrumb بدون route chain
- [ ] back CTA فقط با navigation state
- [ ] shared WeatherPoint یک صفحهٔ عمومی
- [ ] بدون ETA/ascent/speed/start-time روی صفحهٔ standalone
- [ ] theme dark/light درست
- [ ] بدون root overflow
