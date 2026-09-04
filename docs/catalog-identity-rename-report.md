# گزارش یکدست‌سازی هویت کاتالوگ

این گزارش نتیجهٔ مرحلهٔ پاک‌سازی کاتالوگ پیش از کار SEO است. هدف آن است که
هر نقطه، مسیر و نقطهٔ مستقل یک هویت پایدار، قابل جست‌وجو و قابل تشخیص داشته
باشد. این تغییر فقط روی نام و شناسهٔ داده‌هاست؛ مختصات، ارتفاع، forecast و
داده‌های Open-Meteo منبع جدیدی پیدا نکرده‌اند.

## قواعد نهایی

- slug نقطه و مسیر با حروف کوچک انگلیسی و خط تیره است؛ برای مثال
  `tochal-velenjak`.
- نقطهٔ مستقل باید در slug زمینهٔ نقطه یا نوع مکان را داشته باشد؛ برای مثال
  `damavand-shelter-4000`، نه `shelter_4000`.
- `page_name` نام کامل و مناسب عنوان صفحه است و باید مستقل از route خوانده
  شود. `short_label` فقط برای کارت‌های فشرده است.
- نقطهٔ شاخص مثل `tochal` همان هویت عمومی نقطه است و به
  `/points/{slug}` می‌رود. هیچ پروفایل یا موجودیت جداگانه‌ای وجود ندارد.
- endpoint قدیمی route-point و URLهای قدیمی redirect یا alias ندارند؛ لینک‌های
  داخلی و دادهٔ seed باید از slug نهایی استفاده کنند.

## تغییر نقاط و مسیرها

| قدیمی | نهایی |
| --- | --- |
| `touchal` | `tochal` |
| `touchal-darband` | `tochal-darband` |
| `touchal-welanjak` | `tochal-velenjak` |
| `touchal-kalkchal` | `tochal-kolakchal` |
| `touchal-shahrestanak` | `tochal-shahrestanak` |
| `touchal-ahar` | `tochal-ahar` |
| `azadkouh-kelakbala` | `azadkouh-kelak-bala` |
| `daryasar-asalmahaleh` | `daryasar-esel-mahalleh` |

## تغییر نقطه‌های مستقل

### توچال

| قدیمی | نهایی | نام صفحه |
| --- | --- | --- |
| `sarband` | `tochal-sarband-square` | میدان سربند |
| `pas_ghaleh` | `tochal-pas-ghaleh-village` | روستای پس‌قلعه |
| `shirpala` | `tochal-shirpala-shelter` | پناهگاه شیرپلا |
| `amiri` | `tochal-amiri-shelter` | جان‌پناه امیری |
| `goleband` | `tochal-goleband-ridge` | یال گوله‌بند توچال |
| `velenjak` | `tochal-velenjak-village` | ولنجک |
| `velenjak_parking` | `tochal-velenjak-parking` | پارکینگ مجموعهٔ توچال در ولنجک |
| `station_1`, `station_2`, `station_5`, `station_7` | `tochal-telecabin-station-1`, `-2`, `-5`, `-7` | ایستگاه تله‌کابین توچال |
| `qezqunchal_dopestan` | `tochal-qezqunchal-peak` | قلهٔ قزقون‌چال |
| `barfchal` | `tochal-barfchal-peak` | قلهٔ برف‌چال توچال |
| `homand_tochal` | `tochal-homand-tochal` | قلهٔ هومند توچال |
| `lezoon_east`, `lezoon_west` | `tochal-lezoon-east`, `tochal-lezoon-west` | قلهٔ لزون شرقی/غربی |
| `chahar_paloon` | `tochal-chahar-paloon` | قلهٔ چهارپالون |
| `jamshidieh_park` | `tochal-jamshidieh-park` | پارک جمشیدیه |
| `piyazchal_pass` | `tochal-piyazchal-pass` | گردنهٔ پیازچال |
| `espilat_sarlo_pass` | `tochal-espilat-sarlo-pass` | گردنهٔ اسپیلت و سرلو |
| `shakarab` | `tochal-shakarab-ahaar` | شکرآب آهار |
| `naseri_palace` | `shahrestanak-naseri-palace` | کاخ ناصری شهرستانک |

`tochal` نقطهٔ canonical است و slug سادهٔ نقطه را نگه می‌دارد. نقطهٔ `tochal_hotel`
نیز به `tochal-hotel` و `kolakchal_camp` به `tochal-kolakchal-camp` تبدیل شده‌اند.

### دماوند

`damavand_sulfur_hill` → `damavand-sulfur-hill` (تپهٔ گوگردی دماوند)،
`damavand_west_5008` → `damavand-west-5008`،
`damavand_western_parking` → `damavand-western-parking`،
هیچ رکورد تازه‌ای به کاتالوگ اضافه نشده است؛ داده‌های موجود عمداً در migration و
fixtureهای فعلی حفظ شده‌اند.
`damavand_northeast_north_join` → `damavand-northeast-north-junction`،
`damavand_sang_bozorg` → `damavand-sang-bozorg`، و
`damavand_shelter_4000`/`damavand_shelter_5000` →
`damavand-shelter-4000`/`damavand-shelter-5000` شدند. اگر مسیر غربی بعداً به
عارضهٔ میانی معتبر نیاز داشته باشد، تا زمان اثبات آن `pending` می‌ماند و نقطهٔ
ساختگی اضافه نمی‌شود.

### سایر نقاط

- دشت دریاسر: `daryasar_spring` → `daryasar-spring`؛ نام صفحه «چشمهٔ مسیر
  اِسِل‌محله تا دشت دریاسر» است.
- علم‌کوه: `alamkuh_siahsang` → `alamkuh-siahsang`؛ نام صفحه «سیاه‌سنگ
  علم‌کوه» است.
- گهر: `gahar_aligudarz_tapleh_trailhead` → `gahar-tapleh-trailhead`.
- زرین‌کوه: `zarrinkuh_khosravan_start` → `zarrinkuh-khosravan-village` و
  `zarrinkuh_aynehvarzan_start` → `zarrinkuh-aynehvarzan-parking`.
- هزار: `hazar_ardikan_babzangi_ridge` و
  `hazar_babzangi_route_junction` به نقطهٔ مشترک
  `hazar-ardikan-babzangi-junction` تبدیل شدند.
- درفک: `dorfak_south_spring` و `dorfak_west_jeyruni_spring` به نقطهٔ واحد
  `dorfak-jeyruni-spring` merge شدند.
- همهٔ نقطه‌های باقی‌ماندهٔ کاتالوگ‌های آزادکوه، دارآباد، سبلان و سایر نقاط
  از underscore به slug خط‌تیره‌ای تبدیل شده‌اند و metadata هویتی گرفته‌اند.

## حذف و merge

- رکوردهای synthetic با slugهای `dest:*` و `route:*` دیگر هویت عمومی ندارند؛
  در migration به canonical یا نقطهٔ مستقل متناظر منتقل و رکوردهای تکراری
  merge شدند.
- forecastهای ساعتی، روزانه و resolutionهای نقاط mergeشده به winner منتقل
  شدند و وابستگی RoutePoint، مبدأ/نقطه مسیر و پروفایل نقطه دوباره وصل شد.
- نقاط مستقل غیرقابل استفاده یا duplicate هویت عمومی نگه نداشتند. migration
  فقط duplicateهای قابل اثبات را حذف می‌کند و نقطهٔ operator-managed نامرتبط
  را خودکار تصاحب نمی‌کند.

## بررسی بعد از migration/import

در محیط تست یا سرور، بعد از migration و seed این دستور read-only را اجرا کنید:

```bash
docker compose --env-file .env -f infra/compose/compose.yaml exec -T api \
  python manage.py validate_catalog --database --strict
```

برای بررسی فایل‌های fixture بدون تغییر دیتابیس:

```bash
docker compose --env-file .env -f infra/compose/compose.yaml exec -T api \
  python manage.py validate_catalog --all --strict
```

هر خطای duplicate، slug نامعتبر، metadata ناقص، route کمتر از سه نقطه یا
canonical link ناقص باید پیش از کار SEO رفع شود. هشدار فاصلهٔ نزدیک دو نقطه
نیازمند بررسی curator است و نباید با تغییر کور مختصات پنهان شود.
