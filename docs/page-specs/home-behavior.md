# رفتار Home

## قرارداد تعامل

- `/` نقطهٔ ورود محصول است.
- autocomplete از `GET /api/v1/search/suggestions/?q=` با debounce ~۲۰۰ms و حداقل ۲ کاراکتر normalize‌شده؛
  جست‌وجو هم ابتدای عبارت و هم واژه‌های داخل نام/alias مقصد یا نقطه را پیدا می‌کند
  (مثلاً «گهر» → «دریاچهٔ گهر»). عنوان و slug مسیرها عمداً در جست‌وجو نیستند.
- stale responses نادیده گرفته می‌شوند (AbortController + request generation).
- Enter روی highlight → navigate؛ Enter بدون highlight همان جست‌وجوی unified را submit می‌کند.
- Arrow keys، Escape، focus management و combobox semantics.
- query باید trim و normalize شود و input پس از خطا حفظ بماند.
- نتیجهٔ مقصد: `/destination/{slug}`؛ نقطه: `/points/{weatherPointSlug}`.
- submit بدون highlight اگر یک نتیجه داشته باشد مستقیم navigate می‌کند و اگر چند نتیجه داشته باشد فهرست unified مقصد/نقطه را نشان می‌دهد؛ به endpoint قدیمی destination-only fallback نمی‌کند.
- شکست درخواست unified با پیام خطا و retry مشخص می‌شود و query باقی می‌ماند.
- theme toggle global است.

## mobile و overflow

combobox panel نباید hero را جابه‌جا کند یا overflow افقی بسازد. grid مقصدها با viewport سازگار باشد.

## observability آینده

eventهای احتمالی: `destination_search_submitted`، `search_suggestion_selected`، `popular_destination_selected`، `theme_changed`.
