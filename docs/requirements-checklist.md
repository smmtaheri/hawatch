# checklist الزامات validation

تاریخ به‌روزرسانی: 2026-08-26

این checklist الزامات handoff اولیه را نگه می‌دارد و وضعیت را با implementation محلی فعلی هم‌تراز می‌کند.

| # | الزام | وضعیت | evidence |
| --- | --- | --- | --- |
| 1 | دقیقاً ۱۶ تصویر asset | PASS | `design/manifest.json` و `design/screens` |
| 2 | source screenshots بدون تغییر | PASS | PNGها دست‌نخورده؛ بدون resize/re-encode |
| 3 | مسیر page/theme/device | PASS | `design/screens/{page}/{theme}/{device}.png` |
| 4 | manifest match | PASS | نام، ابعاد و SHA-256 |
| 5 | duplicate/missing/misnamed | PASS | فقط pairهای عمدی source/organized |
| 6 | DOCX و design system | PASS | `references/Hawatch.docx` + `visual-tokens.json` |
| 7 | مستندات صفحات | PASS | `design/pages/*` و live inspection |
| 8 | layout/interaction/state docs | PASS | page specs + live inspection |
| 9 | light/dark و mobile/desktop | PASS | ۱۲ ترکیب مرجع + پیاده‌سازی محلی |
| 10 | flowهای navigation | PASS | `docs/user-flows/*` و React Router |
| 11 | API contract + API اجرایی | PASS | `docs/api/*` و `apps/api` endpointها |
| 12 | Django/DRF/PostGIS/Python 3.14/uv | PASS | `apps/api/pyproject.toml` و Compose |
| 13 | Redis/Kafka/ingestion scope | PASS | Redis فقط profile `cache`؛ Kafka/ingestion خارج از scope |
| 14 | retention/retry/checkpoint docs | PASS | `docs/architecture/weather-data-pipeline.md` |
| 15 | implementation محلی | PASS | `apps/web`، `apps/api`، `infra/compose` اجرایی‌اند (ادعای «فقط `.gitkeep`» منسوخ است) |
| 16 | Login و design assets دست‌نخورده | PASS | Login فقط reference؛ screenshots تغییر نکرده‌اند |

## جمع وضعیت‌ها

- PASS: `16`
- FAIL: `0`
- BLOCKED (non-gating): source محلی `/workspace/sites/hawatch-weather`
- خارج از scope عمدی: Login، live weather provider، Kafka، Kubernetes manifests

## تست و اجرای محلی

- `pnpm test` و `pnpm build`
- `docker compose --env-file .env -f infra/compose/compose.yaml exec api pytest`
- `makemigrations --check --dry-run`
- health live/ready، destinations، forecast مقصد و مسیر

جزئیات اجرا: `docs/local-development.md` و `README.md`.
