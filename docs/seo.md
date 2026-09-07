# SEO و HTML اولیهٔ عمومی

## هدف

Home، indexهای عمومی `/points` و `/routes`، تمام Pointهای عمومی در `/points/<slug>` و تمام Routeهای فعال در
`/routes/<slug>` باید پیش از اجرای JavaScript یک HTML معنادار و قابل‌خزش داشته
باشند. canonical هر صفحه همیشه URL تمیز و بدون query است. URLهای queryدارِ
planner، مانند `?date=…&period=…`، با `noindex,follow` منتشر می‌شوند تا لینک‌ها
دنبال شوند اما نسخه‌های پارامتردار وارد نتایج گوگل نشوند.

## معماری

Nginx gateway این سه surface عمومی را به Django می‌فرستد. viewهای
`hawatch.modules.catalog.seo_pages` از دیتابیس runtime می‌خوانند و در HTML اولیه
موارد زیر را می‌سازند:

- `title`، `meta description`، `canonical` و `robots`؛
- یک `h1` و خلاصهٔ معنادار؛
- برای Point: منطقه، دسته‌بندی، ارتفاع و مسیرهای مرتبط؛
- برای Route: مبدأ، مقصد، مسافت/صعود و زنجیرهٔ نقاط مسیر.
- اگر ForecastRecord واقعی در runtime وجود داشته باشد، نزدیک‌ترین دما و وضعیت نیز در fallback اولیهٔ همان صفحه می‌آید؛ در نبود داده هیچ مقدار حدسی نوشته نمی‌شود.
- برای indexها: فهرست دسته‌بندی‌شده با لینک واقعی `<a href>` به همهٔ آیتم‌های عمومی.

همان HTML برای crawler و کاربر عادی ارسال می‌شود؛ تشخیص bot یا user-agent وجود
ندارد. سپس bundle فعلی React از `/assets/hawatch.js` اجرا می‌شود و تجربهٔ SPA
را بدون تغییر ادامه می‌دهد. Home در هر دو لایه دقیقاً یک `h1` دارد. Vite مسیرهای entry CSS/JS را پایدار (`hawatch.css`
و `hawatch.js`) می‌سازد تا Django به hashهای build وابسته نباشد؛ chunkهای داخلی
همچنان hashدار هستند. چون نام این دو entry پایدار است، web Nginx آن‌ها را با
`Cache-Control: no-store, no-cache, must-revalidate, max-age=0` پاسخ می‌دهد: browser و CDN
نباید نسخهٔ قبلی را نگه دارند و navigation بعدی فایل تازه را می‌گیرد.

این یک SSR کامل React نیست: Django فقط shell معنایی اولیه و head را render
می‌کند. مزیت آن این است که دادهٔ اولیه مستقیم از منبع حقیقت runtime می‌آید و
اضافه‌شدن یا ویرایش یک Point/Route از طریق catalog sync یا Admin، بدون hardcode
URL و بدون prerender مجدد، در HTML اولیه هم منعکس می‌شود.

## copy پویا و override اختیاری

`modules/catalog/seo.py` تنها سازندهٔ عمومی copy است. Point از نام canonical،
نوع عارضهٔ فارسی، ارتفاع، منطقه و فقط بازهٔ forecast واقعاً ذخیره‌شده استفاده
می‌کند؛ بنابراین دریاچه، جنگل و کویر هرگز «قله» نامیده نمی‌شوند و مدت یا منبع
نداشته ساخته نمی‌شود. Route از عنوان، مبدأ/مقصد، مسافت و زمان یک‌طرفهٔ ثبت‌شده
استفاده می‌کند.

برای copy واقعاً curated، بلوک اختیاری زیر در همان row Point یا Route catalog و
همان فیلدها در Django Admin وجود دارد. همهٔ فیلدها اختیاری‌اند؛ خالی‌بودن یعنی
قالب عمومی پویا، نه متن تکراریِ backfill‌شده:

```json
"seo": {
  "title": "عنوان یکتا | هواچ",
  "description": "توضیح کوتاه و مبتنی بر دادهٔ مستند.",
  "content": "متن تکمیلی کوتاه با واقعیت قابل‌اتکا."
}
```

`content` فقط در صورت وجود به‌شکل accordion پایین HTML اولیه دیده می‌شود؛ متن
پنهان ویژهٔ موتور جست‌وجو نداریم. validator catalog نوع، طول، کلید ناشناخته،
title تکراری و تکرار غیرطبیعی keyword را رد می‌کند. زیر H1 در HTML و React فقط
یک subtitle کوتاه است. `BreadcrumbList` تنها schema این مرحله است و صرفاً
URLهای canonical واقعی را بازتاب می‌دهد.

`sync_catalog --apply` overrideهای catalog را اتمیک وارد می‌کند. Point/Route
جدید بدون URL hardcode یا prerender/build جدا، title/description/subtitle عمومی،
sitemap و لینک index را خودکار می‌گیرد؛ migration فقط برای ذخیرهٔ override لازم
است.

## indexability نقاط فنی

`seo_indexable` در هر row از Catalog منبع سیاست discoverability است. مقدار
`false` نقطه را حذف یا غیرفعال نمی‌کند: WeatherPoint فعال همچنان در زنجیرهٔ
Route، جست‌وجوی داخلی، API و ingest/forecast باقی می‌ماند. فقط صفحهٔ مستقل آن
با status 200 و canonical تمیز، `noindex,follow` و `X-Robots-Tag` متناظر می‌گیرد
و از sitemap کنار گذاشته می‌شود. فهرست و لینک‌های داخل اپ همچنان همهٔ نقاط فعال
را نشان می‌دهند تا مسیر، جست‌وجو و timeline بدون تغییر کار کنند. View خود نقطه
از query عمومی جداست تا این URL همچنان برای timeline مسیر قابل بازشدن باشد.

Policy مرکزی برای point typeهای فنی (`parking`، `spring`، `pass`، `ridge`،
`trailhead` و `technical_point`) وقتی flag حذف شده باشد، noindex را پیش‌فرض
می‌کند. استثناهای واقعی مانند ایستگاه تله‌کابین، پناهگاه معروف یا مبدأی که
خودش مقصد مستقل است باید در Catalog صریحاً `seo_indexable: true` داشته باشند.
این resolution در seed و `sync_catalog` مشترک است و syncهای بعدی flag را
برنمی‌گردانند. Duplicate بررسی‌شده باید یک slug canonical داشته باشد؛ تا وقتی
هم‌هویتی با مختصات/منبع ثابت نشده، رکوردها حذف یا redirect نمی‌شوند.

Attribution فقط یک متن کوچک `دادهٔ هواشناسی: Open-Meteo` در footer است؛ منبع و
زمان به‌روزرسانی داخل کارت‌های forecast یا محتوای اصلی قرار نمی‌گیرد.

## رفتار URL

| وضعیت | status | robots | canonical |
| --- | --- | --- | --- |
| URL تمیز Home/Point/Route | 200 | `index,follow` | همان URL تمیز |
| URL تمیز index نقاط/مسیرها | 200 | `index,follow` | همان URL تمیز |
| همان URL با query | 200 | `noindex,follow` | همان URL بدون query |
| slug نامعتبر Point/Route | 404 | `noindex,follow` | ندارد |

`X-Robots-Tag` نیز با meta robots هم‌راستاست. پاسخ‌های HTML با
`Cache-Control: no-cache` برمی‌گردند تا تغییرات کاتالوگ با revalidation دیده شوند.
در Route تمیز، تاریخ/بازه/سرعت/ساعت پیش‌فرض فقط در state React قرار می‌گیرند و
به URL نوشته نمی‌شوند؛ با اولین تغییر واقعی کاربر query به URL اضافه و صفحه
`noindex,follow` می‌شود. canonical در هر دو حالت بدون query می‌ماند و React با
تغییر navigation، meta robots را دوباره محاسبه می‌کند.

کدهای داخلی `place_type` در HTML عمومی نمایش داده نمی‌شوند. mapping مرکزی
`PLACE_TYPE_LABELS` در `modules/catalog/identity.py` آن‌ها را به برچسب فارسی
تبدیل می‌کند و برای مقدار ناشناخته از «عارضهٔ ثبت‌شده» استفاده می‌شود.
صفحهٔ Point فقط به Routeهایی لینک می‌دهد که نقطه واقعاً عضو زنجیره یا مبدأ/مقصد
آن Route فعال باشد. برای Point اصلیِ یک مقصد، تطبیق دقیق `target_label` با نام
کانونیکال مقصد نیز مجاز است تا مقصدهایی مثل دریاچهٔ گهر که endpoint فیزیکیِ
جداگانه دارند از مسیرهای واقعی خود جدا نشوند؛ رابطهٔ محتواییِ حدسی ساخته نمی‌شود.

## تنظیم CDN و cache

اگر CDN یا reverse proxy بیرونی جلوی gateway قرار دارد، این قواعد را اعمال کنید:

- `/`، `/points/*` و `/routes/*` را cache نکنید (`Cache-Control: no-cache` را
  عبور دهید) و query string را در cache key نگه ندارید؛ canonical خود HTML بدون
  query است اما queryها باید `noindex,follow` بمانند.
- `/admin/*` و `/api/*` خصوصی/پویا هستند و نباید در cache عمومی ذخیره شوند؛ هدر
  `Cache-Control: private, no-store` را برای Admin حفظ کنید.
- chunkهای hashدارِ `/assets/chunks/*` و فونت/برند versioned را می‌توان با
  `public, max-age=31536000, immutable` cache کرد. دو entry پایدار
  `/assets/hawatch.css` و `/assets/hawatch.js` نباید immutable یا با TTL بلند
  cache شوند؛ header origin آن‌ها باید عبور کند. پس از deploy این تغییر، یک‌بار
  cache قدیمی همین دو URL را در CDN purge کنید تا clientهای cache‌شده فوراً
  نسخهٔ جدید را بگیرند.
- `/robots.txt` و `/sitemap.xml` عمومی‌اند ولی پویا هستند؛ cache کوتاه (حداکثر
  چند دقیقه) یا revalidation فعال بگذارید و آدرس کامل sitemap را نگه دارید.

gateway فعلی cache داخلی ندارد و هدر no-cache Django را عبور می‌دهد؛ این قواعد
برای CDN بیرونیِ production است و به deploy یا تغییر catalog وابسته نیست.

## بررسی محلی پس از build

برای HTML اولیه از gateway Compose استفاده کنید، نه Vite dev server؛ Vite dev
server صرفاً برای توسعهٔ SPA است:

```bash
curl -fsS http://localhost/points/tochal | sed -n '1,80p'
curl -fsS http://localhost/points | sed -n '1,100p'
curl -fsS http://localhost/routes | sed -n '1,100p'
curl -fsS 'http://localhost/routes/tochal-darband?date=2026-09-04&period=morning' | sed -n '1,80p'
curl -i http://localhost/points/not-a-real-point
```

در deploy کد، imageهای `api` و `web` باید طبق روند عادی build شوند؛ تغییر
catalog به‌تنهایی به build یا restart نیاز ندارد. پس از `sync_catalog --apply`
یک Point یا Route جدید بلافاصله HTML اولیهٔ اختصاصی خود را از همین renderer
می‌گیرد.
