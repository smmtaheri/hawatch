"""Public source and last-update labels for forecast payloads."""

from __future__ import annotations

from datetime import datetime

from hawatch.common.time import JALALI_MONTHS, format_clock, jalali_parts, now_tehran, to_fa_digits


def source_label(source: str, provider: str = "") -> str:
    """Return a display label without coupling the frontend to one provider."""

    normalized = str(source or provider or "").strip().lower()
    if normalized in {"open-meteo", "open-meteo-forecast"}:
        return "Open-Meteo"
    if normalized == "hawatch-demo":
        return "دادهٔ نمایشی"
    return normalized.replace("_", "-").replace("-", " ").title() or "دادهٔ هواشناسی"


def attribution_for_rows(rows) -> dict | None:
    """Describe only the records that contributed to the rendered forecast.

    For a route this deliberately uses the oldest contributing update: that is
    the conservative timestamp for a forecast assembled from several points.
    """

    rows = list(rows)
    if not rows:
        return None
    updated_at = min(row.generated_at for row in rows)
    sources = sorted({source_label(row.source, row.provider) for row in rows if row.source or row.provider})
    return attribution_payload(" · ".join(sources), updated_at)


def attribution_payload(source: str, updated_at: datetime | None) -> dict | None:
    if updated_at is None:
        return None
    local = now_tehran(updated_at)
    year, month, day = jalali_parts(local.date())
    label = (
        f"{to_fa_digits(day)} {JALALI_MONTHS[month - 1]} "
        f"{to_fa_digits(year)}، {format_clock(local.hour, local.minute)}"
    )
    return {
        "source": source or "دادهٔ هواشناسی",
        "updated_at": local.isoformat(),
        "updated_label": label,
    }
