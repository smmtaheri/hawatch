# راهنمای استاندارد افزودن مقصد، نقطه و مسیر

این سند مرجع اصلی افزودن مقصدهای جدید به هواچ است. برای شروع کار نفر بعدی
همین سند را کامل بخواند؛ قرارداد جزئی‌تر فیلدها در
[`catalog-and-weather-validation.md`](catalog-and-weather-validation.md) و رفتار
forecast در [`api/forecast-contract.md`](api/forecast-contract.md) است.

## اصل معماری

دیتابیس منبع حقیقت runtime است. مقصد، WeatherPoint، Route و RoutePoint بعد از
import در دیتابیس ذخیره می‌شوند و برای اضافه‌کردن آن‌ها deploy یا migration لازم
نیست.

فایل JSON فقط یک ورودی versioned برای import است. می‌تواند در `/tmp` یا یک
مخزن خصوصی نگه‌داری شود و با `--stdin` از کامپیوتر اپراتور به کانتینر API
فرستاده شود؛ فایل JSON و GPX لازم نیست روی سرور کپی شوند.

کدهای عمومی این workflow در repository هستند:

- `scripts/validate_open_meteo_catalog.py`: اعتبارسنجی read-only مختصات، DEM و provider؛
- `scripts/analyze_route_tracks.py`: تحلیل read-only GPX روی کامپیوتر محلی؛
- `scripts/publish_catalog.py`: اجرای استاندارد کل workflow محلی/SSH؛
- `seed_catalog --stdin`: check-only یا import اتمیک در دیتابیس؛
- `ingest_open_meteo`: ذخیرهٔ forecast نقاط فعال؛
- `catalog_preflight`: بررسی read-only دادهٔ واقعی داخل دیتابیس.

## داده‌های لازم

### مقصد

برای هر مقصد یک رکورد با این اطلاعات لازم است:

- `slug` یکتا و پایدار، مثلاً `damavand`؛
- نام، نام کوتاه، منطقه و `category_key`؛ برای دماوند `volcano`؛
- مختصات canonical به‌صورت WGS84 ده‌دهی؛
- ارتفاع معتبر و منبع آن؛
- `climate`، تصویر و alt text؛
- مقصد جدید به‌صورت پیش‌فرض محبوب نیست. مجموعهٔ حداکثر چهار مقصد محبوب هوم را با
  command مدیریتی `set_popular_destinations` و به‌ترتیب دلخواه تنظیم کنید؛ لازم
  نیست برای تغییر آن کد یا migration بسازید.

`category_key` فقط متن دسته‌بندی نیست؛ کلید معنایی آیکون مقصد هم هست و از
دیتابیس به فرانت می‌رسد. برای مثال، اسکلیم باید `waterfall` داشته باشد و دماوند
`volcano`. بعد از اضافه‌شدن یک کلید به مجموعهٔ runtime، ثبت مقصدهای بعدی با یکی
از کلیدهای موجود فقط با import کاتالوگ یا Admin انجام می‌شود و deploy جداگانه
لازم ندارد. کلید ناشناخته نباید استفاده شود؛ UI برای جلوگیری از نمایش گمراه‌کننده
به‌جای کوه، نشان خنثی نشان می‌دهد.

همان نقطهٔ مقصد باید در `weather_points` با `kind: "destination"` هم تعریف شود
تا صفحهٔ مقصد و در صورت وجود مسیرها به یک WeatherPoint canonical وصل باشند.

### مقصد بدون مسیر

همهٔ مقصدها الزاماً مسیر پیادهٔ عمومی ندارند. برای دریاچه، جادهٔ دسترسی
آفرودی/خودرویی یا مقصدی که هنوز route پیادهٔ معتبر و مستند ندارد، مقصد را به‌صورت
destination-only ثبت کنید؛ ترک خودرو را به route پیاده تبدیل نکنید. در این حالت:

- یک canonical destination WeatherPoint با مختصات و ارتفاع معتبر کافی است؛
- `routes` باید یک آبجکت خالی (`{}`) باشد، نه اینکه حذف شود؛
- GPX لازم نیست و timing، distance و ascent مسیر نداریم؛
- forecast همان نقطه با ingest عادی ذخیره می‌شود و `catalog_preflight` فقط
  profile/provider را بررسی می‌کند؛
- UI مقصد بدون route را با وضعیت «هنوز مسیری برای این نقطه ثبت نشده» نشان می‌دهد.

اگر بعداً route پیادهٔ معتبر پیدا شد، همان catalog را با route، RoutePointهای
واقعی و evidence جداگانه version کنید و دوباره از gate کامل route عبور دهید.

نمونهٔ فعلی: دریاچهٔ تار با مختصات نمایندهٔ پهنهٔ آبی
`35.730520, 52.227850` و elevation کاتالوگ `2896 m` ثبت شده است. Open-Meteo
برای همین نقطه DEM برابر `2896 m` و نزدیک‌ترین grid در فاصلهٔ حدود `2.95 km`
برگرداند؛ این برای forecast قابل‌قبول است اما دقت پیش‌بینی واقعی را تضمین
نمی‌کند. منابع بررسی دسترسی و موقعیت: [OSM/Mapcarta](https://mapcarta.com/13159408)،
[Wikipedia](https://en.wikipedia.org/wiki/Lake_Tar)، و
[راهنمای دسترسی](https://zooomlite.ir/%D8%AF%D8%B1%DB%8C%D8%A7%DA%86%D9%87-%D8%AA%D8%A7%D8%B1-%D8%AF%D9%85%D8%A7%D9%88%D9%86%D8%AF/).

### WeatherPoint

برای هر نقطه:

- slug یکتا، نام و مختصات دقیق؛
- `elevation_m` از منبع قابل‌اعتماد، ترجیحاً DEM/PBF تأییدشده؛
- `elevation_source` یا `evidence_note` برای audit؛

### قواعد نام‌گذاری نقطه‌ها

- `WeatherPoint.name` باید نام یک عارضهٔ واقعی و قابل‌شناسایی باشد؛ نام‌های
  عمومی مثل «محل استراحت مسیر»، «شیب نهایی قله» یا «کمپ سوم» بدون ذکر
  مسیر/مکان قابل قبول نیستند.
- اگر یک نقطه بین چند مسیر مشترک است، نام canonical آن باید مستقل از یک
  مسیر خاص و همچنان قابل‌شناسایی باشد؛ برای متن route-specific از
  `RoutePoint.name` استفاده کنید، چون همین مقدار در تایم‌لاین عمومی نمایش داده
  می‌شود.
- نقطهٔ میانی باید یک عارضهٔ واقعی مثل گردنه، پناهگاه، چشمه، تقاطع مشخص،
  دریاچه یا چشم‌انداز مستند باشد. صرفاً «استراحتگاه» یا «توقفگاه میانی» نقطهٔ
  قابل انتشار نیست؛ اگر نام واقعی پیدا نشد، آن نقطه را به زنجیرهٔ عمومی اضافه
  نکنید.
- نام‌های ارتفاعی باید کوه/یال و ارتفاع را کامل داشته باشند؛ مثلاً
  «یال غربی دماوند · ارتفاع ۵۰۰۸ متر».
- برای عارضه‌های شماره‌دار، نام مکان را همراه شماره بیاورید؛ مثلاً «ایستگاه ۱
  توچال»، نه «ایستگاه ۱». برای پناهگاه‌ها و جان‌پناه‌ها نیز نوع عارضه را در
  نام بیاورید؛ مثلاً «جان‌پناه امیری»، نه «امیری».
- `name` باید برچسب نمایشی یکتا و روشن باشد و `aliases` شکل‌های کوتاه، فاصله‌دار
  یا رایج همان نام را پوشش دهد تا جست‌وجو حفظ شود. اگر هویت نقطه تغییر کرد، slug
  canonical را در همهٔ fixtureها، API، frontend و مستندات یک‌جا عوض کنید؛ URL قدیمی
  عمداً redirect یا نگاشت legacy ندارد.
- اگر ارتفاع هنوز قطعی نیست، مقدار `null` و وضعیت provisional استفاده شود؛
- GPX `<ele>` به‌تنهایی حقیقت ارتفاع نیست.

GPX برای گرفتن آب‌وهوا لازم نیست. مختصات و ارتفاع برای ساخت WeatherPoint
کافی است؛ GPX فقط برای بررسی هندسه، فاصله، صعود و نقاط میانی مسیر استفاده می‌شود.

### حداقل کیفیت route و انتخاب ترک

این بخش فقط وقتی مقصد route دارد gate اجباری قبل از ساخت catalog است. هر فایلی
که فقط به گهر، دماوند یا هر مقصد دیگری نزدیک باشد، خودبه‌خود evidence معتبر route
نیست. مقصد بدون route به GPX نیاز ندارد.

- مسیر باید با route محصول یکی باشد: مبدأ و مقصد یکسان، جهت پیمایش روشن، مسیر
  پیوسته و قابل‌دنبال‌کردن، و یک access point واقعی داشته باشد.
- برای محصول فعلی، ترک اصلی باید مسیر پیمایش پیاده/هiking باشد و در گزارش منبع
  نیز با همین کاربری معرفی شده باشد. ترک دوچرخه، موتور، خودرو، اسب، trail پراکنده
  یا مسیر نامرتبط را برای route پیاده رد کنید. چنین ترکی اگر فقط برای تطبیق یک
  مختصات استفاده شود باید صریحاً cross-check نام‌گذاری شود و هرگز مبنای
  `distance_km`، `ascent_m` یا ETA نباشد.
- مسیرهای صخره‌نوردی، سنگ‌نوردی، یخچالی یا فنی که با پیمایش عادی مخاطب یکی نیستند
  در فاز عمومی وارد نشوند؛ مگر اینکه محصول جداگانه و شواهد/برچسب‌گذاری جدا داشته
  باشند.
- مسیرهای بسیار پراکنده، بی‌نام، کم‌اعتبار یا بدون گزارش روشنِ مبدأ/مقصد را
  انتخاب نکنید. برای route اصلی ترجیحاً دو ترک مستقلِ پیاده از منابع معتبر را
  تطبیق دهید؛ اگر فقط یک ترک موجود است، فاصله و نقاط آن را با گزارش مسیر یا منبع
  مستقل کنترل کنید و confidence/uncertainty را محافظه‌کارانه ثبت کنید.
- عنوان، نوع فعالیت، توضیحات، distance، ascent و endpointهای منبع را قبل از
  استفاده بخوانید. `hiking-trails` در URL به‌تنهایی کافی نیست؛ محتوای صفحه باید
  واقعاً مسیر پیادهٔ موردنظر را تأیید کند.
- ترک باید برای route یک خط پیوسته از origin تا target بدهد. فایل round-trip یا
  نزولی فقط پس از تعیین جهت و نقطهٔ cut استفاده شود؛ timestamp خام GPX چندروزه
  زمان حرکت معتبر نیست و برای moving time/ETA استفاده نمی‌شود.
- هر route عمومی حداقل سه نقطهٔ واقعی دارد: مبدأ، حداقل یک landmark میانیِ
  نام‌دار و مستند، و مقصد. اگر route واقعاً کوتاه است، باز هم نباید نقطهٔ جعلی
  برای رسیدن به عدد سه ساخته شود؛ در آن حالت شواهد را تکمیل یا route را pending
  نگه دارید.

### قرارداد فولدر ترک

به‌محض شروع مقصد جدید، فولدر را در checkout محلی بسازید؛ اگر وجود ندارد، agent
باید خودش آن را بسازد و از کاربر بخواهد فایل‌ها را همان‌جا بگذارد:

```bash
cd /path/to/hawatch
mkdir -p tracks/<destination-slug>
```

نام فایل باید بدون بازکردن فایل نیز قابل‌فهم باشد؛ الگوی پیشنهادی:
`<destination>-<side-or-access>-<origin>-to-<target>-<year>.gpx`، مثلاً:
`tracks/gahar/gahar-dorud-cheshmeh-khieh-to-lake-2014.gpx`.
فایل‌های دانلودشدهٔ مبهم را قبل از تحلیل rename کنید و mapping را در
`tracks/<destination-slug>/manifest.json` ثبت کنید. اگر یک فایل reverse یا فقط
cross-check است، آن را در نام و manifest مشخص کنید.

رینیم بخشی از workflow اجباری است، نه کار اختیاری بعد از import. بعد از دانلود،
هر فایل را با نامی که مقصد، جبهه/مبدأ، مقصد مسیر و سال را نشان دهد به همان فولدر
منتقل کنید؛ سپس نام جدید را عیناً در manifest بنویسید. نمونهٔ صریح برای هزار:

```bash
cd /path/to/hawatch
mv tracks/hazar/qlh-hzr-khrmn-24-shhrywr-402-z-msyr-abshr-ryn.gpx \
  tracks/hazar/hazar-rayen-waterfall-parking-to-summit-2023-roundtrip.gpx
mv tracks/hazar/swd-bh-qlh-hzr-z-msyr-abshr-ryn.gpx \
  tracks/hazar/hazar-rayen-waterfall-parking-to-summit-2019.gpx
```

قبل از ادامه، نام‌ها و local-only بودن فولدر را کنترل کنید:

```bash
find tracks/<destination-slug> -maxdepth 1 -type f -printf '%f\n' | sort
git check-ignore -v tracks/<destination-slug>/*.gpx tracks/<destination-slug>/manifest.json
```

اگر `git check-ignore` برای همهٔ فایل‌ها خروجی نداد، قبل از ساخت catalog باید
`.gitignore` را اصلاح کنید؛ GPX و manifest نباید هیچ‌وقت وارد commit، image یا
سرور شوند.

کل `tracks/` از ابتدا تا انتها local-only است: نه commit، نه Docker image، نه
کپی روی سرور و نه سرو از API. manifest هم فقط برای تحلیل local است و runtime آن
را نمی‌خواند. وضعیت license را تا زمان تأیید `unverified` نگه دارید.

ترتیب کار با ترک:

1. فایل‌های دانلودشده را با الگوی نام‌گذاری بالا rename کنید و نام نهایی را در
   manifest ثبت کنید.
2. منبع و نوع فعالیت هر ترک را بررسی و ترک‌های دوچرخه/خودرو/فنی/پراکنده را حذف
   کنید؛ مسیر انتخابی را با گزارش مستقل تطبیق دهید.
3. نقاط named واقعی را از waypoint و geometry استخراج کنید؛ `Waypoint`،
   `Park`، `Rest area` و «شیب نهایی» بدون landmark واقعی وارد catalog نشوند.
4. manifest را بسازید، `timestamp_quality` و `license_status` را صریح ثبت کنید.
5. analyzer را فقط local و read-only اجرا کنید و خروجی آن را با منبع مسیر مقایسه
   کنید؛ analyzer خودش catalog را تغییر نمی‌دهد:

```bash
python3 scripts/analyze_route_tracks.py \
  --manifest tracks/<destination-slug>/manifest.json \
  --catalog /tmp/<destination-slug>_v1.json \
  > /tmp/<destination-slug>_tracks_report.json
```

6. فقط پس از قبولی این gate، `distance_km`، `ascent_m`، نقاط میانی و cumulative
   timing را وارد catalog کنید. GPX `<ele>` به‌تنهایی elevation truth نیست.

### Route (اختیاری)

اگر مقصد route دارد، برای هر مسیر:

- `slug`، عنوان، subtitle، برچسب جبهه و origin/destination label؛
- آرایهٔ `points` به‌ترتیب حرکت از مبدأ تا مقصد؛
- `sort_order` مثبت؛ عدد کمتر زودتر نمایش داده می‌شود؛
- `featured: true` فقط برای مسیرهای پیشنهادی UI است و ترتیب را تعیین نمی‌کند؛
- `distance_km` و `ascent_m` فقط وقتی ثبت شوند که evidence کافی دارند.

یک WeatherPoint می‌تواند بین چند Route مشترک باشد. برای آن یک slug بسازید و
همان slug را در چند مسیر استفاده کنید؛ برای هر مسیر RoutePoint جداگانه ساخته
می‌شود و timing آن مسیر را دارد.

اگر یک مسیر در کاتالوگ مقصد جدید از نقطهٔ canonical یک مقصد موجود شروع یا عبور
می‌کند، آن نقطه را دوباره در `weather_points` کپی نکنید. ابتدا کاتالوگ مالک آن
نقطه را import کنید، سپس slug آن را در آرایهٔ اختیاری
`shared_weather_points` بگذارید و همان slug را در `routes.*.points` استفاده
کنید. Loader نقطه را از دیتابیس resolve می‌کند و مالکیت، مختصات و ارتفاع آن را
تغییر نمی‌دهد. اگر slug در دیتابیس موجود نباشد یا live/active نباشد، import
fail می‌شود. نمونهٔ فعلی: route دریاچهٔ تار → زرین‌کوه از `tar_lake` مشترکِ
کاتالوگ `tar_v1.json` استفاده می‌کند؛ بنابراین کلیک روی نقطهٔ شروع به صفحهٔ
canonical `/destination/tar-lake` می‌رود. رکورد قدیمیِ ساحل تار صفحهٔ مستقلی ندارد
و در لینک‌های جدید استفاده نمی‌شود.

### زمان‌بندی arrival-aware

اگر می‌خواهیم زیر هر نقطهٔ مسیر زمان رسیدن و آب‌وهوای همان زمان نمایش داده شود،
route باید timing کامل داشته باشد:

```json
{
  "timing_status": "estimated",
  "one_way_minutes": 650,
  "timing": {
    "method": "gpx-geometry+dem+web-reports-v1",
    "version": "damavand-timing-v1",
    "confidence": "medium",
    "uncertainty_minutes": 90,
    "source_urls": ["https://example.org/source"],
    "cumulative_minutes": {
      "trailhead": 0,
      "shelter": 270,
      "summit": 650
    }
  }
}
```

قواعد اجباری:

- `timing_status` باید `estimated` یا `curated` باشد؛
- `one_way_minutes` زمان صعود یک‌طرفه در سرعت متوسط است؛
- cumulative برای تمام نقاط مسیر لازم است؛
- مقدار اول صفر و همهٔ مقادیر بعدی strictly increasing باشند؛
- مقدار نهایی cumulative با `one_way_minutes` برابر باشد؛
- method، version، confidence، uncertainty و حداقل یک source URL ثبت شوند؛
- timestamp ثبت‌شدهٔ یک GPX چندروزه، زمان حرکت مسیر نیست؛ استراحت/شب‌مانی نباید
  وارد ETA شود؛
- اگر timing قابل‌دفاع نیست، route باید `pending` بماند. در این حالت forecast
  عمومی نقطه موجود است، اما arrival forecast عمداً ساخته نمی‌شود.

سرعت‌های آرام و سریع در runtime از زمان متوسط مشتق می‌شوند (`1.25` و `0.80`).
لازم نیست برای هر سرعت سه مجموعه timing جداگانه ذخیره شود.

## تنظیم مقصدهای محبوب هوم

لیست بدون query در `GET /api/v1/destinations/` همان لیست مقصدهای محبوب هوم است و
حداکثر چهار رکورد برمی‌گرداند. جست‌وجوی endpoint جداگانه همچنان مقصدهای فعال
غیرمحبوب را هم پیدا می‌کند. برای تغییر لیست روی local یا سرور، slugها را به
ترتیب نمایش به command بدهید:

```bash
cd apps/api
uv run python manage.py set_popular_destinations \
  tochal damavand daryasar alamkuh
```

یا با comma-separated:

```bash
docker compose --env-file .env -f infra/compose/compose.yaml exec -T api \
  python manage.py set_popular_destinations \
  --slugs tochal,damavand,daryasar,alamkuh
```

این command به‌صورت اتمیک همهٔ مقصدهای دیگر را از لیست محبوب خارج می‌کند، ترتیب
را از ۱ تا ۴ می‌نویسد و اگر slug ناشناخته یا بیشتر از چهار مورد داده شود هیچ
تغییری نگه نمی‌دارد. برای خالی‌کردن لیست از `--clear` استفاده کنید.

## GPX و manifest

اگر GPX دارید، آن را فقط در checkout محلی زیر `tracks/<destination>/` بگذارید.
کل `tracks/` در Git ignore است و نباید commit، image یا سرور شود. `manifest.json`
فقط mapping فایل GPX به route، کیفیت timestamp و وضعیت license است؛ API در زمان
seed یا ingest آن را نمی‌خواند.

تحلیل محلی:

```bash
cd /path/to/hawatch

python3 scripts/analyze_route_tracks.py \
  --manifest tracks/damavand/manifest.json \
  --catalog /tmp/damavand_v1.json \
  > /tmp/damavand_tracks_report.json
```

خروجی distance، صعود نرم‌شده و نزدیک‌ترین نقطهٔ track را گزارش می‌کند؛ خودش
catalog را تغییر نمی‌دهد. timing نهایی تصمیم editorial است و باید با گزارش مسیر
و منابع وب/میدانی ثبت شود، نه اینکه یک timestamp خام بدون بررسی وارد ETA شود.

## فلو پیشنهادی کامل

### ۱. ساخت و ویرایش catalog روی local

یک فایل مثل `/tmp/damavand_v1.json` بسازید. این فایل باید shape نمونهٔ
`apps/api/fixtures/catalog/tochal_v1.json` را داشته باشد و route timing کامل
داشته باشد اگر قرار است arrival weather نمایش داده شود.

قبل از ساخت JSON، اگر مقصد route دارد فولدر `tracks/<destination-slug>/` را بسازید
و معیارهای «حداقل کیفیت route و انتخاب ترک» را در همین سند اجرا کنید. برای هر
route حداقل origin، یک landmark میانی واقعی و target را مشخص کنید. نبود GPX مانع
forecast مقصد یا destination-only نیست، اما بدون evidence کافی نباید
distance/ascent/ETA قطعی یا route عمومیِ ناقص منتشر شود.

برای شروع می‌توان از
[`templates/catalog-template.json`](templates/catalog-template.json) یک کپی
گرفت و همهٔ مقادیر نمونه را با دادهٔ مقصد واقعی جایگزین کرد. فایل template عمداً
یک route `pending` دارد تا مسیر ناقص به‌اشتباه به‌عنوان arrival-ready منتشر نشود.

برای مقصد جدید لازم نیست فایل را در repository یا سرور قرار دهید. اگر بخواهید
نسخهٔ داده قابل بازبینی داشته باشید، آن را در یک محل خصوصی/محلی نگه دارید؛
runtime بعد از import دیتابیس است.

### ۲. اعتبارسنجی محلی provider و ارتفاع

این فرمان هیچ database write ندارد و از Open-Meteo برای elevation و forecast
ساعتی استفاده می‌کند:

```bash
cd /path/to/hawatch
python3 scripts/validate_open_meteo_catalog.py \
  --catalog /tmp/damavand_v1.json
```

این مرحله gate اجباری بعد از آماده‌کردن WeatherPointها و قبل از هر `seed` است.
اگر حتی یک point خطا بگیرد، نباید catalog یا آن point وارد دیتابیس شود؛ همان
خروجی شامل slug نقطه و علت خطا باید به درخواست‌کننده/چت گزارش شود و مختصات یا
ارتفاع نباید بی‌دلیل حدس زده و silently اصلاح شود. خطاهای blocking شامل این‌هاست:

- مختصات نامعتبر، پاسخ elevation نامعتبر یا نبودن elevation منبع‌دار؛
- فاصلهٔ grid پاسخ Open-Meteo بیشتر از `۵ km`؛
- نبودن `time`، دما، بارش یا `weather_code` ساعتی، یا ناهماهنگی طول آرایه‌ها؛
- اختلاف بیشتر از `۱۰۰ m` بین ارتفاع catalog و DEM، مگر اینکه مقدار catalog
  اصلاح و دوباره اعتبارسنجی شود.

validator برای هر خطای بالا exit code غیرصفر می‌دهد. `publish_catalog.py --apply`
این validator را قبل از اتصال به سرور اجرا می‌کند و در صورت خطا به مرحلهٔ
`seed_catalog` نمی‌رسد. گزینه‌های `--skip-provider-validation` و
`--allow-unresolved-elevation` فقط برای بررسی draft هستند و با `--apply` مجاز
نیستند. `seed_catalog --check-only` فقط shape JSON را می‌سنجد و جای این gate
را نمی‌گیرد.

این بررسی باید نشان دهد:

- مختصات در محدودهٔ WGS84 و تکراری نیستند؛
- همهٔ routeها فقط به pointهای موجود اشاره می‌کنند؛
- برای هر point دادهٔ ساعتی provider وجود دارد؛
- فاصلهٔ مرکز grid provider حداکثر ۵ کیلومتر است؛
- اختلاف elevation catalog و DEM حداکثر `۱۰۰ متر` است؛ بیشتر از آن failure است.

این تست ثابت نمی‌کند پیش‌بینی weather از نظر MAE در دنیای واقعی «دقیق» است؛
فقط می‌سنجد نقطه به grid درست وصل است و forecast قابل دریافت است. سنجش دقت
تجربی نیازمند observation واقعی/ایستگاه مرجع و workflow جداگانه است.

### ۳. یک فرمان برای check و publish

حالت بدون `--apply` فقط بررسی می‌کند:

```bash
cd /path/to/hawatch
python3 scripts/publish_catalog.py \
  --catalog /tmp/damavand_v1.json \
  --host root@SERVER_IP
```

این wrapper به‌ترتیب این کارها را انجام می‌دهد:

1. local Open-Meteo/DEM validation؛
2. ارسال JSON از stdin به سرور و `seed_catalog --check-only`؛
3. توقف بدون هیچ database write.

پس از موفقیت check، publish واقعی:

```bash
python3 scripts/publish_catalog.py \
  --catalog /tmp/damavand_v1.json \
  --host root@SERVER_IP \
  --apply
```

در حالت apply، wrapper به‌ترتیب زیر عمل می‌کند:

1. دوباره از pass شدن gate محلی Open-Meteo/DEM مطمئن می‌شود؛
2. catalog را با `seed_catalog --stdin --strict` به‌صورت اتمیک import می‌کند؛
3. فقط slugهای همین catalog را با `ingest_open_meteo` می‌گیرد؛
4. `catalog_preflight --destination ... --require-forecast --strict` را اجرا می‌کند؛
5. اگر همه‌چیز pass شود، مقصد آمادهٔ refresh صفحه است.

اگر عمداً route بدون timing اضافه می‌کنید، باید آگاهانه استفاده کنید:

```bash
python3 scripts/publish_catalog.py \
  --catalog /tmp/draft.json \
  --host root@SERVER_IP \
  --apply \
  --allow-pending-timing
```

این گزینه مشکل را پنهان نمی‌کند؛ route در دیتابیس `pending` می‌ماند و arrival
weather آن در UI نمایش داده نمی‌شود. برای launch عمومی بهتر است بدون این گزینه
کار کنید تا missing timing جلوی publish گرفته شود.

### ۴. معادل دستی روی سرور

این مسیر فقط وقتی مجاز است که فرمان local validator بلافاصله قبل از آن با
`pass=True` تمام شده باشد. `seed_catalog --check-only` به‌تنهایی اعتبار weather
یا ارتفاع را بررسی نمی‌کند. اگر validator خطا داد، import را اجرا نکنید و همان
خطای دارای slug نقطه را گزارش کنید.

اگر wrapper در دسترس نبود، از root checkout سرور:

```bash
ssh root@SERVER_IP \
  'cd /root/hawatch && docker compose --env-file .env -f infra/compose/compose.yaml exec -T api python manage.py seed_catalog --stdin --check-only' \
  < /tmp/damavand_v1.json

ssh root@SERVER_IP \
  'cd /root/hawatch && docker compose --env-file .env -f infra/compose/compose.yaml exec -T api python manage.py seed_catalog --stdin --strict' \
  < /tmp/damavand_v1.json

ssh root@SERVER_IP \
  'cd /root/hawatch && docker compose --env-file .env -f infra/compose/compose.yaml exec -T api python manage.py ingest_open_meteo'

ssh root@SERVER_IP \
  'cd /root/hawatch && docker compose --env-file .env -f infra/compose/compose.yaml exec -T api python manage.py catalog_preflight --destination damavand --require-forecast --strict'
```

در فرمان‌های بالا `/tmp/damavand_v1.json` روی local خوانده می‌شود و از stdin
عبور می‌کند؛ لازم نیست `/tmp` روی سرور وجود داشته باشد.

برای بررسی مقصد بدون تغییر:

```bash
ssh root@SERVER_IP \
  'cd /root/hawatch && docker compose --env-file .env -f infra/compose/compose.yaml exec -T api python manage.py catalog_preflight --destination damavand --require-forecast'
```

در `catalog_preflight`، حالت `--strict` warningهای timing را هم failure می‌کند.
برای مقصدی که هنوز timing ندارد، `pass=False` با warning طبیعی است؛ این نشانهٔ
خرابی ingest نیست.

### وضعیت فعلی دماوند

برای دماوند، چهار route اصلی با timing تخمینی اولیه وارد دیتابیس شده‌اند:

| route | زمان متوسط یک‌طرفه | عدم‌قطعیت | وضعیت |
| --- | ---: | ---: | --- |
| جنوبی | ۶۱۵ دقیقه | ±۹۰ دقیقه | estimated |
| غربی | ۶۹۰ دقیقه | ±۹۰ دقیقه | estimated |
| شمال‌شرقی | ۶۵۰ دقیقه | ±۹۰ دقیقه | estimated |
| شمالی | ۷۵۰ دقیقه | ±۹۰ دقیقه | estimated |

این اعداد برای اتصال forecast به زمان رسیدن استفاده می‌شوند و field-curated
نیستند؛ بعداً با چند track مستقل و گزارش میدانی می‌توان آن‌ها را به‌روزرسانی کرد.
GPX شمالی timestamp معتبر برای محاسبهٔ moving time نداشت و timestamp خام آن در
این timing استفاده نشده است.

### ۵. مسیر Admin بدون JSON

برای ورود دستی:

1. Admin → WeatherPoint: slug، نام، مختصات، elevation، `is_active=true` و
   `ingest_enabled=true`؛ `fixture_managed` را دستی true نکنید.
2. در صورت نیاز Destination profile را به WeatherPoint canonical وصل کنید.
3. Admin → Route: مقصد فعال، عنوان، `sort_order` و active.
4. RoutePointها را به‌ترتیب بسازید و برای همه `cumulative_minutes` وارد کنید.
5. بعد از save، publish service ترتیب، origin/target، segment، axis و timing را
   normalize می‌کند؛ timing ناقص عمداً pending می‌شود.
6. ingest هدفمند را اجرا و preflight را چک کنید.

برای اضافه‌کردن سریع مقصدهای متعدد، JSON + wrapper پیشنهاد می‌شود؛ Admin برای
اصلاح یک رکورد یا override اپراتوری مناسب‌تر است.

### Definition of Done برای مقصد جدید

مقصد فقط وقتی «آمادهٔ نمایش» محسوب می‌شود که همهٔ این موارد برقرار باشند:

1. category/icon از کلیدهای موجود انتخاب شده و مقصد ناخواسته وارد popular home
   نشده باشد.
2. canonical destination WeatherPoint و همهٔ route pointها مختصات WGS84، ارتفاع
   منبع‌دار و نام قابل‌شناسایی داشته باشند؛ ارتفاع provisional باید همین‌طور
   برچسب بخورد و GPX `<ele>` جای آن را نگیرد.
3. اگر `routes` خالی نیست، هر route حداقل origin → landmark واقعی → target،
   ترتیب `sort_order` و timing کامل یا وضعیت آگاهانهٔ `pending` داشته باشد.
4. اگر route وجود دارد، همهٔ ترک‌های مورد استفاده، hiking مناسب و پیوسته باشند؛ هیچ ترک دوچرخه، فنی،
   پراکنده یا نامرتبط در محاسبهٔ route وارد نشده باشد.
5. validator محلی، check-only remote، import strict، ingest و preflight strict
   pass شده باشند؛ validator باید برای هر point پاسخ elevation، grid نزدیک و
   دادهٔ ساعتی کامل گزارش کند و برای هر point forecast ذخیره‌شده وجود داشته باشد.
6. صفحهٔ مقصد و تمام routeها با API واقعی refresh و از نظر نام، مختصات، timing و
   weather point بررسی شده باشند.
7. `tracks/` و manifest local-only، ignored و خارج از commit باقی مانده باشند.

## حل خطاهای رایج

### `timed_routes=0` یا `زمان‌بندی در دسترس نیست`

نقاط forecast دارند اما route timing ندارد یا cumulative یکی از نقاط خالی است.
دوباره ingest کردن این مشکل را حل نمی‌کند. timing را به JSON اضافه و دوباره با
`seed_catalog --stdin --strict` import کنید.

### `provider_checked=17` ولی route هنوز خالی است

این حالت طبیعی است: provider برای WeatherPointها موفق بوده، اما API برای اتصال
forecast به نقطهٔ مسیر به arrival time نیاز دارد. timing و `cumulative_minutes`
را بررسی کنید.

### `Catalog input is valid; No database changes made`

این خروجی `--check-only` است و موفقیت آن به معنی import نیست. مرحلهٔ apply را
بعد از بررسی اجرا کنید.

### slug conflict

import معمولی non-destructive است. ردیف operator-managed overwrite نمی‌شود؛ در
حالت strict کل import rollback می‌شود. slug موجود را reuse کنید یا conflict را
در Admin بررسی کنید؛ `--force-adopt` فقط با تصمیم صریح اپراتور استفاده شود.

### دادهٔ هوا قدیمی است

ingest scheduler طبق timezone تهران در ساعت‌های ۰۰:۰۰، ۰۶:۰۰، ۱۲:۰۰ و ۱۸:۰۰
اجرا می‌شود. برای refresh فوری:

```bash
docker compose --env-file .env -f infra/compose/compose.yaml run --rm ingest
```

سپس preflight را اجرا کنید. frontend مستقیماً به Open-Meteo وصل نمی‌شود؛ فقط
forecast ذخیره‌شدهٔ دیتابیس را می‌خواند.

## چک‌لیست قبل از اعلام آماده‌بودن

- [ ] مقصد و canonical destination WeatherPoint مختصات و elevation منبع‌دار دارند.
- [ ] اگر مقصد route دارد، هر route `sort_order` درست و points مرتب از مبدأ تا مقصد دارد.
- [ ] اگر route دارد، distance/ascent عمومی قابل‌دفاع و timingهای arrival دارای provenance هستند.
- [ ] `validate_open_meteo_catalog.py` بدون error pass شده است.
- [ ] هیچ pointی اختلاف catalog/DEM بیشتر از `۱۰۰ m`، grid دورتر از `۵ km` یا
      hourly ناقص ندارد؛ در غیر این صورت import انجام نشده و خطا گزارش شده است.
- [ ] remote `seed_catalog --stdin --check-only` pass شده است.
- [ ] import strict انجام شده است.
- [ ] ingest موفق بوده است.
- [ ] preflight با `--require-forecast --strict` pass شده است.
- [ ] صفحهٔ مقصد و هر route با date/period/start_time واقعی refresh و بررسی شده‌اند.
- [ ] GPX و manifest داخل `tracks/` باقی مانده و commit نشده‌اند.
