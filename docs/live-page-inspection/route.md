# بررسی read-only صفحهٔ Route

زمان بررسی: 2026-08-25. URL: `https://hawatch-weather.admirer135.chatgpt.site/routes/touchal-darband`

منبع labels: `[LIVE]` DOM/رفتار live، `[LIVE-BUNDLE]` assetهای JS/CSS live، `[SCREENSHOT]` تصاویر repository، `[PRODUCT]` درخواست محصول، `[BLOCKED]` منبع در دسترس‌نبوده.

## ۱. بخش‌های قابل مشاهده و ترتیب

ترتیب مشاهده‌شده در Route:

۱. header کوچک.
۲. `route-hero`: breadcrumb، title `دربند تا توچال` و status هشدار.
۳. `route-sibling-nav`: مسیرهای دیگر همان مقصد.
۴. `route-planner`: chip `انتخاب روز` و day tabs.
۵. `route-weather-card`: period toggle، محور نقاط مهم، hourly values و point weather cards.
۶. `stats-grid`: مسافت، صعود، زمان رفت‌وبرگشت، رسیدن به مقصد.
۷. side planner: ساعت شروع، speed controls و gauge.
۸. `route-decision`: forecast summary، وضعیت، decision، پیشنهادها و share actions.
۹. footer.

در mobile planner و decision در جریان عمودی صفحه قرار می‌گیرند؛ در desktop planner/decision در side و محتوای route در main چندستونه قرار می‌گیرند. [LIVE][SCREENSHOT]

## ۲. متن‌ها، عنوان‌ها، labelها و CTAها

| عنصر | متن دقیق مشاهده‌شده |
| --- | --- |
| breadcrumb | `مقصدها / قلهٔ توچال / دربند تا توچال` |
| title | `دربند تا توچال` |
| hero status | `نقطهٔ حساس: گردنهٔ لوپ · نقطهٔ حساس؛ زمان ذخیره داشته باش · حوالی ۱۰:۴۵` |
| sibling chip | `مسیرهای دیگر` |
| sibling parent | `قلهٔ توچال` |
| planner chip | `انتخاب روز` |
| weather chip | `نقاط مهم` |
| period | `صبح / ۰۰ تا ۱۲` و `بعدازظهر / ۱۲ تا ۲۴` |
| endpoint labels | `مبدا · دربند` و `مقصد · قلهٔ توچال` |
| quick label | `تنظیم سریع حرکت` |
| start label | `ساعت شروع` |
| speed label | `سرعت حرکت` |
| speed helper | `زمان رسیدن همهٔ نقاط با این انتخاب تغییر می‌کند.` |
| decision chip | `پیش‌بینی مسیر · امروز` |
| decision title | `با حرکت ساعت ۰۶:۰۰، حدود ۱۳:۰۰ به مقصد می‌رسی.` |
| decision status | `هشدار` |
| decision summary | `در حوالی گردنهٔ لوپ شرایط پرریسک می‌شود؛ امکان برگشت را از قبل در برنامه نگه دار.` |
| summary time | `۱۰:۴۵ · نقطهٔ حساس؛ زمان ذخیره داشته باش` |
| recommendation heading | `پیشنهادهای این برنامه` |
| recommendation 1 | `اگر رعدوبرق، باد شدید یا دید محدود فعال است، صعود را ادامه نده و زودتر برگرد.` |
| recommendation 2 | `باد در بخش حساس بالاست؛ بندهای کوله و باتوم را محکم کن و روی یال توقف طولانی نداشته باش.` |
| copy CTA | `کپی لینک برنامه` |
| Telegram CTA | `ارسال در تلگرام ↗` |
| footer | `هوای مقصد، برنامهٔ مسیر` |

نقاط مسیر و دادهٔ متناظر live:

| نقطه | زمان | دما | باد | state | href |
| --- | --- | --- | --- | --- | --- |
| دربند | ۰۶:۰۰ | ۸° | ۶ | normal | `/destination-point/darband` |
| شیرپلا | ۰۷:۲۰ | ۷° | ۱۱ | normal | `/destination-point/shirpala` |
| جان‌پناه امیری | ۰۹:۱۰ | ۵° | ۲۲ | change | `/destination-point/amiri-shelter` |
| گردنهٔ لوپ | ۱۰:۴۵ | ۳° | ۳۱ | critical | `/destination-point/loop-pass` |
| پناهگاه توچال | ۱۲:۱۰ | ۲° | ۳۶ | critical | `/destination-point/tochal-shelter` |
| قلهٔ توچال | ۱۳:۰۰ | ۱° | ۳۹ | critical | `/destination-point/tochal-summit` |

## ۳. لینک‌ها و navigation

| متن/نقش | href یا رفتار |
| --- | --- |
| هواچ | `/` |
| ورود | `/login` |
| back mobile | `/destination/touchal` با aria-label `بازگشت به صفحهٔ مقصد` |
| breadcrumb مقصدها | `/#search-results` |
| breadcrumb قلهٔ توچال | `/destination/touchal` |
| route sibling ولنجک | `/routes/touchal-welanjak` |
| route sibling کلکچال | `/routes/touchal-kalkchal` |
| route sibling شهرستانک | `/routes/touchal-shahrestanak` |
| route sibling آهار | `/routes/touchal-ahar` |
| route point | `/destination-point/{pointSlug}` |
| share initial href | `/share`، target `_blank` |
| Telegram after click | `https://t.me/share/url?...` با query رمزگذاری‌شدهٔ plan |

## ۴. رفتار دکمه‌ها، toggleها، tabها، inputها و کارت‌ها

- theme toggle با localStorage `hawatch-theme` کار می‌کند.
- day tabs با state داخلی شروع از `امروز` هستند؛ کلیک tab، day index را تغییر می‌دهد و arrival/weather/decision را recompute می‌کند.
- period با `صبح`/`بعدازظهر` در UI و stateهای `morning`/`night` در bundle کنترل می‌شود؛ helperهای route point و hourly با آن تغییر می‌کنند.
- speed options دقیقاً `آرام`، `متوسط`، `سریع` هستند و multiplierهای bundle به‌ترتیب `1.2`، `1` و `.82` است. انتخاب در localStorage key `hawatch-plan-speed-{slug}` ذخیره می‌شود.
- start range input با aria-label `ساعت شروع حرکت`، `step=30` و min/max بازهٔ period دارد. onChange ساعت شروع را ذخیره و زمان همهٔ نقاط را update می‌کند.
- point axis card و point weather card هر دو به destination-point link هستند و state خود را با class `normal/change/critical` نشان می‌دهند.
- copy CTA لینک plan را با `navigator.clipboard.writeText` یا fallback textarea کپی می‌کند؛ success text `لینک کپی شد ✓`، failure text `کپی ناموفق بود` و بعد از ۲۴۰۰ms به idle برمی‌گردد. [LIVE-BUNDLE]
- Telegram CTA ابتدا `/share` دارد و هنگام click href را با URL رمزگذاری‌شدهٔ t.me جایگزین می‌کند.

## ۵. بازگشت بین Home، Destination و Route

Home → Destination با tile؛ Destination → Route با route card؛ Route → Destination با back link یا breadcrumb؛ brand از هر صفحه به Home. در Route breadcrumb مقصد نیز به `/destination/touchal` برمی‌گردد. [LIVE]

## ۶. انتخاب روز، صبح/بعدازظهر، ساعت شروع و سرعت

- default day: امروز، index ۱.
- day tabs: دیروز ۲۶ مرداد، امروز ۲۷ مرداد، فردا ۲۸ مرداد، چهارشنبه ۲۹ مرداد، پنجشنبه ۳۰ مرداد، جمعه ۳۱ مرداد، شنبه ۱ شهریور.
- default period: صبح `۰۰ تا ۱۲`.
- start default: `۰۶:۰۰`؛ ticks live `۰۰:۰۰` تا `۱۰:۰۰` در بازهٔ نمایش‌شده.
- speed default: متوسط.
- route plan زمان رسیدن را با speed multiplier و baseMinutes نقاط محاسبه می‌کند؛ state critical در نقطه یا arrival time بالا decision state را تعیین می‌کند. [LIVE-BUNDLE]

## ۷. مسیرهای دیگر همان مقصد

در sibling nav مسیر current حذف شده و چهار مسیر دیگر با distance نمایش داده می‌شوند: ولنجک تا توچال `۱۴٫۸ km`، کلکچال تا توچال `۱۷٫۴ km`، شهرستانک تا توچال `۱۸٫۶ km`، آهار تا توچال `۱۸٫۶ km`. [LIVE]

## ۸. کارت تصمیم، هشدار، اشتراک‌گذاری و نقاط مسیر

- hero warning نقطهٔ حساس و زمان آن را برجسته می‌کند.
- route axis از origin دربند تا destination قلهٔ توچال شش node دارد.
- hourly grid شش بازهٔ ۰۰:۰۰، ۰۲:۰۰، ۰۴:۰۰، ۰۶:۰۰، ۰۸:۰۰ و ۱۰:۰۰ دارد؛ ۰۴:۰۰ change و ۰۶:۰۰ تا ۱۰:۰۰ critical هستند.
- point weather grid برای هر نقطه time، icon، condition، temperature، wind و status label دارد.
- decision card در نمونهٔ live critical است، `هشدار` دارد، زمان شروع/رسیدن/سرعت/نقطهٔ حساس را خلاصه می‌کند، دو recommendation دارد و دو share action ارائه می‌دهد.

## ۹. تفاوت mobile و desktop

| مورد | mobile 576px | desktop 1905px |
| --- | --- | --- |
| header | observed 552×75px | observed 1416×92px |
| hero | observed 552×116px، radius 25px، padding 12px 16px | observed 1416×230px، radius 25px، padding حدود 42px 40px 30px |
| sibling routes | دو ستونه/فشرده و card کوچک | نوار افقی زیر hero |
| planner | کنترل‌ها در flow عمودی؛ ساعت و سرعت باید compact بمانند | main/side layout؛ gauge و speed در side |
| point weather | محور و cardها با تراکم زیاد در عرض صفحه | محور و hourly/point cards در پنل بزرگ |
| decision | full width، observed حدود 552px و radius 14px | side card حدود 300px و radius حدود 17px |
| stats | چهار card در grid mobile | چهار stat card در یک ردیف |
| overflow | root measured بدون overflow | root measured بدون overflow |

## ۱۰. تفاوت light و dark

- light body `rgb(201,220,218)`، text `#173746`، route hero زمینهٔ teal تیره و decision critical زمینهٔ beige/coral با border amber/coral.
- dark body `#0b2732`، text `#edf7f4`، surface آبی-سبز، route hero gradient teal، decision critical با border coral و shadow تیره.
- computed route decision light: border `rgb(184,156,92)`، radius 17px، shadow حدود `0 10px 24px rgba(16,43,61,.075)`.
- computed route decision dark: border `rgba(237,137,123,.84)`، radius 17px، shadow حدود `0 14px 30px rgba(0,0,0,.16)`.
- semantic severity در هر دو theme با labelهای فارسی و status class قابل تشخیص است. [LIVE CSS/DOM]

## ۱۱. اندازه، فاصله، رنگ، border، radius، shadow و typography

- font computed: `Vazirmatn, "Noto Sans Arabic", Tahoma, Arial, sans-serif`، 16px، line-height 27.2px.
- route hero desktop/mobile radius 25px؛ desktop shadow light حدود `0 11px 26px rgba(16,43,61,.12)` و dark حدود `0 16px 36px rgba(0,0,0,.2)`.
- standard card radius 18px؛ mobile standard card observed radius 18px، decision mobile 14px.
- theme toggle desktop height 33px و mobile 38px، radius 999px.
- light page body `#c9dcda`، dark `#0b2732`؛ light text `#173746` و dark text `#edf7f4`.
- live CSS brand teal `#1d7f86`، dark teal `#61c5c0`، amber dark `#f0bd61` و coral dark `#ed897b`.

## ۱۲. loading، empty، error و stale-data

- loading: **BLOCKED**؛ Route experience static data را synchronous از props می‌گیرد و page-specific loading UI ندارد.
- empty route/forecast: **BLOCKED** برای route معتبر Touchal؛ route point list ثابت است و branch خالی در URL بررسی‌شده فعال نیست.
- error: **PARTIAL**؛ فقط failure کپی لینک در source bundle با `کپی ناموفق بود` وجود دارد. error برای forecast/provider/API مشاهده نشد.
- stale: **BLOCKED**؛ timestamp/freshness یا stale badge در Route live وجود ندارد.

این وضعیت‌ها بدون منبع حدس زده نمی‌شوند و در `docs/open-questions.md` آمده‌اند.

## ۱۳. داده‌ها و API آینده

- live route از `site-data-DQ0UR-FX.js` route object و point data می‌گیرد و `route-experience-DjDtmwVB.js` derived timing/weather/decision را client-side محاسبه می‌کند. [LIVE-BUNDLE]
- page-specific route bundle هیچ provider URL، Open-Meteo یا `/api` weather call ندارد؛ RSC navigation framework fetch با provider weather اشتباه نشود.
- future product need: route catalog، forecast normalized، route plan computation و share payload. [PRODUCT]
- endpointهای پیشنهادی not-live: `GET /api/v1/routes/{slug}`، `GET /api/v1/routes/{slug}/plan?...` و share contract آینده.

## ۱۴. محدودیت overflow و responsive

- root document/body در هر چهار ترکیب اندازه‌گیری‌شده overflow افقی نداشت.
- در mobile route linear axis باید در container خودش قابل اسکن/scroll باشد و root را عریض نکند.
- زمان، سرعت و gauge باید در یک composition فشرده بمانند؛ خط جداکنندهٔ عمودی desktop نباید به mobile منتقل شود. `[PRODUCT]` و `[SCREENSHOT]`
- route point axis و weather cards باید از نظر ترتیب origin→destination هم‌معنا بمانند، حتی اگر layout فشرده شود.

## ۱۵. معیار پذیرش قابل تست

| بخش | معیار تست |
| --- | --- |
| navigation | back به `/destination/touchal`، breadcrumb مقصد به همان URL و siblingها به routeهای درست می‌روند. |
| day/period | default امروز/صبح است؛ کلیک day و period state active و دادهٔ derived را تغییر می‌دهد. |
| planner | start default ۰۶:۰۰ و speed متوسط است؛ تغییر start/speed زمان رسیدن و decision title را update می‌کند. |
| points | شش نقطه با نام/زمان/دما/باد و href درست روی axis و cardها render می‌شوند. |
| decision | status، critical point، start/finish، recommendations و copy/Telegram CTA قابل مشاهده‌اند. |
| share | copy success/failure label درست و Telegram link دارای payload رمزگذاری‌شده است. |
| responsive | در mobile root overflow ندارد و controls compact هستند؛ در desktop main/side composition حفظ می‌شود. |
| state gaps | loading/forecast error/stale تا contract آیندهٔ داده تصویب نشده، PASS تلقی نشوند. |

## منابع و محدودیت evidence

- live DOM، computed style، interaction، screenshot و JS bundle: `[LIVE]`/`[LIVE-BUNDLE]`.
- images: `design/screens/route/{light,dark}/{mobile,web}.png`. `[SCREENSHOT]`
- سورس local `/workspace/sites/hawatch-weather`: `[BLOCKED]`.
- Hawatch.docx: `[BLOCKED]`.
- الزام mobile/desktop، RTL، overflow و no implementation: `[PRODUCT]`.

