# گزارش validation و بازبینی repository

تاریخ بررسی اولیه (handoff): ۱۴۰۵/۰۶/۰۴ برابر با 2026-08-26  
تاریخ به‌روزرسانی (implementation محلی): 2026-08-26

## دامنه و نتیجه

این سند ابتدا برای validation دست‌آورد design/handoff نوشته شد. پس از scaffold اجرایی، وضعیت فعلی repository به‌روزرسانی شده است.

وضعیت فعلی: **implementation محلی موجود و قابل اجرا است** (Home، Destination، Route + Django API + Compose). Login همچنان reference و خارج از scope است.

## وضعیت منابع

| منبع | وضعیت | evidence |
| --- | --- | --- |
| `references/Hawatch.docx` | PASS | خوانده شده؛ اصول بصری با `design/tokens/visual-tokens.json` هم‌راستا ثبت شده‌اند. |
| `/workspace/sites/hawatch-weather` | BLOCKED (non-gating) | مسیر در این محیط وجود ندارد؛ مانع اجرا نیست. |
| `design/source-screens/` / `design/screens/` | PASS | ۱۶ asset منطقی × organized copy؛ بدون resize/re-encode. |
| live reference URLs | PASS | قرارداد رفتار/بصری؛ دادهٔ محلی از API دمو می‌آید نه از live site. |
| `apps/web` + `apps/api` + `infra/compose` | PASS | نسخهٔ محلی اجرایی با pnpm workspace، Django/DRF/PostGIS و Compose. |

## وضعیت الزامات (نسبت به handoff قبلی)

| # | الزام handoff | وضعیت فعلی |
| --- | --- | --- |
| 1–10 | design assets، docs، flows، light/dark، mobile/desktop | همچنان PASS؛ دارایی‌های design دست‌نخورده‌اند. |
| 11 | API contract و پیاده‌سازی | **به‌روز شد:** قرارداد در `docs/api/*` و endpointهای `/api/v1/...` پیاده شده‌اند. |
| 12 | Django/DRF/PostgreSQL/Python 3.14/uv | **به‌روز شد:** `apps/api` با Django 5.2، DRF، psycopg، PostGIS و uv. |
| 13 | Redis/Kafka/ingestion | Redis فقط profile `cache`؛ Kafka و ingestion واقعی هنوز خارج از scope. |
| 14 | retention/retry/checkpoint docs | در pipeline doc و ports آینده ثبت شده؛ runtime ingestion ندارد. |
| 15 | نبود implementation | **منسوخ:** implementation محلی موجود است. |
| 16 | خارج از scope | Login و design assets تغییر نکرده‌اند. |

## implementation فعلی

- Frontend: `apps/web` — React + TypeScript + Vite + React Router؛ RTL و Vazirmatn؛ light/dark
- Backend: `apps/api` — Django REST؛ destinations/routes/forecast؛ demo seed idempotent `hawatch-demo-v1`
- Infra: `infra/compose/compose.yaml` — postgres (`postgis/postgis:16-3.5`)، api، web؛ Redis با `REDIS_PUBLISH_PORT`
- تست‌ها: Vitest برای صفحات؛ pytest برای health/seed/API/migrations/indexes

## محدودیت‌های شناخته‌شده

1. `/workspace/sites/hawatch-weather` unavailable است.
2. Login، Open-Meteo، Kafka، Kubernetes manifests و share server-side پیاده نشده‌اند.
3. دادهٔ هوا دمو است و نباید observation واقعی تلقی شود.
4. مقایسهٔ visual با screenshotهای مرجع نزدیک شده اما ادعاهای pixel-perfect فقط پس از capture و بازرسی واقعی معتبرند.
