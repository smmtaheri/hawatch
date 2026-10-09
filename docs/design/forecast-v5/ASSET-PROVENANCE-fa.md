# دارایی‌های بستهٔ v5

- `reference/site/` کپی دقیق dist نسخه۳۳ سایت تأییدشده است؛ SHA-256 هر فایل در `docs/source-provenance.json` ثبت شده. منبع اصلی font/token/icon/background برای frontend همین مسیر است.
- `assets/fonts/`: Vazirmatn Regular و Bold در WOFF2/TTF، مجوز OFL محفوظ ازv4. داخل محصول همان نسخهٔ موجود را استفاده کنید، فونت جدید جایگزین نشود.
- `assets/backgrounds/`: هشت تصویر اصلی مقصد/مسیر × موبایل/دسکتاپ × روشن/تاریک با bytes قبلی حفظ شده‌اند.
- `assets/share-backgrounds/`: روشن و تاریک اصلیِ خروجی مسیر حفظ شده‌اند؛ تصویری دوباره ساخته نشده است.
- `assets/icons/ui/`, `equipment/`, `weather/`: SVGهای جاری استخراج‌شده از همان mapهای کد مرجع؛ currentColor، وزن و viewBox حفظ شده. هندسهٔ expand/collapse۲۴ و کوهنورد/chevron۶۴ است؛ تفاوت viewBox را با stroke ثابت CSS روی route badge کنترل کنید.
- `reference/site/assets/icons.js`: map آیکون‌های اصلی. `HW_BRAND` و categoryهای اصلی در `catalog-data.js` هستند؛ `assets/icons/brand/hawatch.svg` کپی logo برای استفادهٔ مستقیم است.
- `equipment/photos/`:۳۵عکس واقعی بدون دستکاری ازv4، URL منبع و bytes/حقوق درcatalog/ATTRIBUTION؛ جست‌وجوی قبلی مجدداً اجرا نشده. این تصاویر مرجعند، UI اصلی SVG خطی است.
- تصاویر `screens/` از renderer محلی با source جاری ثبت شده‌اند؛ PNGهای `export/` از canvas واقعی همان منطق share، Telegram از همانPNG، بدون imagegen.

فایل `docs/icons-sheet.html` همهٔ SVGها را برای مرور نشان می‌دهد. گزارش `source-provenance.json` دقیقاً مشخص می‌کند کدام فایل باv4 byte-identical باقی مانده و کدام از source فعلی استخراج/به‌روز شده است. فایل reference JS آزمایشی قدیمی درv5 حذف شده تا چند مرجع متفاوت باقی نمانند.
