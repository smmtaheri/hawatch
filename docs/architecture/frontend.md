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

Login پیاده نشده است.
