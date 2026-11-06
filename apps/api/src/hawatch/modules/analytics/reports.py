"""Private, bounded report queries, using one immutable cutoff per request."""

from __future__ import annotations

from datetime import timedelta
from zoneinfo import ZoneInfo

from django import forms
from django.core.paginator import Paginator
from django.db.models import Count, Sum, Value, CharField
from django.db.models.functions import Coalesce, TruncDay, TruncHour
from django.utils import timezone

from .attribution import SOURCES, NAVIGATIONS
from .models import (
    AnalyticsCoverage,
    MonthlyPageViewAggregate,
    PageViewEvent,
    VisitSession,
)
from hawatch.modules.forecasts.models import WeatherPoint
from hawatch.modules.routes.models import Route

TEHRAN = ZoneInfo("Asia/Tehran")
RANGES = {
    "24h": "۲۴ ساعت اخیر",
    "7d": "۷ روز اخیر",
    "30d": "۳۰ روز اخیر",
    "days": "N روز اخیر",
    "custom": "بازهٔ دلخواه",
    "all": "کل زمان",
}
GROUPS = {
    "page": "صفحه",
    "source": "منبع ورود",
    "navigation": "نحوهٔ رسیدن",
    "previous": "صفحهٔ قبلی",
    "landing": "صفحهٔ ورود",
    "campaign": "کمپین",
    "referrer": "دامنهٔ ارجاع",
    "time": "زمان",
}


class ReportForm(forms.Form):
    scope = forms.ChoiceField(
        label="گزارش",
        choices=[("views", "بازدید نقاط و مسیرها"), ("entries", "ورود به کل سایت")],
        initial="views",
        required=False,
    )
    type = forms.ChoiceField(
        label="نوع صفحه",
        choices=[("all", "همه"), ("point", "نقطه"), ("route", "مسیر")],
        initial="all",
        required=False,
    )
    range = forms.ChoiceField(
        label="بازه", choices=list(RANGES.items()), initial="24h", required=False
    )
    days = forms.IntegerField(
        label="تعداد روز", min_value=1, max_value=36500, required=False, initial=7
    )
    start = forms.DateTimeField(
        label="از (ساعت تهران)",
        required=False,
        widget=forms.DateTimeInput(
            attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"
        ),
    )
    end = forms.DateTimeField(
        label="تا (ساعت تهران)",
        required=False,
        widget=forms.DateTimeInput(
            attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"
        ),
    )
    until = forms.DateTimeField(required=False, widget=forms.HiddenInput)
    source = forms.ChoiceField(
        label="منبع ورود", required=False, choices=[("", "همه")] + list(SOURCES.items())
    )
    navigation = forms.ChoiceField(
        label="نحوهٔ رسیدن",
        required=False,
        choices=[("", "همه")] + list(NAVIGATIONS.items()),
    )
    campaign = forms.CharField(label="کمپین", max_length=100, required=False)
    previous = forms.CharField(label="صفحهٔ قبلی", max_length=200, required=False)
    landing = forms.CharField(label="صفحهٔ ورود", max_length=200, required=False)
    referrer = forms.CharField(label="دامنهٔ ارجاع", max_length=200, required=False)
    page_slug = forms.SlugField(label="شناسهٔ صفحه", max_length=96, required=False)
    group = forms.ChoiceField(
        label="تفکیک بر اساس",
        required=False,
        choices=list(GROUPS.items()),
        initial="page",
    )
    metric = forms.ChoiceField(
        label="مرتب‌سازی",
        required=False,
        choices=[
            ("page_views", "تعداد بازدید / ورود"),
            ("unique_visitors", "بازدیدکنندهٔ یکتا"),
            ("sessions", "نوبت بازدید"),
        ],
        initial="page_views",
    )
    order = forms.ChoiceField(
        label="ترتیب",
        required=False,
        choices=[("desc", "نزولی"), ("asc", "صعودی")],
        initial="desc",
    )

    def clean(self):
        data = super().clean()
        for key, default in [
            ("scope", "views"),
            ("type", "all"),
            ("range", "24h"),
            ("group", "page"),
            ("metric", "page_views"),
            ("order", "desc"),
        ]:
            data[key] = data.get(key) or default
        if data["range"] == "days" and not data.get("days"):
            self.add_error("days", "تعداد روز را وارد کنید.")
        if data["range"] == "custom":
            if not data.get("start") or not data.get("end"):
                self.add_error("start", "شروع و پایان بازه لازم است.")
            elif data["start"] >= data["end"]:
                self.add_error("end", "پایان باید بعد از شروع باشد.")
        if data["scope"] == "entries" and (
            data.get("navigation")
            or data.get("previous")
            or data["group"] in {"navigation", "previous"}
        ):
            self.add_error(
                "scope", "نحوهٔ رسیدن و صفحهٔ قبلی برای گزارش بازدید صفحات است."
            )
        return data


def report_data(params):
    data = params.copy()
    if data.get("range") == "today":
        data["range"] = "24h"  # Existing daily bookmark now means rolling24h.
    for key, default in [
        ("scope", "views"),
        ("type", "all"),
        ("range", "24h"),
        ("group", "page"),
        ("metric", "page_views"),
        ("order", "desc"),
    ]:
        if not data.get(key):
            data[key] = default
    form = ReportForm(data)
    if not form.is_valid():
        return {"form": form, "rows": [], "summary": None, "ranges": RANGES}
    f = form.cleaned_data
    now = timezone.now()
    end = min(f.get("until") or now, now)
    if f["range"] == "custom":
        end = min(f["end"], now)
        start = f["start"]
    elif f["range"] == "all":
        start = None
    else:
        days = {"24h": 1, "7d": 7, "30d": 30}.get(f["range"], f.get("days") or 7)
        start = end - timedelta(days=days)
    # No future/client-controlled event timestamps can enlarge a report.
    if start and start >= end:
        form.add_error("start", "بازهٔ آینده یا خالی قابل گزارش نیست.")
        return {"form": form, "rows": [], "summary": None, "ranges": RANGES}
    is_entries = f["scope"] == "entries"
    qs = (
        VisitSession.objects.filter(started_at__lt=end)
        if is_entries
        else PageViewEvent.objects.filter(occurred_at__lt=end)
    )
    time_field = "started_at" if is_entries else "occurred_at"
    if start:
        qs = qs.filter(**{time_field + "__gte": start})
    prefix = "" if is_entries else "session__"
    if f["type"] != "all":
        qs = (
            qs.filter(
                landing_path__startswith="/points/"
                if f["type"] == "point"
                else "/routes/"
            )
            if is_entries
            else qs.filter(page_type=f["type"])
        )
    if f.get("source"):
        if not is_entries and f["source"] == "unknown":
            qs = qs.filter(session__isnull=True)
        else:
            qs = qs.filter(**{prefix + "source": f["source"]})
    for key, field in [
        ("campaign", "campaign"),
        ("landing", "landing_path"),
        ("referrer", "referrer_host"),
    ]:
        if f.get(key):
            qs = qs.filter(**{prefix + field: f[key]})
    if f.get("page_slug"):
        if is_entries:
            qs = qs.filter(
                landing_path__in=[
                    "/points/" + f["page_slug"],
                    "/routes/" + f["page_slug"],
                ]
            )
        else:
            qs = qs.filter(page_slug=f["page_slug"])
    if not is_entries:
        if f.get("navigation"):
            qs = qs.filter(navigation_source=f["navigation"])
        if f.get("previous"):
            qs = qs.filter(previous_path=f["previous"])
    aggregates = dict(
        page_views=Count("pk"),
        unique_visitors=Count("visitor_hash", distinct=True),
        sessions=Count("pk", distinct=True)
        if is_entries
        else Count("session_id", distinct=True),
    )
    summary = qs.aggregate(**aggregates)
    group = f["group"]
    if is_entries and group == "page":
        group = "landing"
    field = {
        "source": prefix + "source",
        "campaign": prefix + "campaign",
        "landing": prefix + "landing_path",
        "referrer": prefix + "referrer_host",
        "navigation": "navigation_source",
        "previous": "previous_path",
    }.get(group)
    if group == "page":
        grouped = qs.values("page_type", "page_slug").annotate(**aggregates)
    elif group == "time":
        trunc = TruncHour if start and end - start <= timedelta(days=1) else TruncDay
        grouped = (
            qs.annotate(bucket=trunc(time_field, tzinfo=TEHRAN))
            .values("bucket")
            .annotate(**aggregates)
        )
    else:
        grouped = (
            qs.annotate(
                bucket=Coalesce(field, Value("unknown"), output_field=CharField())
            )
            .values("bucket")
            .annotate(**aggregates)
        )

    # Old monthly totals have neither source dimensions nor arbitrary boundaries.
    # Only include them in unfiltered all-time view totals; never invent detail.
    coverage = AnalyticsCoverage.objects.first()
    legacy_eligible = (
        f["range"] == "all"
        and not is_entries
        and not any(
            f.get(k)
            for k in [
                "source",
                "navigation",
                "campaign",
                "previous",
                "landing",
                "referrer",
            ]
        )
    )
    legacy = MonthlyPageViewAggregate.objects.none()
    legacy_totals = {"page_views": 0, "unique_visitors": 0}
    if legacy_eligible:
        legacy = MonthlyPageViewAggregate.objects.all()
        if coverage and end < coverage.detailed_since:
            # A monthly bucket intersecting an old cutoff cannot be split exactly.
            legacy = legacy.filter(
                month_start__lt=timezone.localtime(end, TEHRAN).date().replace(day=1)
            )
        if f["type"] != "all":
            legacy = legacy.filter(page_type=f["type"])
        if f.get("page_slug"):
            legacy = legacy.filter(page_slug=f["page_slug"])
        legacy_totals = legacy.aggregate(
            page_views=Sum("page_views"), unique_visitors=Sum("unique_visitors")
        )
        for key in legacy_totals:
            legacy_totals[key] = legacy_totals[key] or 0
        for key in ["page_views", "unique_visitors"]:
            summary[key] += legacy_totals[key]
    query = data.copy()
    query["until"] = end.isoformat()
    query.pop("page", None)
    query.pop("export", None)

    def drill(key, value):
        p = query.copy()
        p[key] = value
        p["group"] = "page"
        return "?" + p.urlencode()

    def label(row):
        value = row.get("bucket", "")
        if group == "time":
            return timezone.localtime(value, TEHRAN).strftime("%Y-%m-%d %H:%M")
        if group == "source":
            return SOURCES.get(value, value or "نامشخص")
        if group == "navigation":
            return NAVIGATIONS.get(value, value or "نامشخص")
        return value or "نامشخص"

    direction = "-" if f["order"] == "desc" else ""
    exporting = params.get("export") == "csv"
    max_export = 10000
    if group == "page":
        names = {
            ("point", p["slug"]): p["page_name"] or p["name"]
            for p in WeatherPoint.objects.values("slug", "name", "page_name")
        }
        names.update(
            {
                ("route", r["slug"]): r["title"]
                for r in Route.objects.values("slug", "title")
            }
        )
        buckets = {(r["page_type"], r["page_slug"]): dict(r) for r in grouped}
        if legacy_eligible:
            for old in legacy.values("page_type", "page_slug").annotate(
                page_views=Sum("page_views"), unique_visitors=Sum("unique_visitors")
            ):
                key = (old["page_type"], old["page_slug"])
                b = buckets.setdefault(
                    key,
                    {
                        "page_type": key[0],
                        "page_slug": key[1],
                        "page_views": 0,
                        "unique_visitors": 0,
                        "sessions": 0,
                    },
                )
                for metric in ["page_views", "unique_visitors"]:
                    b[metric] += old[metric]
        # Keep zero-view pages in the default report without hiding archived events.
        if not any(
            f.get(k)
            for k in [
                "source",
                "navigation",
                "campaign",
                "previous",
                "landing",
                "referrer",
            ]
        ):
            for key in names:
                if (f["type"] == "all" or f["type"] == key[0]) and (
                    not f.get("page_slug") or f["page_slug"] == key[1]
                ):
                    buckets.setdefault(
                        key,
                        {
                            "page_type": key[0],
                            "page_slug": key[1],
                            "page_views": 0,
                            "unique_visitors": 0,
                            "sessions": 0,
                        },
                    )
        rows = [
            {
                **r,
                "label": names.get(key, key[1]),
                "detail_url": drill("page_slug", key[1]),
            }
            for key, r in buckets.items()
        ]
        rows.sort(
            key=lambda r: (r[f["metric"]], r["label"]), reverse=f["order"] == "desc"
        )
        paginator = Paginator(rows, 50)
        page = paginator.get_page(params.get("page"))
        selected = rows[: max_export + 1] if exporting else page.object_list
    else:
        grouped = grouped.order_by(direction + f["metric"], "bucket")
        paginator = Paginator(grouped, 50)
        page = paginator.get_page(params.get("page"))
        selected = grouped[: max_export + 1] if exporting else page.object_list
        key = {
            "source": "source",
            "campaign": "campaign",
            "landing": "landing",
            "previous": "previous",
            "navigation": "navigation",
            "referrer": "referrer",
        }.get(group)
        selected = [
            {
                **r,
                "label": label(r),
                "detail_url": drill(key, r["bucket"]) if key and r["bucket"] else "",
            }
            for r in selected
        ]
    if group != "page" and legacy_eligible and legacy_totals["page_views"]:
        # Shown separately on every page, not added to another named source bucket.
        legacy_row = dict(
            label="تاریخچهٔ ماهانه؛ تفکیک موجود نیست", sessions=0, **legacy_totals
        )
    else:
        legacy_row = None
    maximum = max((r["page_views"] for r in selected), default=1) or 1
    for row in selected:
        row["bar_pct"] = round(row["page_views"] / maximum * 100)
    return {
        "form": form,
        "rows": selected,
        "summary": summary,
        "start": start,
        "end": end,
        "query_string": query.urlencode(),
        "page_obj": page,
        "is_entries": is_entries,
        "group_label": GROUPS[group],
        "legacy_row": legacy_row,
        "has_historical_aggregates": MonthlyPageViewAggregate.objects.exists(),
        "legacy_included": bool(legacy_totals["page_views"]),
        "coverage": coverage,
        "partial_history": bool(
            coverage and (start is None or start < coverage.detailed_since)
        ),
        "ranges": RANGES,
        "export_too_large": exporting and len(selected) > max_export,
    }
