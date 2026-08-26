# قرارداد آیندهٔ forecast

این قرارداد برای طراحی backend و UI ثبت شده است و implementation نیست.

## envelope پیشنهادی

```text
forecast
├── destination
├── current
├── daily[]
├── hourly[]
├── alerts[]
├── freshness
└── metadata
```

## destination

شامل `slug`، نام نمایشی، latitude، longitude، elevation، timezone و منبع تأیید مختصات است.

## current و hourly

هر reading باید در صورت وجود condition، temperature، apparent temperature، wind speed/direction، gust، visibility، precipitation، cloud cover، UV و valid time داشته باشد. واحد هر مقدار در contract ثبت شود؛ تبدیل display در لایهٔ مناسب انجام گیرد.

## alerts

هر alert شامل `severity` (`normal`، `change`، `critical`)، title، description، valid window، affected destination/points و action guidance است. رنگ semantic از severity مشتق می‌شود، نه برعکس.

## freshness و metadata موردنیاز

- provider
- coordinates
- elevation
- fetched_at
- valid_from
- valid_to
- model
- request_id
- ingestion_run_id
- schema_version
- content_hash
- status
- error information

## freshness rules

UI باید تفاوت `ready`، `stale` و `partial-data` را از روی contract تشخیص دهد. threshold دقیق stale، tolerance clock skew و fallback provider هنوز تصمیم باز است.

