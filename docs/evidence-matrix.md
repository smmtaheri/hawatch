# ماتریس evidence هواچ

تاریخ بررسی: 2026-08-28

این ماتریس منبع هر تصمیم validation را مشخص می‌کند. `LIVE-BUNDLE` یعنی JavaScript/CSS منتشرشدهٔ همان سایت، نه source محلی. موارد آینده از رفتار فعلی live جدا نگه داشته شده‌اند.

## کد منابع

| کد | منبع |
| --- | --- |
| `PRODUCT` | درخواست صریح محصول، قوانین `AGENTS.md` و محدودیت این milestone |
| `SCREENSHOT-SOURCE` | PNGهای اصلی در `design/source-screens/` |
| `SCREENSHOT-ORG` | PNGهای مرتب‌شده در `design/screens/` |
| `LIVE-H` | DOM، computed style و interaction صفحهٔ Home live |
| `LIVE-D` | DOM، computed style و interaction صفحهٔ Destination live |
| `LIVE-R` | DOM، computed style و interaction صفحهٔ Route live |
| `LIVE-BUNDLE` | assetهای script/style لینک‌شده از HTML live شامل page/data/experience bundles |
| `DOCX` | `references/Hawatch.docx`؛ فایل موجود و خوانده‌شده |
| `LOCAL-SOURCE` | `/workspace/sites/hawatch-weather`؛ در این محیط موجود نیست و طبق تصمیم کاربر reference unavailable و non-gating است |
| `GIT` | `git status --short --branch` و history فعلی؛ commitهای مستندشدهٔ repository |
| `LOCAL-IMPLEMENTATION` | source فعلی همین repository در `apps/web` و `apps/api`؛ برای رفتار اجراشده، جدا از reference live |

## repository و تصاویر

| جزئیات | منبع | evidence |
| --- | --- | --- |
| تعداد assetهای منطقی | `SCREENSHOT-SOURCE` + `SCREENSHOT-ORG` + manifest + `PRODUCT` | ۴ صفحه × ۲ تم × ۲ دستگاه = ۱۶ asset؛ ۱۶ source و ۱۶ organized copy طبق تصمیم قطعی کاربر |
| تعداد فایل فیزیکی | `SCREENSHOT-SOURCE` + `SCREENSHOT-ORG` + `PRODUCT` | ۳۲ PNG فیزیکی؛ duplicateهای source/organized عمدی و مجاز هستند و شمارش منطقی همچنان ۱۶ است |
| نام و مسیر هر تصویر | manifest + filesystem | `design/manifest.json`، مسیرهای `design/source-screens/` و `design/screens/{page}/{theme}/{device}.png` |
| width/height | manifest + `identify` | 576×1077 یا 1905×1047 برای Home/Login؛ 576×1729 یا 1905×1602 برای Destination؛ Route mobile 576×2528/2564 و web 1905×1457 |
| hash و عدم re-encode pairها | manifest + filesystem | ۱۶/۱۶ SHA-256 source و organized match؛ source و organized هرکدام ۱۶ hash unique دارند |
| نبودن PNG خارج از scope | filesystem | جست‌وجوی repository به‌جز `.git` فقط دو مجموعهٔ مجاز را یافت |

## DOCX و design system

| جزئیات | منبع | evidence |
| --- | --- | --- |
| نام محصول و هویت تصمیم‌محور | `DOCX` | پاراگراف‌های ۱ تا ۷: دیدن مقصد، تغییر مسیر و تصمیم زمان/مسیر |
| فارسی، RTL و Estedad | `DOCX` + `PRODUCT` + local implementation | پاراگراف‌های ۸ تا ۱۶؛ HTML دارای `lang=fa` و `dir=rtl`؛ `design/tokens/typography.md` و `apps/web/public/fonts/` |
| dark palette | `DOCX` + tokens + `PRODUCT` | پاراگراف‌های ۱۷ تا ۲۸؛ طبق تصمیم قطعی، مقدار canonical فقط از `design/tokens/visual-tokens.json` خوانده می‌شود |
| light palette | `DOCX` + tokens + live + `PRODUCT` | پاراگراف‌های ۲۹ تا ۴۰ DOCX بررسی شد؛ اختلاف‌های قبلی با تصمیم canonical بودن `visual-tokens.json` حل و markdownها توضیحی تلقی شدند |
| لوگو و icon طبیعت | `DOCX` + design system | پاراگراف‌های ۴۱ تا ۵۲؛ `design/system/design-system.md` و `component-inventory.md` |
| radius، border، shadow و semantic color | `DOCX` + tokens + live | پاراگراف‌های ۵۳ تا ۶۱؛ `design/tokens/visual-tokens.json` و live computed styles |
| hierarchy اطلاعات | `DOCX` + `PRODUCT` | پاراگراف‌های ۶۲ تا ۷۲؛ تصمیم → تغییر هوا → مسیر/زمان → جزئیات فنی |
| نبایدها | `DOCX` + AGENTS | پاراگراف‌های ۷۳ تا ۸۱؛ no pure-white admin feel، no font mixing، no heavy shadow و no technical detail before decision |

## Home

| جزئیات | منبع | evidence |
| --- | --- | --- |
| ترتیب بخش‌ها | `LIVE-H` + `SCREENSHOT-SOURCE` | `docs/live-page-inspection/home.md` §۱: header، hero copy، search، heading، destination grid |
| متن‌ها، title، label و CTA | `LIVE-H` + `LIVE-BUNDLE` | همان سند §۲: title/description، «هوای مسیرت را ببین»، placeholder، «جست‌وجو»، «مقصدهای محبوب/نتایج مرتبط» و empty copy |
| لینک‌ها و navigation | `LIVE-H` | §۳: brand `/`، Login `/login` و شش destination href |
| theme، input، search و tile behavior | `LIVE-H` + `LIVE-BUNDLE` | §۴: `hawatch-theme`، normalize فارسی، filter روی name/type، max شش result و submit بدون provider/API |
| flow و back | `LIVE-H` + `PRODUCT` | §۵ و `docs/user-flows/home-to-destination.md`؛ Home → Destination و brand/back context |
| نبودن route/decision/share در Home | `LIVE-H` | §۶ تا §۸ |
| mobile/desktop | `LIVE-H` + screenshots | §۹ و tokens observed: mobile 576، grid دو ستونه؛ web 1905، row شش‌تایی؛ root بدون overflow |
| light/dark و visual values | `LIVE-H` + `SCREENSHOT-SOURCE` + `LOCAL-IMPLEMENTATION` | §۱۰ و §۱۱: body، search/tile، radius، border، shadow و Estedad |
| loading/empty/error/stale | `LIVE-H` + `LIVE-BUNDLE` + `PRODUCT` | §۱۲: empty مشاهده شد؛ contract قطعی آینده skeleton، error همان بخش + retry، stale با دادهٔ قبلی/زمان/هشدار کهربایی و empty/error مستقل است |
| future data/API | `PRODUCT` + `docs/api/*` | §۱۳ live static بودن را جدا از endpointهای پیشنهادی آینده ثبت می‌کند |
| responsive constraint و acceptance | `LIVE-H` + `PRODUCT` | §۱۴ و §۱۵؛ search overlap/root overflow ممنوع |

## Destination

| جزئیات | منبع | evidence |
| --- | --- | --- |
| ترتیب بخش‌ها | `LIVE-D` + screenshots | `docs/live-page-inspection/destination.md` §۱: header، breadcrumb/hero، forecast، day tabs، period، hourly، metrics، routes، decision |
| متن‌ها و داده‌های قابل مشاهده | `LIVE-D` + `LIVE-BUNDLE` | §۲: title توچال، current، alert، updated، hourly، metrics و decision copy |
| لینک‌ها و routeهای دیگر | `LIVE-D` | §۳ و §۷: پنج route Touchal و hrefهای دقیق |
| انتخاب day و period | `LIVE-D` + `LIVE-BUNDLE` | §۴ و §۶: هفت day tab، `aria-selected`، صبح/بعدازظهر و تغییر hourly heading |
| forecast cards، legend و metrics | `LIVE-D` | §۱ و §۸: normal/change/critical، باد، دید، UV، بارش، طلوع/غروب |
| flow و back | `LIVE-D` + `docs/user-flows/destination-to-route.md` | §۵: Home → Destination → Route و parent destination |
| mobile/desktop | `LIVE-D` + screenshots | §۹: hero 548×116 mobile و 1416×250 web، route grid، root بدون overflow |
| light/dark و visual values | `LIVE-D` + `SCREENSHOT-SOURCE` | §۱۰ و §۱۱: body/surface/text/teal/amber/coral، border/radius/shadow/type |
| loading/empty/error/stale | `LIVE-D` + `LIVE-BUNDLE` + `PRODUCT` | §۱۲: route-empty branch در Touchal active نیست؛ contract قطعی stateها در بخش DOCX/product ثبت شده و رفتار live مشاهده‌نشده به‌عنوان implementation ادعا نمی‌شود |
| future API و داده | `PRODUCT` + `docs/api/forecast-contract.md` | §۱۳: current static بودن و نیاز آیندهٔ internal API، normalized forecast و freshness |
| overflow و acceptance | `LIVE-D` + `PRODUCT` | §۱۴ و §۱۵: روزها قبل از controls و root overflow ممنوع |

## Route

| جزئیات | منبع | evidence |
| --- | --- | --- |
| ترتیب بخش‌ها | `LIVE-R` + screenshots | `docs/live-page-inspection/route.md` §۱: hero، sibling nav، planner، weather/points، stats، decision، share |
| متن‌ها، alert و decision | `LIVE-R` + `LIVE-BUNDLE` | §۲: breadcrumb، title، sensitive point، planner labels، recommendations و share labels |
| شش point مسیر | `LIVE-R` + `LIVE-BUNDLE` | §۳: دربند، شیرپلا، جان‌پناه امیری، گردنهٔ لوپ، پناهگاه توچال، قلهٔ توچال با زمان/دما/باد/state/href |
| sibling route navigation | `LIVE-R` | §۳ و §۷: چهار route دیگر و distance |
| day/period/start/speed | `LIVE-R` + `LIVE-BUNDLE` | §۴ و §۶: روز، صبح/بعدازظهر، range با step=30، default 06:00، speed آرام/متوسط/سریع و multiplierهای sample |
| derived arrival و critical decision | `LIVE-R` + `LIVE-BUNDLE` | §۴ و §۸: زمان رسیدن، نقطهٔ حساس، warning و recommendation |
| share copy و Telegram | `LIVE-R` + `LIVE-BUNDLE` | §۴ و §۸: clipboard/fallback، success/failure copy و dynamic Telegram URL |
| flow و back | `LIVE-R` + `docs/user-flows/navigation-and-back.md` | §۵: brand → Home، breadcrumb/back → Destination و sibling route |
| mobile/desktop | `LIVE-R` + screenshots | §۹: hero 552×116 mobile، decision full width؛ web hero 1416×230 و decision حدود 300px؛ root بدون overflow |
| light/dark و visual values | `LIVE-R` + `SCREENSHOT-SOURCE` | §۱۰ و §۱۱: semantic severity، body/surface، border/radius/shadow/type |
| loading/empty/error/stale | `LIVE-R` + `LIVE-BUNDLE` + `PRODUCT` | §۱۲: loading/stale در live expose نشده و copy failure partial است؛ contract قطعی stateها برای آینده ثبت شده و empty/error مستقل می‌مانند |
| future plan API | `PRODUCT` + `docs/api/*` | §۱۳: endpoint پیشنهادی future و ممنوعیت اتصال مستقیم frontend به provider/database |
| overflow و acceptance | `LIVE-R` + `PRODUCT` | §۱۴ و §۱۵: root overflow ممنوع و scoped axis behavior در OQ-013 |

## Login

| جزئیات | منبع | evidence |
| --- | --- | --- |
| وجود asset و metadata | `SCREENSHOT-SOURCE` + manifest | `hawatch_05` تا `hawatch_08` و مسیرهای `design/screens/login/{light,dark}/{mobile,web}.png` |
| layout، component، text و interaction contract | `PRODUCT` + screenshot + design docs | `design/pages/login.md` و `docs/page-specs/login-behavior.md`؛ Login route-backed overlay پیاده شده است |
| stateها | `PRODUCT` + design docs | شماره input واقعی است، CTA OTP تا آماده‌شدن API disabled است و علت آن اعلام می‌شود |
| responsive و light/dark | screenshot + page doc | چهار تصویر Login canonical به‌علاوهٔ دو reference flow در `design/screens/login/reference/` |
| live Login | `LOCAL-IMPLEMENTATION` | mobile تمام‌صفحه، desktop dialog و direct `/login?returnTo=…` صفحهٔ کامل است؛ OTP/backend هنوز فعال نیست |

## API، معماری و مرزبندی implementation

| جزئیات | منبع | evidence |
| --- | --- | --- |
| internal API و عدم اتصال مستقیم frontend | `PRODUCT` + docs | `AGENTS.md`، `docs/api/api-overview.md`، `docs/architecture/frontend.md` |
| Django REST Framework، PostgreSQL، Python 3.14، uv | `PRODUCT` + docs | `README.md` و `docs/architecture/backend.md`؛ compatibility فقط به‌عنوان preflight آینده ثبت شده |
| Redis/queue/Kafka/data lake | `PRODUCT` + ADR + Compose | pipeline docs و ADR 0002/0003؛ Redis فقط profile `cache`؛ Kafka و data lake runtime ندارند |
| raw/normalized، retention حداکثر یک هفته و cleanup | `PRODUCT` + pipeline doc | `docs/architecture/weather-data-pipeline.md` §raw، §retention و cleanup policy |
| retry، backoff، checkpoint، heartbeat و no-concurrent-run | `PRODUCT` + LOCAL implementation + ADR | ingest صریح retry/lock/checkpoint دارد و maintenance/retention جداست؛ queue/worker دائمی و Kafka runtime این milestone نیستند |
| implementation محلی | filesystem + tests | `apps/web`، `apps/api`، `infra/compose`، seed دمو و تست‌های Vitest/pytest؛ ادعای «فقط `.gitkeep`» منسوخ است |

## هم‌ترازی با implementation فعلی

| جزئیات | منبع | evidence |
| --- | --- | --- |
| جست‌وجوی unified Home | `LOCAL-IMPLEMENTATION` + `PRODUCT` | `apps/web/src/components/SearchCombobox.tsx`، `features/home/HomePage.tsx` و `apps/web/src/api/client.ts`; پیشنهادها از `/api/v1/search/suggestions/` می‌آیند، حداقل دو کاراکتر و debounce حدود ۲۰۰ms دارند، و submit destination-only fallback ندارد. |
| نتیجهٔ خطای جست‌وجو | `LOCAL-IMPLEMENTATION` | SearchCombobox وضعیت error را نگه می‌دارد و Home پیام خطا و retry ارائه می‌کند؛ query از بین نمی‌رود. |
| صفحهٔ canonical نقطه | `LOCAL-IMPLEMENTATION` + `PRODUCT` | `apps/web/src/features/point/PointDetailPage.tsx` و `PointNavigation.tsx`؛ مسیر عمومی `/points/{slug}`، بدون timing planner و با related routes در ورود مستقیم. |
| API نقطه و جست‌وجو | `LOCAL-IMPLEMENTATION` | `apps/api/src/hawatch/api/v1/urls.py` و `views.py`؛ endpointهای point forecast و search suggestions اجرایی‌اند. |
| Route → Point و back context | `LOCAL-IMPLEMENTATION` | Route point links URL تمیز می‌سازند؛ `location.state.fromRoute` شامل pathname/search/href است و queryهای `date`، `period`، `start_time` و `speed` را برای بازگشت restore می‌کند. |
| period فعلی | `LOCAL-IMPLEMENTATION` + `PRODUCT` | `apps/api/src/hawatch/common/time.py` و `apps/web/src/lib/periods.ts`؛ Asia/Tehran و سه پنجرهٔ ۰۳–۱۱، ۱۱–۱۹، ۱۹–۰۳ با چهار ساعت دوساعته در هر پنجره. |
| Point در design handoff | `SCREENSHOT-SOURCE` + `LOCAL-IMPLEMENTATION` | screenshot مستقل Point وجود ندارد؛ `design/pages/point.md` آن را extension سیستم Destination معرفی می‌کند و ادعای pixel-perfect ندارد. |

## evidenceهای مسدود

| موضوع | وضعیت | دلیل |
| --- | --- | --- |
| source محلی | BLOCKED | `/workspace/sites/hawatch-weather` وجود ندارد؛ طبق تصمیم کاربر reference unavailable است و validation را متوقف نمی‌کند؛ OQ-001 |
| referenceهای قدیمی probe/result | BLOCKED | فایل‌های تاریخی `/workspace/scratch/...` در checkout فعلی موجود نیستند؛ manifest به DOCX repository اشاره می‌کند؛ OQ-002 |
| canonical tokenها | PASS | `design/tokens/visual-tokens.json` تنها منبع مقدارهاست؛ markdownها توضیح‌دهنده‌اند؛ OQ-004 resolved |
| loading/error/stale و empty/error | PASS | contract قطعی کاربر ثبت شد؛ عدم مشاهدهٔ branch در live با پیاده‌سازی موجود اشتباه نمی‌شود |
| تغییرات خارج از scope | `GIT` + `PRODUCT` | وضعیت working tree در هر validation جداگانه بررسی می‌شود؛ تغییرات design/docs و runtime باید جداگانه review شوند و فایل‌های PNG بدون تغییر بمانند. |

## قاعدهٔ استفاده

هر مقدار دارای `[PRODUCT]` یا future docs، رفتار فعلی سایت live محسوب نمی‌شود مگر با evidence جدا. source محلی unavailable به‌صورت non-gating ثبت شده است. implementation محلی فعلی از API داخلی و دادهٔ دمو استفاده می‌کند؛ مسیر ingest واقعی وجود دارد اما فقط با command/provider صریح اجرا می‌شود. OTP واقعی و ingestion خودکار startup خارج از scope هستند.
