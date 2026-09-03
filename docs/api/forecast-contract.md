# قرارداد forecast هواچ

timezone محصول: `Asia/Tehran` (زمان رسمی ایران، مستقل از timezone مرورگر یا سرور).

بازهٔ قابل مشاهدهٔ این نسخه:

- رابط کاربری ۷ روز را نشان می‌دهد: دیروز، امروز، و پنج روز بعد.
- پنجرهٔ ingest provider هفت روز تقویمیِ امروز تا شش روز بعد است؛ روز گذشته فقط
  اگر از ingest قبلی در دیتابیس موجود باشد نگه داشته می‌شود و دوباره از provider
  درخواست نمی‌شود.
- hourly: هر دو ساعت؛ هر بازه دقیقاً سه کارت دارد.
- `period.headline` فقط فیلد سازگاری/داخلی است و در UI Destination/Point نمایش داده نمی‌شود.
- چهار بازهٔ غیرهم‌پوشان از نیمه‌شب تا پایان همان روز (قرارداد قدیمیِ سه‌بازه‌ای با این برنامه **جایگزین شده**):

| `period` | برچسب | پنجرهٔ منطقی | کارت‌ها |
| --- | --- | --- | --- |
| `midnight` | نیمه‌شب | ۰۰:۰۰–۰۶:۰۰ | ۰۰، ۰۲، ۰۴ |
| `morning` | صبح | ۰۶:۰۰–۱۲:۰۰ | ۰۶، ۰۸، ۱۰ |
| `noon` | ظهر | ۱۲:۰۰–۱۸:۰۰ | ۱۲، ۱۴، ۱۶ |
| `night` | شب | ۱۸:۰۰–۲۴:۰۰ | ۱۸، ۲۰، ۲۲ |

برای سازگاری با لینک‌های قبلی، شناسهٔ `afternoon` در ورودی API به `noon` تبدیل می‌شود؛ پاسخ canonical همیشه `noon` است.

## معنای تاریخ برای همهٔ بازه‌ها

`date` تاریخ تقویمیِ همان بازه است. هر چهار بازه در همان روز قرار دارند؛
`period=night` شامل ۱۸:۰۰، ۲۰:۰۰ و ۲۲:۰۰ همان روز است و از نیمه‌شب عبور نمی‌کند.
فیلتر همچنان با پنجرهٔ timezone-aware انجام می‌شود.

## انتخاب پیش‌فرض (بدون query صریح)

| ساعت محلی تهران | `selected_period` | `selected_date` |
| --- | --- | --- |
| ۰۰:۰۰–۰۵:۵۹ | `midnight` | امروز |
| ۰۶:۰۰–۱۱:۵۹ | `morning` | امروز |
| ۱۲:۰۰–۱۷:۵۹ | `noon` | امروز |
| ۱۸:۰۰–۲۳:۵۹ | `night` | امروز |

اگر کاربر `date` یا `period` را صریح بفرستد، API همان را برمی‌گرداند و frontend بعد از load آن را overwrite نمی‌کند. در بار اول بدون query، frontend نباید `period=morning` بفرستد؛ backend مقدار را در `meta` برمی‌گرداند.

## past / current / future

flagها از **timestamp واقعی** هر reading (`forecast_at`) نسبت به `current_local_time` محاسبه می‌شوند. ساعت‌های گذشته dim می‌شوند؛ ساعت جاری مشخص است؛ دادهٔ cross-midnight در `night` همین قواعد را دارد.

## envelope

```text
forecast (Forecast Place — destination یا point)
├── subject { kind, slug, canonical_href, name, elevation, coords, hero_image, ... }
├── hero { status, alert }
├── forecast { days[], period, current?, hourly[], meta }
├── metrics[]
├── decision
├── related_routes[]
├── (سازگاری) destination | point | weather | days | hourly | meta
```

`metrics[]` برای هر شاخص شامل `icon`، `label`، `value`، `note` و `color` است. مقدار `icon` یک
نام معنایی پایدار است و glyph یا متن نمایشی نیست؛ کلاینت آن را از sprite رسمی
`/icons/specialist/hawatch-specialist-icons.svg` رندر می‌کند. نگاشت فعلی:

در پاسخ route forecast، `decision.gear[]` نیز آرایه‌ای از کلیدهای معنایی تجهیزات
است. این کلیدها برای رندر آیکون و نام وسیله‌اند (مثلاً `backpack`،
`waterproof-shell` و `microspikes`) و نباید با متن فارسی recommendation جایگزین
شوند. فهرست کلیدها و assetهای نسخهٔ فعلی در
`apps/web/public/icons/gear/manifest.fa.json` ثبت شده است. فیلد قدیمی
`decision.recommendations[]` برای سازگاری کلاینت‌ها باقی می‌ماند، اما UI share
کارت فقط `gear[]` را نمایش می‌دهد.

| `icon` | شاخص |
| --- | --- |
| `wind-average` | باد میانگین |
| `wind-gust` | تندباد |
| `visibility` | دید افقی |
| `freezing-level` | تراز صفر درجه |
| `cloud-base` | پایهٔ ابر |
| `uv-index` | تابش فرابنفش |
| `precipitation` | بارش |
| `sunrise-sunset` | طلوع / غروب |
| `temperature` | دما (حسی، مطلق، کمینه و بیشینه) |

آیکون فقط کمک بصری است؛ عنوان و مقدار متریک همیشه به‌صورت متنی نیز ارائه می‌شوند.

متریک‌های دما و بارش از رکوردهای همان بازهٔ انتخاب‌شده ساخته می‌شوند: دمای حسی و مطلق
میانگین بازه‌اند، کمینه و بیشینه از `temperature_c` همان بازه محاسبه می‌شوند، و
`باران`/`برف` مجموع مقدارهای ساعتی همان بازه هستند. `precipitation_mm` مقدار کل بارش
(باران و برف) در هر ساعت است؛ `rain_mm` مؤلفهٔ باران به میلی‌متر و `snowfall_cm` مؤلفهٔ برف به
سانتی‌متر است. کارت عمومی ساعتی و خلاصهٔ آب‌وهوای نقطهٔ مسیر `apparent_temperature`
را نشان می‌دهند؛ مقدار مطلق برای جزئیات تخصصی نیز در payload باقی می‌ماند.

Route envelope جداگانه است و `route` / `points[]` / `timing_pending` دارد.

هر reading شامل `temperature_c` (دمای مطلق)، `apparent_temperature_c` (دمای حسی)،
`temperature_label` و `apparent_temperature_label`، condition/code، wind speed/gust/direction،
`precipitation_probability`، `precipitation_mm` (مقدار کل بارش همان ساعت)، `rain_mm` (مؤلفهٔ باران)،
`snowfall_cm` (مؤلفهٔ برف)، visibility، cloud cover، UV در صورت وجود، و
`freezing_level_m` در صورت ارائهٔ provider، و flagهای:

- `is_yesterday`
- `is_today`
- `is_past`
- `is_current`
- `is_future`

تمام timestampهای public (`forecast_at`، `valid_from`، `valid_to`، `generated_at` و `current_local_time`) با offset `Asia/Tehran` برمی‌گردند؛ timestamp UTC در قرارداد frontend نمایش داده نمی‌شود.

برای Destination و Point، `current`/`weather` باید **فقط** از reading داخل پنجرهٔ period انتخاب‌شده بیاید؛ fallback کل روز تقویمی ممنوع است. «الان» فقط وقتی مجاز است که reading واقعاً `is_current` باشد.

## metadata

- `data_mode`
- `provider` / `source`
- `generated_at`
- `current_local_time`
- `timezone`
- `seed_version`
- `freshness` (`ready` | `stale` | `partial`)
- `selected_date` / `selected_period`
- `valid_from` / `valid_to`

دادهٔ دمو به‌عنوان مشاهدهٔ واقعی معرفی نمی‌شود؛ `data_mode=demo` است.

## route planner

- `start_time` در هر period به بازهٔ همان period محدود می‌شود.
- granularity پیش‌فرض: `PLANNER_TIME_STEP_MINUTES = 60` در `hawatch.common.time` (منبع واحد؛ frontend از payload می‌خواند).
- پاسخ `period` در route (و place) شامل `planner_step_minutes`، `planner_start_minutes`، `planner_end_minutes`، `planner_last_start_minutes`، `planner_default_start_minutes`، `planner_slots[]`، `planner_ticks[]` است.
- نیمه‌شب قابل انتخاب: ۰۰–۰۵؛ صبح: ۰۶–۱۱؛ ظهر: ۱۲–۱۷؛ شب: ۱۸–۲۳.
- Gauge بصری RTL است: زودترین زمان راست، دیرترین چپ.
- هر period فقط همان بازهٔ شش‌ساعتهٔ روز را پوشش می‌دهد؛ `00:00` متعلق به `midnight` و `18:00` متعلق به `night` است.

### ورودی و نرمال‌سازی `start_time`

| ورودی | رفتار |
| --- | --- |
| `06:00` (ASCII) | پذیرفته؛ خروجی wire: `06:00` |
| `۰۶:۰۰` / `٠٦:٠٠` (Persian/Arabic) | normalize به ASCII؛ همان دقیقه |
| `360` (legacy bare minutes) | پذیرفته؛ تفسیر دقیقه از نیمه‌شب (۰–۱۴۳۹) و clamp داخل period |
| `10:15` (off-step) | floor به step پیکربندی‌شده سپس clamp داخل period |
| `12:xx`، `12:00:00`، `25:00`، `12:60` | **رد** → HTTP `400` با پیام validation |

- خروجی canonical در query و share URL همیشه **ASCII `HH:MM`** است (`format_start_time_wire` / `toClock`).
- برچسب فارسی (`۰۶:۰۰`) فقط در فیلد display `start_time` پاسخ API برای UI است؛ authority عددی `start_minutes` است.
- frontend بعد از پاسخ route باید `start_minutes` API را مرجع قرار دهد، نه URL خام.

### سیاست پیش‌فرض (بدون `start_time` یا بعد از تغییر `date`/`period`)

- اگر `date` + `period` همان بازهٔ جاری تهران باشد → ساعت فعلی floor‌شده به `PLANNER_TIME_STEP_MINUTES`؛
- در غیر این صورت → `default_start` همان period (`midnight=02:00`، `morning=08:00`، `noon=14:00`، `night=20:00`)؛
- `default_start_minutes` مسیر (مثلاً 06:00 برای دربند) **جایگزین** period default نمی‌شود.

- وقتی `timing_pending=true` است، arrival/ETA ساخته نمی‌شود.
- وقتی timing در دسترس نیست، خلاصهٔ آب‌وهوای نقطه به‌عنوان پیش‌بینی رسیدن ارائه نمی‌شود؛ حالت فشردهٔ فارسی «زمان‌بندی در دسترس نیست» نشان داده می‌شود (`weather_available=false`).
- `timing_pending` یک flag قراردادی برای client است و نباید عیناً در متن کاربر نمایش داده شود؛ UI باید پیام فارسی قابل فهم ارائه کند.

### زمان‌بندی تخمینی مسیر (Tochal v3)

Catalog `hawatch-tochal-catalog-v6` / `tochal-timing-v3`. هر پنج مسیر توچال estimated:

- Darband / Velenjak / Ahar: method `web-naismith-total+gpx-profile-v2` — totals از web/Naismith، پروفایل cumulative از GPX moving proportions (نه موتور per-segment).
- Kalkchal: `gpx-geometry+web-naismith-v3` — هندسه کامل GPX؛ timestampهای مصنوعی (فاصلهٔ دقیق ۴۰ ثانیه) برای moving-time قابل استفاده نیستند؛ medium 390 دقیقه / uncertainty ≥45.
- Shahrestanak: `composite-gpx+dem+web-reports-v1` — برآورد ترکیبی روستا→ناصری + ناصری→قله؛ medium 370 / uncertainty ≥50؛ estimated نه curated. زنجیرهٔ اجباری از گردنهٔ شهرستانک (`shahrestanak_pass`) می‌گذرد، نه بازارک.

- `slow`/`medium`/`fast` ضریب زمان نسبی‌اند نه km/h: آرام `1.25`، متوسط `1.00`، سریع `0.80` (`SPEED_TIME_FACTORS`).
- `paced_minutes = round_to_nearest_5(cumulative_medium_minutes * speed_time_factor)`.
- `arrival_at` از `start_minutes` تهران + paced duration ساخته می‌شود و می‌تواند از مرز period و نیمه‌شب عبور کند.
- برای هر RoutePoint فقط forecast همان `WeatherPoint` انتخاب می‌شود (نزدیک‌ترین ساعتی در ±۹۰ دقیقه به `arrival_at`). در تساوی فاصله، `forecast_at` زودتر و سپس primary key پایین‌تر برنده است؛ fallback به قله/مقصد ممنوع است؛ خارج از tolerance → `weather_available=false`.
- `state` کارت نقطه فقط از `severity` همان forecast انتخاب‌شده می‌آید؛ آستانهٔ زمان سپری‌شده یا بازنویسی hourly مقصد از روی critical نقطه ممنوع است.
- period انتخاب‌شده فقط پنجرهٔ مجاز حرکت را محدود می‌کند؛ بعد از محاسبهٔ رسیدن، خلاصهٔ period مبدأ به همهٔ نقاط تحمیل نمی‌شود.
- فیلد `one_way_minutes` مدت صعود یک‌طرفهٔ متوسط است؛ نباید در `round_trip_minutes` ذخیره شود.
- مسیر فقط وقتی usable است که status برابر `estimated`/`curated` باشد، `one_way_minutes` مثبت باشد، حداقل دو نقطه داشته باشد، همهٔ نقاط estimated/curated با cumulative کامل، cumulative اول صفر، strictly increasing، و cumulative نهایی برابر `one_way_minutes` باشد؛ در غیر این صورت `timing_pending=true`. `base_minutes` legacy برای arrival کافی نیست.
- GPX فقط evidence داخلی است (`tracks/`، analyzer آفلاین)؛ در API/seed/ingest parse نمی‌شود و از Docker imageهای production حذف می‌شود.
- پاسخ نقطه شامل `arrival_at`، `arrival_minutes`، برچسب تقریبی زمان (`حدود HH:MM` در UI)، `timing_status`/`confidence`/`uncertainty`، `forecast_at` و شرط/دما/باد/severity همان نقطه است.
- `points[].note` فقط از `RoutePoint.public_note` صریح و کوتاه می‌آید. evidence/GPX/DEM و یادداشت‌های catalog در `internal_note` نگه‌داری می‌شوند و در هیچ پاسخ public برنمی‌گردند.

## نقطهٔ canonical (Forecast Place — نقش point)

- `GET /api/v1/points/{weather_point_slug}/forecast/?date=&period=`
- URL frontend: `/points/{weather_point_slug}` — مثال `/points/tochal-sarband-square`
- همان قرارداد place مشترک با destination؛ frontend فقط `forecast.*` را مصرف می‌کند (alias ریشه سازگاری است)
- WeatherPoint مقصدی `canonical_href` عمومی در namespaceٔ `/points/` ندارد؛ frontend
  باید از ابتدا `/destination/{slug}` را لینک کند.
- **بدون** planner controls روی صفحه
- mobile هم همان `mobile-route-picker` مقصد را برای مسیرهای مرتبط نشان می‌دهد

## جست‌وجوی پیشنهاد (Home)

- `GET /api/v1/search/suggestions/?q=...`
- حداقل ۲ کاراکتر normalize‌شده؛ تطبیق substring برای پیدا کردن واژه‌های داخل نام/alias؛ حداکثر ۸ نتیجه
- عنوان و slug مسیرها در این endpoint ایندکس نمی‌شوند و نباید نتیجهٔ جست‌وجو باشند.
- مقصد یک‌بار برمی‌گردد (نه duplicate با WeatherPoint قله)
- انواع: `destination` → `/destination/{slug}`؛ `point` → `/points/{weather_point_slug}`
- label نمونه: `قلهٔ توچال — مقصد` · `پس‌قلعه — نقطهٔ مسیر · توچال`

## slider commit

در Route، مقدار gauge بلافاصله با state محلی به‌روز می‌شود؛ commit به URL/API فقط در پایان تعامل (pointer/touch release، blur، Enter/Space) یا debounce کوتاه (~۳۰۰ms) انجام می‌شود.

## contract بصری مشترک

- `meta.current_local_time` تنها مرجع تعیین بازهٔ جاری/گذشته در timezone رسمی ایران است.
- UI باید periodهای کاملاً گذشته را کم‌رنگ کند و period جاری/آینده را عادی نگه دارد.
- فیلد `updated_label` برای نمایش عمومی deprecated است؛ timestamp خام ISO نباید در UI رندر شود.
- Route نباید period weather را به‌عنوان پیش‌بینی رسیدن نشان دهد وقتی timing pending است.
- `/destination/*` و `/points/*` یک قالب Forecast Place دارند؛ baseline بصری screenshotهای Destination است.
