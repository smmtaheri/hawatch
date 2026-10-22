# مرجع اجرای شاخص‌ها

۱۶ PNG ثبت‌شده از implementation واقعی، نه image generation یا تزریق دادهٔ
نمایشی در فرانت: موبایل ۴۳۰px و دسکتاپ ۱۶۰۰px، روشن/تاریک، روزانه و ۶/۳/۱
ساعته. روز دوم باز می‌شود و روزهای دیگر روزانه می‌مانند. دادهٔ API از DB
موقت synthetic آمده است؛ گرمای تصاویر پیش‌بینی واقعی توچال نیست.

برای تکرار با یک Chrome موقت دارای CDP روی 9416 و stack محلی روی 5173:

```bash
node scripts/check-forecast-indicators.mjs
```

اسکریپت فقط origin محلی را می‌پذیرد و همهٔ درخواست‌های غیر GET و analytics را
مسدود می‌کند. فایل `verification.json` گواه مقایسهٔ DOM نمودارهای قبلی با
مینِ مرجع `ba32388`، نبود overflow، حفظ اسکرول عمودی، عرض‌های ۳۲۰/۳۶۰ و یک GET هوا در
هر مرورگر است. ردیف‌های UV و گرما و جفت min/max از خود API/renderer می‌آیند.
PNGها بدون resize، فشرده‌سازی یا بازکدگذاری نگهداری شده‌اند.

نمونه‌ها: [موبایل روشن، ۶ساعته](mobile-light-6h.png)،
[موبایل تاریک، ۱ساعته](mobile-dark-1h.png)،
[دسکتاپ تاریک، روزانه](desktop-dark-24h.png)،
[دسکتاپ روشن، ۳ساعته](desktop-light-3h.png).

در پیگیری فشرده‌سازی ردیف‌ها، خوانایی ساقه‌های باد سبک و نمایش گسستهٔ freezing
level، تصویرهای browser fixture با دادهٔ synthetic در
[موبایل](../forecast-indicators-fix/mobile-dark-density.png) و
[دسکتاپ](../forecast-indicators-fix/desktop-dark-density.png) ثبت شده‌اند.
این اعداد نمایشی‌اند و پیش‌بینی واقعی هوا را نشان نمی‌دهند.
