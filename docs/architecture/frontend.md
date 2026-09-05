# معماری frontend هواچ

## انتخاب

- React + TypeScript
- Vite
- React Router
- pnpm workspace در ریشهٔ repository
- CSS از tokenهای canonical به‌علاوهٔ stylesheet منطبق با live visual contract

Tailwind به‌عنوان dependency اضافه نشده است. هویت بصری از `design/tokens/visual-tokens.json` و CSS مرجع صفحه‌های live پیروی می‌کند.

## مرزبندی

frontend فقط `VITE_API_BASE_URL` را صدا می‌زند. لایهٔ client در `apps/web/src/api/` است. componentها catalog یا forecast را hard-code نمی‌کنند.

برای SEO، gateway درخواست‌های Home و URLهای canonical Point/Route را به Django
می‌فرستد تا `title`، metaها و fallback معنایی از دیتابیس runtime قبل از اجرای
JavaScript در HTML حاضر باشند. React همچنان پس از load شدن bundle همان SPA را
render می‌کند؛ جزئیات در [`../seo.md`](../seo.md) است. entryهای build با نام
پایدار تولید می‌شوند تا template Django به hashهای Vite وابسته نباشد.

## theme و RTL

- `dir=rtl` و `lang=fa`
- فونت self-hosted و متغیر Estedad با stack مشترک `"Estedad", "Noto Sans Arabic", Tahoma, Arial, sans-serif`؛ تعریف `@font-face` در `apps/web/src/styles/tokens.css` و asset در `apps/web/public/fonts/`
- theme با `data-theme` و `localStorage` key `hawatch-theme`
- تغییر theme انتخاب روز/بازه/مسیر را reset نمی‌کند

## صفحات این milestone

- `/`
- `/points/:slug` — `PlaceForecastPage` (قالب مشترک Point Forecast)
- `/routes/:slug`

Home از search index داخلی، پیشنهادهای همهٔ نقاط را با debounce و keyboard navigation مصرف می‌کند. کلیک روی point به URL تمیز `/points/{pointSlug}` می‌رود و context بازگشت Route فقط در React Router state نگه داشته می‌شود.

Login به‌صورت route-backed پیاده شده است؛ در وضعیت فعلی یک flow آزمایشی محدود frontend با شمارهٔ مجاز، کد ثابت و session یک‌ماهه دارد. OTP واقعی و احراز هویت backend هنوز باید جداگانه طراحی شوند.
