from __future__ import annotations

from datetime import timedelta

from django.contrib import admin
from django.db.models import Count, Sum
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseForbidden
from django.template.response import TemplateResponse
from django.urls import path
from django.utils import timezone

from hawatch.modules.forecasts.models import WeatherPoint
from hawatch.modules.routes.models import Route

from .models import MonthlyPageViewAggregate, PageViewEvent


RANGES = {
    "today": "امروز",
    "7d": "۷ روز اخیر",
    "30d": "۳۰ روز اخیر",
    "all": "کل زمان",
}


@admin.register(PageViewEvent)
class PageViewEventAdmin(admin.ModelAdmin):
    change_list_template = "admin/analytics/pageviewevent/change_list.html"
    list_display = ("page_type", "page_slug", "occurred_at")
    list_filter = ("page_type", "occurred_at")
    date_hierarchy = "occurred_at"
    ordering = ("-occurred_at",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return bool(request.user.is_active and request.user.is_superuser)

    def has_delete_permission(self, request, obj=None):
        return False

    def has_module_permission(self, request):
        return bool(request.user.is_active and request.user.is_superuser)

    def has_view_permission(self, request, obj=None):
        return bool(request.user.is_active and request.user.is_superuser)

    def get_readonly_fields(self, request, obj=None):
        return tuple(field.name for field in self.model._meta.fields)

    def save_model(self, request, obj, form, change):
        raise PermissionDenied("رویدادهای analytics فقط خواندنی هستند.")

    def get_urls(self):
        custom_urls = [
            path(
                "overview/",
                self.admin_site.admin_view(self._superuser_only(self.overview_view)),
                name="analytics_pageviewevent_overview",
            )
        ]
        return custom_urls + super().get_urls()

    @staticmethod
    def _superuser_only(view):
        def wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated or not request.user.is_superuser:
                return HttpResponseForbidden("دسترسی فقط برای superuser مجاز است.")
            return view(request, *args, **kwargs)

        return wrapped

    @staticmethod
    def _private(response):
        response["Cache-Control"] = "private, no-store"
        response["Pragma"] = "no-cache"
        return response

    def changelist_view(self, request, extra_context=None):
        return self._private(super().changelist_view(request, extra_context=extra_context))

    def change_view(self, request, object_id, form_url="", extra_context=None):
        return self._private(super().change_view(request, object_id, form_url, extra_context))

    def history_view(self, request, object_id, extra_context=None):
        return self._private(super().history_view(request, object_id, extra_context))

    @staticmethod
    def _starts(now):
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return {
            "today": today,
            "7d": today - timedelta(days=6),
            "30d": today - timedelta(days=29),
            "all": None,
        }

    @staticmethod
    def _filtered_events(page_type, start):
        events = PageViewEvent.objects.all()
        if page_type in {PageViewEvent.PageType.POINT, PageViewEvent.PageType.ROUTE}:
            events = events.filter(page_type=page_type)
        if start is not None:
            events = events.filter(occurred_at__gte=start)
        return events

    def overview_view(self, request):
        page_type = request.GET.get("type", "all")
        if page_type not in {"all", PageViewEvent.PageType.POINT, PageViewEvent.PageType.ROUTE}:
            page_type = "all"
        selected_range = request.GET.get("range", "30d")
        if selected_range not in RANGES:
            selected_range = "30d"
        metric = request.GET.get("metric", "page_views")
        if metric not in {"page_views", "unique_visitors"}:
            metric = "page_views"
        order = request.GET.get("order", "desc")
        if order not in {"asc", "desc"}:
            order = "desc"

        point_qs = WeatherPoint.objects.filter(is_active=True).only("slug", "name", "page_name")
        route_qs = Route.objects.filter(is_active=True).only("slug", "title")
        pages = []
        if page_type in {"all", PageViewEvent.PageType.POINT}:
            pages.extend(
                {"page_type": PageViewEvent.PageType.POINT, "slug": p.slug, "name": p.page_name or p.name}
                for p in point_qs.order_by("page_name", "slug")
            )
        if page_type in {"all", PageViewEvent.PageType.ROUTE}:
            pages.extend(
                {"page_type": PageViewEvent.PageType.ROUTE, "slug": r.slug, "name": r.title}
                for r in route_qs.order_by("title", "slug")
            )

        now = timezone.localtime()
        starts = self._starts(now)
        metrics = {}
        summaries = {}
        for key, start in starts.items():
            queryset = self._filtered_events(page_type, start)
            grouped = queryset.values("page_type", "page_slug").annotate(
                page_views=Count("id"),
                unique_visitors=Count("visitor_hash", distinct=True),
            )
            metrics[key] = {(item["page_type"], item["page_slug"]): item for item in grouped}
            summaries[key] = queryset.aggregate(
                page_views=Count("id"),
                unique_visitors=Count("visitor_hash", distinct=True),
            )

        # Raw events older than 30 days are represented by monthly counters.
        # They belong in the all-time view only; the rolling windows contain
        # raw events by definition. Summing monthly distinct counts is clearly
        # marked approximate in the template.
        historical = MonthlyPageViewAggregate.objects.all()
        if page_type in {PageViewEvent.PageType.POINT, PageViewEvent.PageType.ROUTE}:
            historical = historical.filter(page_type=page_type)
        historical_groups = historical.values("page_type", "page_slug").annotate(
            page_views=Sum("page_views"), unique_visitors=Sum("unique_visitors")
        )
        for item in historical_groups:
            key = (item["page_type"], item["page_slug"])
            bucket = metrics["all"].setdefault(key, {"page_views": 0, "unique_visitors": 0})
            bucket["page_views"] += int(item["page_views"] or 0)
            bucket["unique_visitors"] += int(item["unique_visitors"] or 0)
        historical_summary = historical.aggregate(
            page_views=Sum("page_views"), unique_visitors=Sum("unique_visitors")
        )
        summaries["all"]["page_views"] += int(historical_summary["page_views"] or 0)
        summaries["all"]["unique_visitors"] += int(historical_summary["unique_visitors"] or 0)

        selected_metrics = metrics[selected_range]
        rows = []
        for page in pages:
            values = selected_metrics.get((page["page_type"], page["slug"]), {})
            row = {
                **page,
                "page_type_label": "نقطه" if page["page_type"] == PageViewEvent.PageType.POINT else "مسیر",
                "page_views": values.get("page_views", 0),
                "unique_visitors": values.get("unique_visitors", 0),
            }
            for key in RANGES:
                item = metrics[key].get((page["page_type"], page["slug"]), {})
                row[f"{key}_page_views"] = item.get("page_views", 0)
                row[f"{key}_unique_visitors"] = item.get("unique_visitors", 0)
            rows.append(row)
        rows.sort(key=lambda row: (row[metric], row["name"].casefold()), reverse=order == "desc")

        context = {
            **self.admin_site.each_context(request),
            "title": "گزارش بازدید صفحات",
            "rows": rows,
            "summaries": summaries,
            "summary_rows": [
                {
                    "key": key,
                    "label": label,
                    "page_views": summaries[key]["page_views"] or 0,
                    "unique_visitors": summaries[key]["unique_visitors"] or 0,
                }
                for key, label in RANGES.items()
            ],
            "ranges": RANGES,
            "selected_range_label": RANGES[selected_range],
            "selected_type": page_type,
            "selected_range": selected_range,
            "selected_metric": metric,
            "selected_order": order,
            "has_historical_aggregates": MonthlyPageViewAggregate.objects.exists(),
        }
        return self._private(TemplateResponse(request, "admin/analytics/pageviewevent/overview.html", context))
