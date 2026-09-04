# SEO و HTML اولیهٔ عمومی

## هدف

Home، تمام Pointهای عمومی در `/points/<slug>` و تمام Routeهای فعال در
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

همان HTML برای crawler و کاربر عادی ارسال می‌شود؛ تشخیص bot یا user-agent وجود
ندارد. سپس bundle فعلی React از `/assets/hawatch.js` اجرا می‌شود و تجربهٔ SPA
را بدون تغییر ادامه می‌دهد. Vite مسیرهای entry CSS/JS را پایدار (`hawatch.css`
و `hawatch.js`) می‌سازد تا Django به hashهای build وابسته نباشد؛ chunkهای داخلی
همچنان hashدار هستند.

این یک SSR کامل React نیست: Django فقط shell معنایی اولیه و head را render
می‌کند. مزیت آن این است که دادهٔ اولیه مستقیم از منبع حقیقت runtime می‌آید و
اضافه‌شدن یا ویرایش یک Point/Route از طریق catalog sync یا Admin، بدون hardcode
URL و بدون prerender مجدد، در HTML اولیه هم منعکس می‌شود.

## رفتار URL

| وضعیت | status | robots | canonical |
| --- | --- | --- | --- |
| URL تمیز Home/Point/Route | 200 | `index,follow` | همان URL تمیز |
| همان URL با query | 200 | `noindex,follow` | همان URL بدون query |
| slug نامعتبر Point/Route | 404 | `noindex,follow` | ندارد |

`X-Robots-Tag` نیز با meta robots هم‌راستاست. پاسخ‌های HTML با
`Cache-Control: no-cache` برمی‌گردند تا تغییرات کاتالوگ با revalidation دیده شوند.

## بررسی محلی پس از build

برای HTML اولیه از gateway Compose استفاده کنید، نه Vite dev server؛ Vite dev
server صرفاً برای توسعهٔ SPA است:

```bash
curl -fsS http://localhost/points/tochal | sed -n '1,80p'
curl -fsS 'http://localhost/routes/tochal-darband?date=2026-09-04&period=morning' | sed -n '1,80p'
curl -i http://localhost/points/not-a-real-point
```

در deploy کد، imageهای `api` و `web` باید طبق روند عادی build شوند؛ تغییر
catalog به‌تنهایی به build یا restart نیاز ندارد. پس از `sync_catalog --apply`
یک Point یا Route جدید بلافاصله HTML اولیهٔ اختصاصی خود را از همین renderer
می‌گیرد.
