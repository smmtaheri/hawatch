from django.contrib import admin

from .models import AccountProfile, ForecastAccessPolicy, ForecastPlan, Membership


class SuperuserOnlyAdmin(admin.ModelAdmin):
    def has_module_permission(self, request):
        return bool(request.user.is_active and request.user.is_superuser)

    def has_view_permission(self, request, obj=None):
        return bool(request.user.is_active and request.user.is_superuser)

    def has_change_permission(self, request, obj=None):
        return bool(request.user.is_active and request.user.is_superuser)


@admin.register(ForecastAccessPolicy)
class ForecastAccessPolicyAdmin(SuperuserOnlyAdmin):
    list_display = ("display_day_count", "anonymous_visible_days_from_yesterday", "default_authenticated_plan")
    fields = ("display_day_count", "anonymous_visible_days_from_yesterday", "default_authenticated_plan")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ForecastPlan)
class ForecastPlanAdmin(SuperuserOnlyAdmin):
    list_display = ("title", "code", "tier", "visible_days_from_yesterday", "is_active", "sort_order")
    list_editable = ("visible_days_from_yesterday", "is_active", "sort_order")
    search_fields = ("title", "code")


@admin.register(AccountProfile)
class AccountProfileAdmin(SuperuserOnlyAdmin):
    list_display = ("phone_e164", "user")
    search_fields = ("phone_e164", "user__username")
    readonly_fields = ("user", "phone_e164")


@admin.register(Membership)
class MembershipAdmin(SuperuserOnlyAdmin):
    list_display = ("profile", "plan", "is_active", "starts_at", "expires_at", "source")
    list_filter = ("plan", "is_active", "source")
    search_fields = ("profile__phone_e164", "profile__user__username")
