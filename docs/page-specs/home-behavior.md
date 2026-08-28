# رفتار Home

## قرارداد تعامل

- `/` نقطهٔ ورود محصول است.
- autocomplete از `GET /api/v1/search/suggestions/?q=` با debounce ~۲۰۰ms و حداقل ۲ کاراکتر normalize‌شده.
- stale responses نادیده گرفته می‌شوند (AbortController + request generation).
- Enter روی highlight → navigate؛ Enter بدون highlight → submit fallback مقصدها.
- Arrow keys، Escape، focus management و combobox semantics.
- query باید trim و normalize شود و input پس از خطا حفظ بماند.
- نتیجهٔ مقصد: `/destination/{slug}`؛ نقطه: `/points/{weatherPointSlug}`.
- submit fallback همان لیست `/destinations/?query=` را refresh می‌کند.
- theme toggle global است.

## mobile و overflow

combobox panel نباید hero را جابه‌جا کند یا overflow افقی بسازد. grid مقصدها با viewport سازگار باشد.

## observability آینده

eventهای احتمالی: `destination_search_submitted`، `search_suggestion_selected`، `popular_destination_selected`، `theme_changed`.
