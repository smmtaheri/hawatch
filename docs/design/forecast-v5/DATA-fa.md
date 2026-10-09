# قرارداد دادهٔ هفته و نگاشت به رابط

## پاسخ یک‌باره

برای هر مقصد/مسیر یک پاسخ کامل هفته دریافت و cache کنید: **۸ تاریخ محلی، امروز و۷روز بعد**. metadata لازم: `schema_version`, `snapshot_id`, `issued_at`, `time_zone`, `units`. در محصول `expires_at` و revision هوا/هندسه هم اضافه شود. کلیک روز، هر۶/۳/۱ساعت، جزئیات، زمان شروع و سرعت، دادهٔ جدیدِ هوا دریافت نمی‌کند. فقط ورود به مقصد/مسیر جدید یا refresh واقعی snapshot درخواست تازه دارد.

در مرجع، فایل `reference/site/assets/forecast-week.js` یک‌بار لود می‌شود. همان payload کامل به‌صورت JSON در `demo-data.json` است:۳۸مقصد،۴مسیر و۱۱۲۴۸رکورد بازهٔ مقصد. این داده ثابت و ساختگی است، `demo_only:true` دارد و برای استفادهٔ هواشناسی زنده نیست. تاریخ fixture از۲۰۲۶-۱۰-۰۷ است؛ «امروز» در محصول باید از تاریخ محلی پاسخ معتبر بیاید.

## مقصد

`points[slug].days[]` به‌ترتیب راست به چپ در UI:

| فیلد | معنا |
|---|---|
| `id` | شناسهٔ روز |
| `iso` | تاریخ محلی ISO |
| `name` | امروز/فردا/نام روز |
| `date_fa` | تاریخ فارسی؛ نمایش زیر روز |
| `available` | resolutionهای واقعی قابل ارائه |
| `intervals.daily` |۱رکورد |
| `intervals['6h']` |۴رکورد ساعت۰/۶/۱۲/۱۸ |
| `intervals['3h']` |۸رکورد ساعت۰/۳/…/۲۱ |
| `intervals['1h']` |۲۴رکورد ساعت۰..۲۳ |

فیلد `hour` برای روزانه null و بقیه عدد ساعت محلی است. برای API محصول `start_at/end_at` با timezone/offset مشخص ارائه شود تا دامنهٔ هر aggregation مبهم نباشد. نباید صرفاً آرایه را تکثیر کرد و روزانه را ساعتی جلوه داد؛ اگر API finer را ندارد، `available` آن را حذف کند و کنترل مناسب مخفی شود.

| فیلد مقدار | واحد/تفسیر |
|---|---|
| `felt` | دمای حسی °C |
| `actual` | دمای واقعی/مطلق °C |
| `min`, `max` | کمینه/بیشینهٔ همان بازه °C؛ برای instant ساعتی null |
| `wind` | km/h با قرارداد mean/instant معتبر provider |
| `gust` | km/h بیشینهٔ بازه، با مقیاس مشترک باد |
| `rain` | mm مجموع **همان بازه**، نه احتمال درصدی |
| `direction` | درجه از شمال، جهت «از کجا می‌وزد»، بازه۰..۳۵۹ |
| `humidity` | درصد۰..۱۰۰ |
| `visibility` | km |
| `freezing` | ارتفاع تراز صفر درجه برحسب m AMSL؛ یک معیار، نه دو ردیف تکراری |
| `weather` | کلید معتبر icon map، unknown برای نبود وضعیت |
| `hazards` | آرایهٔ معیارهای علت هشدار قرمز، مانند `felt`, `wind` |

عدد صفر معتبر است؛ `null` نبود داده است. frontend با `Number.isFinite` و نگاشت icon امن کار کند. NaN/Infinity در SVG وارد نشود. رنگ گرم/سرد از علامت دماست؛ خطر از `hazards` معتبر محصول است. معنی aggregate هر معیار را backend/provider تعیین کند؛ frontend threshold خطر و min/max ساختگی نسازد.

## مسیر

fixture فعلی `routes[slug]` شامل `distance_km`, `ascent_m`, `descent_m`, `distances_km`, `days[]` است. `days[i].local_date` و `hourly_points[hour][pointIndex]` تمام هفته/تمام نقاط را پوشش می‌دهد. ترتیب matrix دقیقاً همان `record.points` در `catalog-data.js` است؛ آداپتور محصول ترتیب را با pointId تضمین کند، نه اینکه آرایهٔ مرتب‌نشدهٔ پاسخ را مستقیم رسم کند.

برای پاسخ تولیدی، meta نقطه‌ها و geometry revision، cumulativeDistance و itinerary معتبر هم در payload/کاتالوگ cache باشند. فاصله و صعود/فرود fixture نمونه‌اند و منبع اندازه‌گیری مسیر نیستند. کل مسیر هیچ سقف۵/۹/۲۲نقطه‌ای ندارد؛ routeهای واقعی این پیش‌نمایش۶/۶/۱۰/۸نقطه‌اند.

محاسبهٔ مرجع:

```text
arrivalMinutes = startMinutes + round(offsetMinutes[point] * demoSpeedFactor)
arrivalDay = selectedDay + floor(arrivalMinutes / 1440)
hour = floor((arrivalMinutes % 1440) / 60)
values = snapshot.days[arrivalDay]?.hourly_points[hour]?.[point]
```

زمان رسیدن دقیق نقطه نمایش داده می‌شود ولی مقدار هوا در fixture از ساعت containing خوانده می‌شود؛ این رفتار interpolation نیست. در محصول sampling/interval معتبر و روزبعد از timezone payload استفاده کند. زمانی بعد از horizon، مقدارهای هوا null است و خلاصهٔ itinerary همچنان زمان معتبر خودش را دارد. backend می‌تواند همهٔ پروفایل‌های سرعت معتبر را همراه payload بدهد؛ API هوا به‌ازای کلیک لازم نیست. ضرایب۱.۳/۱/.۸ صرفاً دمو هستند.

## state فرانت

مقصد: `resolutionByDay`, `expertOpen`, `scrollAnchor`. مسیر: `selectedDate`, `startMinutes`, `speed`, `gearOpen`, `dateScroll`, `timelineScroll`. theme جدا از forecast data است. modal/export از یک RouteSnapshot immutable برای همان انتخاب ساخته شود تا هنگام کار async، عکس/لینک از دو state متفاوت نیایند.

Loading یک‌بار در انتظار payload، error با retry، no-data با پیام کوتاه، gap با `—` و شکستن خط، unsupported با نبود دکمهٔ finer. abort پاسخ صفحهٔ قبلی، dedup refresh و حفظ last-good snapshot در شکست refresh با وضعیت روشن دادهٔ قدیمی در محصول طراحی شود؛ fixture فعلی این سیاست شبکه را پیاده نکرده است.

## اتصال API موجود

`data-contract.ts` شکل نوع‌دار پیشنهادی است، نه endpoint backend حاضر. نام فیلد/مسیر موجود را با adapter به مدل UI نگاشت کنید. HTTPهای پیشنهادی:

```text
GET /api/forecast/points/{slug}?days=8&resolution=all
GET /api/forecast/routes/{slug}?days=8&resolution=1h
```

در payload محصول تنها مقصد/مسیر درخواست‌شده لازم است؛ فایل دمو برای سادگی همهٔ کاتالوگ را یک‌جا دارد. هشت روز را برای هر کلیک دوباره download نکنید. گزارش `data-validation.json` قرارداد نمونه را بررسی کرده؛ پاسخ backend واقعی هنوز نیاز به integration test خودش دارد.
