# مشخصات صفحهٔ Point

> **بازنشسته.** قالب بصری مستقل Point وجود ندارد.

محتوای رفتاری و acceptance به قالب مشترک منتقل شده است:

- [place-forecast.md](./place-forecast.md) — قالب پیش‌بینی نقطه
- [point-forecast.md](./point-forecast.md) — baseline بصری و کنترل‌ها
- [docs/page-specs/point-behavior.md](../../docs/page-specs/point-behavior.md) — فقط تفاوت‌های محتوایی URL نقطه

URL عمومی `/points/{weatherPointSlug}` برای همهٔ نقطه‌هاست و همان
`PlaceForecastPage` را رندر می‌کند؛ هر نقطه با شناسهٔ canonical خودش لینک می‌شود.
