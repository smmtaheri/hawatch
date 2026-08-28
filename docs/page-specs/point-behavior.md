# رفتار صفحهٔ Point (Standalone)

مرجع بصری: [design/pages/point.md](../../design/pages/point.md) — extension از Destination؛ screenshot مرجع جدا ندارد.

## ورود

- Home autocomplete → `/points/{slug}`
- Route timeline/card → `/points/{slug}` + `state.fromRoute` شامل `pathname`، `search` و `href` مسیر
- URL مستقیم / share / refresh
- Legacy `/routes/{route}/points/{point}` → redirect به canonical

## API

`GET /api/v1/points/{weather_point_slug}/forecast/?date=&period=`

پاسخ شامل: slug/name/aliases، مختصات/ارتفاع/status/provenance، forecast metadata، current/hourly/days/period، related destinations/routes (dedup)، بدون timing مسیر.

## هویت و ظاهر

- Point باید از همان shell، card surface، typography، period control و day selector صفحهٔ Destination استفاده کند.
- صفحهٔ Point screenshot مستقل ندارد؛ ۱۶ تصویر مرجع موجود immutable هستند و Destination baseline بصری است.
- Related routes در sidebar به‌صورت compact single-column نمایش داده می‌شوند؛ grid سه‌ستونهٔ generic مجاز نیست.
- label بالای روزها «انتخاب روز» است و heading/description تکراری forecast نمایش داده نمی‌شود.

## breadcrumb

همیشه: `مقصدها / {نام نقطه}`

## back CTA

| منبع ورود | رفتار |
| --- | --- |
| Route (با state) | `بازگشت به مسیر {title}` → همان مسیر با `date`، `period`، `start_time` و `speed` قبلی |
| Home / direct / refresh | بدون back مسیر؛ optional «مسیرهای مرتبط» |

## controls

- day tabs و period toggle مانند Destination
- **بدون** speed، start-time gauge، ETA، ascent، planner controls

## states

| state | UX |
| --- | --- |
| loading | skeleton/spinner در shell |
| ready | hero + forecast کامل |
| empty | پیام «پیش‌بینی در دسترس نیست» |
| partial | «پیش‌بینی ناقص» |
| error | retry |
| stale | StaleDataNotice |

هیچ timestamp خام یا عبارت داخلی `timing_pending` در متن کاربر نمایش داده نمی‌شود.

## theme / responsive

- `point-page` در dark/light
- mobile: layout تک‌ستونه؛ desktop مستقیم: main + مسیرهای مرتبط؛ desktop با ورود از Route: تک‌ستونه و بدون sidebar خالی
- max-width و padding هم‌تراز Destination

## acceptance

- canonical URL بدون planner noise
- keyboard/back/accessibility برای CTA
- shared point dedup
- اگر point از نوع destination باشد، navigation به destination canonical انجام می‌شود.
- theme و رنگ تمام cardها، از جمله related routes، با Destination یکسان است.
- no horizontal overflow
- بازگشت از Route تمام context برنامه‌ریزی را حفظ می‌کند
