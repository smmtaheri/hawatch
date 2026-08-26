# ماتریس evidence هواچ

تاریخ بررسی: 2026-08-26

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
| `GIT` | `git status --short --branch` و commit اولیه؛ baseline این handoff با پیام مشخص ساخته شد |

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
| فارسی، RTL و Vazirmatn | `DOCX` + `PRODUCT` + live | پاراگراف‌های ۸ تا ۱۶؛ HTML live دارای `lang=fa` و `dir=rtl`؛ `design/tokens/typography.md` |
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
| light/dark و visual values | `LIVE-H` + `SCREENSHOT-SOURCE` | §۱۰ و §۱۱: body، search/tile، radius، border، shadow و Vazirmatn |
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
| layout، component، text و interaction contract | `PRODUCT` + screenshot + design docs | `design/pages/login.md` و `docs/page-specs/login-behavior.md`؛ Login در این milestone reference است و implementation ندارد |
| stateها | `PRODUCT` + design docs | `design/pages/login.md` §۶ و `design/system/component-states.md`؛ live Login برای این milestone ارائه نشده است |
| responsive و light/dark | screenshot + page doc | چهار تصویر Login و `design/pages/login.md` §۹ و §۱۰ |
| live Login | `PRODUCT` + `SCREENSHOT-SOURCE` | طبق تصمیم قطعی Login برای مرحلهٔ بعد است؛ live Login در این milestone validate یا implementation نمی‌شود |

## API، معماری و عدم implementation

| جزئیات | منبع | evidence |
| --- | --- | --- |
| internal API و عدم اتصال مستقیم frontend | `PRODUCT` + docs | `AGENTS.md`، `docs/api/api-overview.md`، `docs/architecture/frontend.md` |
| Django REST Framework، PostgreSQL، Python 3.14، uv | `PRODUCT` + docs | `README.md` و `docs/architecture/backend.md`؛ compatibility فقط به‌عنوان preflight آینده ثبت شده |
| Redis/queue/Kafka/data lake | `PRODUCT` + ADR + Compose | pipeline docs و ADR 0002/0003؛ Redis فقط profile `cache`؛ Kafka و data lake runtime ندارند |
| raw/normalized، retention حداکثر یک هفته و cleanup | `PRODUCT` + pipeline doc | `docs/architecture/weather-data-pipeline.md` §raw، §retention و cleanup policy |
| retry، backoff، checkpoint، heartbeat و no-concurrent-run | `PRODUCT` + ADR | pipeline doc و ADR 0002؛ فقط requirement آینده، بدون worker/queue اجرایی |
| implementation محلی | filesystem + tests | `apps/web`، `apps/api`، `infra/compose`، seed دمو و تست‌های Vitest/pytest؛ ادعای «فقط `.gitkeep`» منسوخ است |

## evidenceهای مسدود

| موضوع | وضعیت | دلیل |
| --- | --- | --- |
| source محلی | BLOCKED | `/workspace/sites/hawatch-weather` وجود ندارد؛ طبق تصمیم کاربر reference unavailable است و validation را متوقف نمی‌کند؛ OQ-001 |
| referenceهای قدیمی probe/result | BLOCKED | مسیرهای manifest در `/workspace/scratch/...` موجود نیستند؛ OQ-002 |
| canonical tokenها | PASS | `design/tokens/visual-tokens.json` تنها منبع مقدارهاست؛ markdownها توضیح‌دهنده‌اند؛ OQ-004 resolved |
| loading/error/stale و empty/error | PASS | contract قطعی کاربر ثبت شد؛ عدم مشاهدهٔ branch در live با پیاده‌سازی موجود اشتباه نمی‌شود |
| تغییرات خارج از scope | PASS | baseline اولیه با پیام مشخص ساخته شد و working tree نهایی clean کنترل شد؛ OQ-015 resolved |

## قاعدهٔ استفاده

هر مقدار دارای `[PRODUCT]` یا future docs، رفتار فعلی سایت live محسوب نمی‌شود مگر با evidence جدا. source محلی unavailable به‌صورت non-gating ثبت شده است. implementation محلی فعلی از API داخلی و دادهٔ دمو استفاده می‌کند؛ Login و ingestion واقعی همچنان خارج از scope هستند.
