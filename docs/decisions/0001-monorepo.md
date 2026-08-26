# ADR 0001: monorepo برای محصول هواچ

- وضعیت: پذیرفته‌شده
- تاریخ: 2026-08-25

## زمینه

هواچ هم‌زمان design handoff، تصاویر، مستندات، frontend آینده و backend آینده دارد. جدا کردن UI/UX از code در شروع می‌تواند باعث drift بین screenshot و implementation شود.

## تصمیم

یک repository با نام `hawatch-product` و ساختار monorepo استفاده می‌کنیم. design، docs، `apps/web`، `apps/api`، `infra` و `scripts` کنار هم version می‌شوند. در این مرحله appها فقط placeholder هستند.

## پیامدها

- مرجع بصری و implementation آینده در یک history قرار می‌گیرند.
- تغییرهای design و acceptance criteria قابل trace هستند.
- ownership و release boundary آینده باید جداگانه تعریف شود.
- repository فعلی Sites دست‌نخورده می‌ماند.

