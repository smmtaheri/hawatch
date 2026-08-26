# معماری آیندهٔ frontend

## انتخاب اولیه

- React + TypeScript
- bundler پیشنهادی: Vite
- مدیریت route بر اساس pageهای Home، Destination، Route و Login reference
- font و layout از design tokens همین repository

این تصمیم به معنی ساخت app در این milestone نیست؛ `apps/web/` عمداً فقط placeholder دارد.

## مرزبندی

frontend فقط API داخلی هواچ را مصرف می‌کند. دسترسی مستقیم به provider، PostgreSQL، Redis یا raw response ممنوع است.

لایه‌های پیشنهادی آینده:

۱. page composition و routing.
۲. domain query/state برای destination، forecast و route plan.
۳. API client typed.
۴. presentation components مطابق design system.
۵. visual QA و responsive checks.

## state و cache

state انتخاب‌های کاربر شامل destination، date، period، start time، speed و theme باید از دادهٔ forecast جدا باشد. cache باید freshness را پنهان نکند و stale/partial را به UI منتقل کند.

## responsive و RTL

mobile و web دو composition مستقل اما هم‌هویت هستند. layout باید از ابتدا RTL باشد و برای جلوگیری از overflow در gridها `minmax(0, 1fr)` و containerهای محدود استفاده شود.

## milestone بعدی

اول یک vertical slice فقط برای Home یا Destination انتخاب شود، با fixture کنترل‌شده و مقایسهٔ screenshot. انتخاب libraryهای state، data fetching و component testing بعد از بررسی compatibility و نیاز واقعی انجام شود.

