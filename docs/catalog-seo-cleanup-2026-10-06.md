# بازبینی پیوند و هویت نقاط — ۶ اکتبر ۲۰۲۶

این تغییر URL، canonical، timing یا ساختار مسیرهای موجود را عوض نمی‌کند و مدل
یا migration ندارد. برای اعمال metadata روی سایت، sync کاتالوگ لازم است؛
commit/push به‌تنهایی دیتابیس runtime را تغییر نمی‌دهد.

## ورودی واقعی برای دو مسیر

شاه‌ورس شرقی مقصد نهایی `blades-rakhsh-to-shahvars` و آبشار سیسنگان مقصد نهایی
`kojur-to-sisangan-waterfall` است. همان WeatherPointهای موجود به مقصد مستقل
`primary` / `importance=primary` / `seo_indexable=true` ارتقا یافتند. Hub، API و
SSR از دادهٔ runtime این دو را پیدا می‌کنند؛ لینک مستقیم از صفحهٔ مقصد به Route
با رابطهٔ واقعی RoutePoint ساخته می‌شود، نه نزدیکی جغرافیایی یا لینک hardcode.
آبشار سیسنگان با پارک ساحلی سیسنگان ادغام نشده و مسیر هم به پارک وصل نشده است.

## aliasهای مبهم

alias عمومی «هویر» برای روستا نگه داشته شد؛ دریاچه با «دریاچه هویر» و شکل‌های
انگلیسی مختص دریاچه شناخته می‌شود. alias «آبشار مسیر کجور به سیسنگان» فقط برای
آبشار انتهایی سیسنگان نگه داشته شد؛ آبشار میانی alias اختصاصی «آبشار خزه ای کجور»
دارد. نام‌ها، مختصات و URLهای این دو جفت عوض نشده‌اند.

## نقاط نزدیک

- گردنهٔ چالون اشتباهاً به یک نقطهٔ track نزدیک قله منتقل شده بود. مختصات خود
  waypoint «شن اسكی گردنه چالون» در GPX محلی منبع Wikiloc 141887696 برابر
  `36.382386, 50.988796` است؛ DEM در این مختصات ۴۴۲۳ متر است. فاصلهٔ آن با قله
  اکنون بیش از ۱۰۰ متر است؛ قله و گردنه دو هویت مستقل باقی می‌مانند.
- جان‌پناه دوشاخ و قله در ترک Wikiloc 48158952 دو waypoint مستقل با فاصلهٔ
  افقی حدود ۸۸ متر و اختلاف DEM برابر ۴۱ متر هستند. استثنای مستند برای این
  جفت ثبت شد؛ جان‌پناه همچنان noindex است.
- آبشارهای سوم، چهارم، ششم و هفتم در GPX منبع Wikiloc 268802470 waypoint و
  شمارهٔ مستقل دارند؛ سوم در منبع 243294044 نیز تأیید می‌شود. پنج جفت نزدیک
  در `reviewed_nearby_point_pairs` مستند شدند. نمایندهٔ هفت آبشار روی آبشار
  هفتم است؛ آبشارهای سوم، چهارم و ششم همچنان پشتیبان noindex هستند. نبود
  تفاوت DEM در یک grid دلیل یک‌عارضه‌بودن نیست.

شواهد محلی GPX فقط برای بازبینی استفاده شدند و وارد Git یا سرور نمی‌شوند.
استثناها آستانهٔ duplicate کمتر از ۲۵ متر را تغییر نمی‌دهند.

منابع هویت:

- https://www.wikiloc.com/hiking-trails/chkhd-syh-khmn-siyah-kaman-141887696
- https://www.wikiloc.com/mountaineering-trails/qlh-dw-shkh-w-syh-sng-z-drkhh-48158952
- https://www.wikiloc.com/hiking-trails/abshr-7-gnh-shyrabd-268802470
- https://www.wikiloc.com/hiking-trails/mjmwh-abshrhy-shyrabd-gr-dyw-spyd-shhrstn-khn-bbyn-shirabad-waterfall-243294044
- https://api.open-meteo.com/v1/elevation?latitude=36.382386&longitude=50.988796

کنترل رگرسیون در `apps/api/tests/test_catalog_seo_cleanup.py`: alias collision،
مختصات گردنه، گراف کامل لینک‌ها، SSR مقصد/مسیر، sitemap و باقی‌ماندن noindexها؛
duplicate واقعی حتی با داشتن استثنای curator همچنان خطاست.
