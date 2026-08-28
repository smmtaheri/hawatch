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
- فونت Vazirmatn
- theme با `data-theme` و `localStorage` key `hawatch-theme`
- تغییر theme انتخاب روز/بازه/مسیر را reset نمی‌کند

## صفحات این milestone

- `/`
- `/destination/:slug`
- `/routes/:slug`
- `/points/:weatherPointSlug` — صفحهٔ مستقل WeatherPoint با URL canonical

Home از search index داخلی، پیشنهادهای مقصد و نقطهٔ مسیر را با debounce و keyboard navigation مصرف می‌کند. کلیک روی نقطهٔ مسیر به URL تمیز `/points/{slug}` می‌رود و context بازگشت Route را در React Router state نگه می‌دارد.

Login پیاده نشده است.
