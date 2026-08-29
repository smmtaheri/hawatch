from __future__ import annotations

import re
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

TEHRAN = ZoneInfo("Asia/Tehran")
PERSIAN_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
ASCII_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
JALALI_MONTHS = [
    "فروردین",
    "اردیبهشت",
    "خرداد",
    "تیر",
    "مرداد",
    "شهریور",
    "مهر",
    "آبان",
    "آذر",
    "دی",
    "بهمن",
    "اسفند",
]
WEEKDAYS = ["دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه", "شنبه", "یکشنبه"]

FORECAST_DAY_COUNT = 7  # yesterday + today + 5 following days
HOURLY_STEP = 2
# Planner gauge / start_time granularity (minutes). Change here for 30- or 5-minute steps later.
PLANNER_TIME_STEP_MINUTES = 60
MORNING_HOURS = (3, 5, 7, 9)
AFTERNOON_HOURS = (11, 13, 15, 17)
NIGHT_HOURS = (19, 21, 23, 1)
ALL_HOURS = MORNING_HOURS + AFTERNOON_HOURS + NIGHT_HOURS

SPEED_MULTIPLIERS = {"آرام": 1.2, "متوسط": 1.0, "سریع": 0.82}
SPEED_ALIASES = {
    "slow": "آرام",
    "medium": "متوسط",
    "fast": "سریع",
    "آرام": "آرام",
    "متوسط": "متوسط",
    "سریع": "سریع",
}

PERIOD_IDS = ("morning", "afternoon", "night")

PERIODS = {
    "morning": {
        "id": "morning",
        "label": "صبح",
        "range_label": "۰۳ تا ۱۱",
        "start_minutes": 180,
        "end_minutes": 660,
        "default_start": 360,
        "hours": MORNING_HOURS,
        "headline": "تغییرات صبح · هر دو ساعت",
    },
    "afternoon": {
        "id": "afternoon",
        "label": "بعدازظهر",
        "range_label": "۱۱ تا ۱۹",
        "start_minutes": 660,
        "end_minutes": 1140,
        "default_start": 720,
        "hours": AFTERNOON_HOURS,
        "headline": "تغییرات بعدازظهر · هر دو ساعت",
    },
    "night": {
        "id": "night",
        "label": "شب",
        "range_label": "۱۹ تا ۰۳",
        "start_minutes": 1140,
        # Exclusive end at 03:00 (1620) so last selectable planner start is 02:00 (1560).
        "end_minutes": 1620,
        "default_start": 1200,
        "hours": NIGHT_HOURS,
        "headline": "تغییرات شب · هر دو ساعت",
    },
}


def timezone() -> ZoneInfo:
    """Return Hawatch's product timezone, independent of browser/server locale."""
    return TEHRAN


def now_tehran(at: datetime | None = None) -> datetime:
    if at is None:
        return datetime.now(tz=timezone())
    if at.tzinfo is None:
        return at.replace(tzinfo=timezone())
    return at.astimezone(timezone())


def to_fa_digits(value) -> str:
    return str(value).translate(PERSIAN_DIGITS)


def gregorian_to_jalali(gy: int, gm: int, gd: int) -> tuple[int, int, int]:
    g_d_m = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    gy2 = gy + 1 if gm > 2 else gy
    days = (
        355666
        + (365 * gy)
        + ((gy2 + 3) // 4)
        - ((gy2 + 99) // 100)
        + ((gy2 + 399) // 400)
        + gd
        + g_d_m[gm - 1]
    )
    jy = -1595 + (33 * (days // 12053))
    days %= 12053
    jy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        jy += (days - 1) // 365
        days = (days - 1) % 365
    if days < 186:
        jm = 1 + days // 31
        jd = 1 + (days % 31)
    else:
        jm = 7 + (days - 186) // 30
        jd = 1 + ((days - 186) % 30)
    return jy, jm, jd


def jalali_parts(value: date) -> tuple[int, int, int]:
    return gregorian_to_jalali(value.year, value.month, value.day)


def jalali_month_day(value: date) -> str:
    _, month, day = jalali_parts(value)
    return f"{to_fa_digits(day)} {JALALI_MONTHS[month - 1]}"


def format_hhmm(minutes: int) -> str:
    minutes = minutes % 1440
    hour, minute = divmod(minutes, 60)
    return format_clock(hour, minute)


def format_clock(hour: int, minute: int = 0) -> str:
    return f"{to_fa_digits(hour).rjust(2, '۰')}:{to_fa_digits(minute).rjust(2, '۰')}"


def format_duration(minutes: int) -> str:
    hours, mins = divmod(minutes, 60)
    if mins:
        return f"{to_fa_digits(hours)} ساعت و {to_fa_digits(mins)} دقیقه"
    return f"{to_fa_digits(hours)} ساعت"


def hour_bucket(at: datetime | None = None) -> str:
    local = now_tehran(at)
    return local.strftime("%Y-%m-%dT%H")


def day_window(today: date | None = None) -> list[date]:
    current = today or now_tehran().date()
    start = current - timedelta(days=1)
    return [start + timedelta(days=offset) for offset in range(FORECAST_DAY_COUNT)]


def day_payload(value: date, today: date) -> dict:
    offset = (value - today).days
    if offset == -1:
        label = "دیروز"
    elif offset == 0:
        label = "امروز"
    elif offset == 1:
        label = "فردا"
    else:
        label = WEEKDAYS[value.weekday()]
    return {
        "date": value.isoformat(),
        "label": label,
        "jalali": jalali_month_day(value),
        "offset": offset,
        "is_yesterday": offset == -1,
        "is_today": offset == 0,
        "is_past": offset < 0,
        "is_future": offset > 0,
        "is_current": offset == 0,
    }


def localize_dt(value: date, hour: int, minute: int = 0) -> datetime:
    return datetime.combine(value, time(hour=hour, minute=minute), tzinfo=timezone())


def period_window(selected_date: date, period: str) -> tuple[datetime, datetime]:
    """Timezone-aware [start, end) window for the selected calendar date and period."""
    if period == "morning":
        return localize_dt(selected_date, 3), localize_dt(selected_date, 11)
    if period == "afternoon":
        return localize_dt(selected_date, 11), localize_dt(selected_date, 19)
    return localize_dt(selected_date, 19), localize_dt(selected_date + timedelta(days=1), 3)


def default_forecast_selection(at: datetime | None = None) -> tuple[date, str]:
    """Default date/period when the client does not specify them explicitly."""
    local = now_tehran(at)
    hour = local.hour
    today = local.date()
    if hour < 3:
        return today - timedelta(days=1), "night"
    if hour < 11:
        return today, "morning"
    if hour < 19:
        return today, "afternoon"
    return today, "night"


def parse_date(raw: str | None, today: date) -> date:
    if not raw:
        return today
    return date.fromisoformat(raw)


def parse_period(raw: str | None) -> str:
    if raw in PERIOD_IDS:
        return raw
    return "morning"


def parse_speed(raw: str | None) -> str:
    if not raw:
        return "متوسط"
    return SPEED_ALIASES.get(raw, "متوسط")


class StartTimeValidationError(ValueError):
    """Raised when a public start_time query value cannot be parsed."""


def _normalize_clock_digits(raw: str) -> str:
    return raw.strip().translate(ASCII_DIGITS)


def format_start_time_wire(minutes: int) -> str:
    """ASCII HH:MM for query parameters and share URLs."""
    clock = minutes % 1440
    hour, minute = divmod(clock, 60)
    return f"{hour:02d}:{minute:02d}"


def parse_start_time_value(raw: str) -> int:
    """Parse start_time query input to wall-clock minutes (0–1439).

    Accepts ASCII or Persian/Arabic digit clocks (HH:MM) and legacy bare minute integers.
    """
    cleaned = _normalize_clock_digits(raw)
    if not cleaned:
        raise StartTimeValidationError("مقدار start_time خالی است.")

    if ":" in cleaned:
        if cleaned.count(":") != 1:
            raise StartTimeValidationError("فرمت start_time نامعتبر است.")
        hours_str, minutes_str = cleaned.split(":", 1)
        if not re.fullmatch(r"\d{1,2}", hours_str) or not re.fullmatch(r"\d{2}", minutes_str):
            raise StartTimeValidationError("فرمت start_time نامعتبر است.")
        hours = int(hours_str)
        minutes = int(minutes_str)
        if hours > 23 or minutes > 59:
            raise StartTimeValidationError("ساعت یا دقیقهٔ start_time نامعتبر است.")
        return hours * 60 + minutes

    if cleaned.isdigit():
        return int(cleaned)

    raise StartTimeValidationError("فرمت start_time نامعتبر است.")


def period_last_start_minute(period: str) -> int:
    """Last valid planner start slot; period window ends are exclusive."""
    spec = PERIODS[period]
    step = PLANNER_TIME_STEP_MINUTES
    return spec["end_minutes"] - step


def planner_start_slots(period: str) -> list[int]:
    """Selectable start minutes for a period at PLANNER_TIME_STEP_MINUTES granularity."""
    spec = PERIODS[period]
    step = PLANNER_TIME_STEP_MINUTES
    last = period_last_start_minute(period)
    return list(range(spec["start_minutes"], last + 1, step))


def format_planner_tick(minutes: int) -> str:
    return format_hhmm(minutes)


def planner_period_payload(period: str) -> dict:
    """Period display + planner bounds/step for route gauge (single source of truth)."""
    spec = PERIODS[period]
    slots = planner_start_slots(period)
    return {
        **spec,
        "planner_step_minutes": PLANNER_TIME_STEP_MINUTES,
        "planner_start_minutes": spec["start_minutes"],
        "planner_end_minutes": spec["end_minutes"],
        "planner_last_start_minutes": period_last_start_minute(period),
        "planner_default_start_minutes": spec["default_start"],
        "planner_ticks": [format_planner_tick(slot) for slot in slots],
        "planner_slots": slots,
    }


def normalize_start_minutes(raw: str, period: str) -> int:
    """Floor to PLANNER_TIME_STEP_MINUTES and clamp inside the selected period window."""
    spec = PERIODS[period]
    step = PLANNER_TIME_STEP_MINUTES
    value = parse_start_time_value(raw)
    if period == "night" and value <= 180:
        value += 1440
    value = (value // step) * step
    last_start = period_last_start_minute(period)
    return max(spec["start_minutes"], min(last_start, value))


def resolve_planner_start_minutes(
    selected_date: date,
    period: str,
    *,
    local: datetime | None = None,
    raw_start: str | None = None,
) -> int:
    """Canonical route start: explicit clock, live floored time, or period default."""
    local = now_tehran(local)
    if raw_start is not None and raw_start != "":
        return normalize_start_minutes(raw_start, period)
    default_date, default_period = default_forecast_selection(local)
    if selected_date == default_date and period == default_period:
        return current_period_start_minutes(period, local)
    return PERIODS[period]["default_start"]


def parse_start_minutes(raw: str | None, period: str, default: int | None) -> int:
    spec = PERIODS[period]
    fallback = spec["default_start"] if default is None else default
    if raw is None or raw == "":
        last_start = period_last_start_minute(period)
        return max(spec["start_minutes"], min(last_start, fallback))
    return normalize_start_minutes(raw, period)


def current_period_start_minutes(period: str, at: datetime | None = None) -> int:
    """Floor current Tehran local time to PLANNER_TIME_STEP_MINUTES; never past last start."""
    local = now_tehran(at)
    spec = PERIODS[period]
    step = PLANNER_TIME_STEP_MINUTES
    now_minutes = local.hour * 60 + local.minute
    if period == "night" and now_minutes <= 180:
        now_minutes += 1440
    floored = (now_minutes // step) * step
    last_start = period_last_start_minute(period)
    return max(spec["start_minutes"], min(floored, last_start))


def datetime_flags(forecast_at: datetime, now: datetime | None = None) -> dict:
    """Past/current/future flags from actual forecast timestamps."""
    local_at = forecast_at.astimezone(timezone())
    local_now = now_tehran(now)
    today = local_now.date()
    value_date = local_at.date()
    bucket_at = local_at.replace(minute=0, second=0, microsecond=0)
    bucket_now = local_now.replace(minute=0, second=0, microsecond=0)
    is_past = bucket_at < bucket_now
    is_current = bucket_at == bucket_now
    is_future = bucket_at > bucket_now
    return {
        "is_yesterday": value_date == today - timedelta(days=1),
        "is_today": value_date == today,
        "is_past": is_past,
        "is_current": is_current,
        "is_future": is_future,
    }


def hour_flags(value: date, hour: int, today: date, current_hour: int) -> dict:
    """Legacy helper; prefer datetime_flags for period-aware rendering."""
    is_today = value == today
    is_yesterday = value == today - timedelta(days=1)
    is_past = value < today or (is_today and hour < current_hour)
    is_current = is_today and hour == current_hour
    is_future = value > today or (is_today and hour > current_hour)
    return {
        "is_yesterday": is_yesterday,
        "is_today": is_today,
        "is_past": is_past,
        "is_current": is_current,
        "is_future": is_future,
    }


def period_hour_slots(selected_date: date, period: str) -> list[tuple[date, int]]:
    """Calendar date + hour for each display card in the period."""
    slots: list[tuple[date, int]] = []
    for hour in PERIODS[period]["hours"]:
        if period == "night" and hour < 3:
            slots.append((selected_date + timedelta(days=1), hour))
        else:
            slots.append((selected_date, hour))
    return slots


def forecast_at_for_slot(selected_date: date, period: str, hour: int) -> datetime:
    if period == "night" and hour < 3:
        return localize_dt(selected_date + timedelta(days=1), hour)
    return localize_dt(selected_date, hour)


def arrival_forecast_at(selected_date: date, arrival_minutes: int) -> datetime:
    """Map extended start minutes (night after midnight) to a timezone-aware instant."""
    day_offset = arrival_minutes // 1440
    clock_minutes = arrival_minutes % 1440
    hour, minute = divmod(clock_minutes, 60)
    return localize_dt(selected_date + timedelta(days=day_offset), hour, minute)
