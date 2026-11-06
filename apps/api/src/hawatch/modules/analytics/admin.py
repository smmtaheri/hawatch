from __future__ import annotations

import csv
import io
from django.contrib import admin
from django.conf import settings
from django.db import connection, transaction, OperationalError
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.template.response import TemplateResponse
from django.urls import path
from .models import PageViewEvent, VisitSession
from .attribution import SOURCES
from .reports import report_data


class PrivateAnalyticsAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return self.has_view_permission(request, obj)

    def has_module_permission(self, request):
        return self.has_view_permission(request)

    def has_view_permission(self, request, obj=None):
        return bool(request.user.is_active and request.user.is_superuser)

    def get_readonly_fields(self, request, obj=None):
        return tuple(f.name for f in self.model._meta.fields)

    def save_model(self, request, obj, form, change):
        raise PermissionDenied("آمار فقط خواندنی است.")

    @staticmethod
    def _private(response):
        response["Cache-Control"] = "private, no-store"
        response["Pragma"] = "no-cache"
        response["X-Robots-Tag"] = "noindex,nofollow"
        return response

    def changelist_view(self, request, extra_context=None):
        return self._private(
            super().changelist_view(request, extra_context=extra_context)
        )

    def change_view(self, request, object_id, form_url="", extra_context=None):
        return self._private(
            super().change_view(request, object_id, form_url, extra_context)
        )

    def history_view(self, request, object_id, extra_context=None):
        return self._private(super().history_view(request, object_id, extra_context))


@admin.register(PageViewEvent)
class PageViewEventAdmin(PrivateAnalyticsAdmin):
    change_list_template = "admin/analytics/pageviewevent/change_list.html"
    list_display = (
        "page_type",
        "page_slug",
        "occurred_at",
        "entry_source",
        "entry_path",
        "entry_campaign",
        "navigation_source",
        "previous_path",
    )
    list_filter = ("page_type", "navigation_source", "session__source", "occurred_at")
    search_fields = ("page_slug", "previous_path", "session__campaign")
    date_hierarchy = "occurred_at"
    ordering = ("-occurred_at",)
    list_select_related = ("session",)

    @admin.display(description="منبع ورود")
    def entry_source(self, obj):
        return (
            SOURCES.get(obj.session.source, obj.session.source)
            if obj.session
            else SOURCES["unknown"]
        )

    @admin.display(description="صفحهٔ ورود")
    def entry_path(self, obj):
        return obj.session.landing_path if obj.session else ""

    @admin.display(description="کمپین")
    def entry_campaign(self, obj):
        return obj.session.campaign if obj.session else ""

    def get_urls(self):
        return [
            path(
                "overview/",
                self.admin_site.admin_view(self.overview_view),
                name="analytics_pageviewevent_overview",
            )
        ] + super().get_urls()

    def overview_view(self, request):
        if not self.has_view_permission(request):
            return self._private(
                HttpResponseForbidden("دسترسی فقط برای superuser مجاز است.")
            )
        try:
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute("SHOW statement_timeout")
                    previous_timeout = cursor.fetchone()[0]
                    cursor.execute(
                        "SELECT set_config('statement_timeout', %s, true)",
                        [str(settings.ANALYTICS_REPORT_TIMEOUT_MS) + "ms"],
                    )
                context = report_data(request.GET)
                # Restore explicitly, including when another caller owns an outer transaction.
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT set_config('statement_timeout', %s, true)",
                        [previous_timeout],
                    )
        except OperationalError:
            return self._private(
                HttpResponse(
                    "گزارش در زمان مجاز آماده نشد؛ بازه یا فیلترها را محدود کنید.",
                    status=503,
                )
            )
        if request.GET.get("export") == "csv":
            if not context["summary"]:
                return self._private(
                    HttpResponseBadRequest("فیلتر یا بازه نامعتبر است.")
                )
            if context["export_too_large"]:
                return self._private(
                    HttpResponseBadRequest(
                        "خروجی بیش از ۱۰۰۰۰ ردیف است؛ بازه یا تفکیک را محدود کنید."
                    )
                )
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(
                ["گروه", "بازدید / ورود", "بازدیدکنندهٔ یکتا", "نوبت بازدید", "از", "تا"]
            )

            def safe(value):
                text = str(value)
                return (
                    "'" + text
                    if text.lstrip().startswith(("=", "+", "-", "@", "\t", "\r"))
                    else text
                )

            for row in [
                *context["rows"],
                *([context["legacy_row"]] if context["legacy_row"] else []),
            ]:
                writer.writerow(
                    [
                        safe(row["label"]),
                        row["page_views"],
                        row["unique_visitors"],
                        row["sessions"],
                        context["start"] or "",
                        context["end"],
                    ]
                )
            response = HttpResponse(
                "\ufeff" + output.getvalue(), content_type="text/csv; charset=utf-8"
            )
            response["Content-Disposition"] = (
                'attachment; filename="hawatch-analytics.csv"'
            )
            return self._private(response)
        context.update(
            self.admin_site.each_context(request), title="گزارش بازدید و منابع ورود"
        )
        return self._private(
            TemplateResponse(
                request, "admin/analytics/pageviewevent/overview.html", context
            )
        )


@admin.register(VisitSession)
class VisitSessionAdmin(PrivateAnalyticsAdmin):
    list_display = (
        "started_at",
        "source",
        "source_evidence",
        "landing_path",
        "campaign",
    )
    list_filter = ("source", "source_evidence", "started_at")
    search_fields = ("landing_path", "referrer_host", "campaign", "utm_source")
    ordering = ("-started_at",)
