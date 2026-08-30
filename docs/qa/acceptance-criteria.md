# معیارهای پذیرش نسخهٔ فعلی هواچ

این سند معیار پذیرش repository اجرایی فعلی است، نه handoff اولیهٔ placeholder. منبع مقدارهای بصری فقط `design/tokens/visual-tokens.json` است و Login در این milestone فقط reference طراحی است.

## repository و اجرای محلی

- [ ] repository در مسیر checkout فعلی `hawatch` قرار دارد و ساختار monorepo شامل `apps/web`، `apps/api`، `infra` و `scripts` است.
- [ ] frontend با React، TypeScript، Vite و React Router اجرا می‌شود.
- [ ] backend با Django REST، PostgreSQL/PostGIS و migrationهای موجود اجرا می‌شود.
- [ ] Compose سبک شامل postgres، api، web، ingest one-shot، `ingest-scheduler` و maintenance است؛ Redis و observability profile اختیاری‌اند.
- [ ] frontend فقط API داخلی را مصرف می‌کند و مستقیماً به provider یا database وصل نمی‌شود.

## تصاویر و design handoff

- [ ] دقیقاً ۱۶ asset منطقی از چهار صفحهٔ Home، Login، Destination و Route، در دو theme و دو device وجود دارد.
- [ ] ۱۶ PNG در `design/source-screens/` byte-for-byte حفظ شده و ۱۶ organized copy در `design/screens/{page}/{theme}/{device}.png` قرار دارد.
- [ ] نام، مسیر، ابعاد و SHA-256 در `design/manifest.json` با فایل واقعی match است.
- [ ] هیچ تصویر resize، compress یا re-encode نشده است.
- [ ] Point screenshot مستقل ندارد و مستندات آن را extension سیستم Destination معرفی می‌کنند؛ تصویر جدیدی بدون منبع ساخته نمی‌شود.
- [ ] ۱۶ asset مرجع دست‌نخورده باقی می‌مانند؛ اصلاحات Point با reuse الگوی Destination مستند می‌شوند و تصویر ساختگی/بدون منبع اضافه نمی‌شود.

## صفحات و navigation

- [ ] Home (`/`) جست‌وجوی unified مقصد و نقطه را با `GET /api/v1/search/suggestions/?q=` و حداقل دو کاراکتر، normalize، prefix match و debounce حدود ۲۰۰ms انجام می‌دهد.
- [ ] Submit/Enter جست‌وجوی destination-only fallback ندارد؛ یک نتیجه مستقیم باز می‌شود و چند نتیجه در فهرست unified نمایش داده می‌شود.
- [ ] Destination (`/destination/{slug}`) مقصد، forecast، روز، سه بازه و مسیرهای مرتبط را نمایش می‌دهد.
- [ ] Route (`/routes/{slug}`) planner، نقاط و weather pointهای مسیر را نمایش می‌دهد.
- [ ] Point (`/points/{weatherPointSlug}`) صفحهٔ canonical مستقل برای WeatherPoint است و timing planner ندارد.
- [ ] point مقصدی مثل `tochal_summit` به `/destination/touchal` canonical می‌رود و صفحهٔ standalone موازی ندارد.
- [ ] `/points/sarband` همان shell بصری Destination را دارد (بدون `.point-page`).
- [ ] Destination و Point از یک `PlaceForecastPage` رندر می‌شوند.
- [ ] لینک Route به Point تمیز است؛ context کامل Route در `location.state.fromRoute` نگه داشته می‌شود.
- [ ] بازگشت Point که از Route باز شده، `date`، `period`، `start_time` و `speed` را restore می‌کند؛ ورود مستقیم/refresh دکمهٔ back گمراه‌کننده ندارد.

## forecast، period و stateها

- [ ] همهٔ صفحات forecast از timezone رسمی `Asia/Tehran` استفاده می‌کنند.
- [ ] بازه‌ها غیرهم‌پوشان و چهار کارت دوساعته دارند: صبح ۰۳/۰۵/۰۷/۰۹، بعدازظهر ۱۱/۱۳/۱۵/۱۷، شب ۱۹/۲۱/۲۳/۰۱.
- [ ] بدون query صریح، backend بازه و روز را بر اساس ساعت تهران تعیین می‌کند؛ query صریح اولویت دارد.
- [ ] loading با skeleton و حفظ layout، error با پیام همان بخش و retry، empty مستقل از error، و stale با دادهٔ قبلی/زمان آخرین update/هشدار کهربایی نمایش داده می‌شوند.
- [ ] partial data بدون صفرسازی یا مقدار ساختگی نمایش داده می‌شود.
- [ ] تغییر روز یا period دادهٔ همان context را refresh می‌کند؛ route timing pending مقدار ساختگی برای ETA، distance یا ascent تولید نمی‌کند.
- [ ] periodهای کاملاً گذشته با ساعت رسمی تهران dim هستند و period جاری واضح است.
- [ ] Route در timing pending متن خام `timing pending`، ETA ساختگی یا fallback ثابت ظهر برای period انتخاب‌شده ندارد.
- [ ] پنج مسیر توچال پس از seed با timing تخمینی v3 کار می‌کنند (شامل شهرستانک ترکیبی). نشان `تخمینی · ±N دقیقه`، بدون fallback قله و بدون ادعای زمان قطعی یا کالیبراسیون میدانی کامل.
- [ ] مبدأ ولنجک `velenjak_parking` است؛ WeatherPoint عمومی `velenjak` حذف نمی‌شود.
- [ ] تغییر start time یا speed arrival و انتخاب forecast نقطه را دوباره محاسبه می‌کند و می‌تواند از مرز period/نیمه‌شب عبور کند.
- [ ] `state` کارت نقطه و تصمیم مسیر فقط از severity پیش‌بینی نقطه‌ای matched ساخته می‌شود؛ آستانهٔ دیررسیدن یا بازنویسی hourly مقصد از critical نقطه ممنوع است.
- [ ] Route timeline دمای زیر marker و headline «تغییرات شب · هر دو ساعت» را نمایش نمی‌دهد.
- [ ] Destination/Point هم `period.headline` را نشان نمی‌دهند؛ فقط کارت ساعتی + legend.
- [ ] Route cards زیر timeline برای هر RoutePoint و زمان رسیدن محاسبه‌شده‌اند، نه forecast عمومی مقصد یا عنوان period مشترک بالای همهٔ نقاط.
- [ ] label بالای day tabs در Destination و Point «انتخاب روز» است و timestamp خام update نمایش داده نمی‌شود.

## responsive، theme و دسترسی‌پذیری

- [ ] چهار حالت light/dark و mobile/desktop برای Home، Destination و Route بدون root horizontal overflow قابل استفاده‌اند.
- [ ] Point در light/dark استایل هم‌خانواده با Destination دارد و در ورود از Route sidebar خالی ایجاد نمی‌کند.
- [ ] Point در light/dark از همان surface، typography و spacing Destination استفاده می‌کند؛ related routes در sidebar فشرده و تک‌ستونه‌اند.
- [ ] root و محتوای فارسی RTL، فونت Vazirmatn و focus/keyboard stateهای قابل دسترس دارند.
- [ ] scroll داخلی، در صورت نیاز، scoped به همان محور/کانتینر است و root را عریض نمی‌کند.

## مستندات و کیفیت

- [ ] README، AGENTS، design pages، page specs، API contract، architecture، ADRها و user flowها با implementation فعلی تناقض ندارند.
- [ ] `docs/open-questions.md` موارد تصمیم‌نشده و source unavailable را صریح ثبت می‌کند.
- [ ] تست frontend، تست backend، type-check و `git diff --check` اجرا و نتیجهٔ واقعی ثبت می‌شوند.
- [ ] Login، provider واقعی، Kafka، Kubernetes و share server-side فقط به‌عنوان خارج از scope/مسیر توسعه ثبت شده‌اند، نه قابلیت آمادهٔ فعلی.
