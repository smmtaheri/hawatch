from __future__ import annotations

from datetime import timedelta

from django.contrib import admin
from django.db.models import Count
from django.template.response import TemplateResponse
from django.urls import path
from django.utils import timezone

from hawatch.modules.forecasts.models import WeatherPoint
from hawatch.modules.routes.models import Route

from .models import PageViewEvent


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
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_urls(self):
        custom_urls = [
            path(
                "overview/",
                self.admin_site.admin_view(self.overview_view),
                name="analytics_pageviewevent_overview",
            )
        ]
        return custom_urls + super().get_urls()

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
        }
        return TemplateResponse(request, "admin/analytics/pageviewevent/overview.html", context)
