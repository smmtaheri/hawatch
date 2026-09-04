# ADR 0002: گزینه‌های pipeline دادهٔ هوا

- وضعیت: باز برای تصمیم نهایی
- تاریخ: 2026-08-25

## زمینه

هواچ به forecast نقطه و forecast زمان‌مند نقاط مسیر نیاز دارد. داده باید تازه، قابل ردیابی، قابل normalize و قابل حذف طبق retention باشد.

## گزینه‌ها

### Celery + Redis

مزایا: اکوسیستم رایج، retry و scheduling آشنا. معایب: operational surface و وابستگی به Redis؛ semantics هماهنگی و idempotency باید صریح طراحی شود.

### job runner ساده

مزایا: کمترین پیچیدگی برای حجم اولیه و مناسب یک pipeline محدود. معایب: retry، lock، observability و رشد هم‌زمانی باید خودمان بسازیم.

### Kafka

مزایا: event log و throughput رشدپذیر. معایب: برای نیاز فعلی سنگین، operational cost بالا و هنوز نیازمند sink/retention جدا.

### data lake

مزایا: مناسب آرشیو و تحلیل حجیم. معایب: برای محصول forecast با retention یک‌هفته‌ای premature و خارج از نیاز فعلی.

## تصمیم موقت

هیچ گزینه‌ای نهایی نشده است. تا روشن‌شدن volume، cadence، SLA، نیاز replay و تیم عملیات، pipeline باید با abstraction و contract مستند طراحی شود؛ نه با افزودن infrastructure در این milestone.

## معیار انتخاب بعدی

idempotency، retry/backoff، atomic checkpoint، heartbeat، جلوگیری از concurrent run، مشاهده‌پذیری، هزینهٔ نگهداری، compatibility با Django/Python 3.14 و امکان حفظ raw metadata.

