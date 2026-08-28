# ADR 0001: monorepo برای محصول هواچ

- وضعیت: پذیرفته‌شده
- تاریخ: 2026-08-25

## زمینه

هواچ هم‌زمان design handoff، تصاویر، مستندات، frontend و backend اجرایی دارد. جدا کردن UI/UX از code می‌تواند باعث drift بین screenshot و implementation شود.

## تصمیم

یک repository با نام `hawatch` و ساختار monorepo استفاده می‌کنیم. design، docs، `apps/web`، `apps/api`، `infra` و `scripts` کنار هم version می‌شوند. در وضعیت فعلی، `apps/web` و `apps/api` implementation قابل‌اجرا دارند و Login همچنان فقط reference طراحی است.

## پیامدها

- مرجع بصری و implementation فعلی/آینده در یک history قرار می‌گیرند.
- تغییرهای design و acceptance criteria قابل trace هستند.
- ownership و release boundary آینده باید جداگانه تعریف شود.
- repository فعلی Sites دست‌نخورده می‌ماند.
