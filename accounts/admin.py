from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.http import HttpResponseRedirect
from django.urls import reverse

from accounts.models import OAuthAccount, User
from accounts.services.auth_service import AuthService


class OAuthAccountInline(admin.TabularInline):
    model = OAuthAccount
    extra = 0
    can_delete = False
    readonly_fields = (
        "provider",
        "provider_user_id",
        "email",
        "email_verified",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request, obj=None) -> bool:
        return False


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    auth_service = AuthService()
    inlines = (OAuthAccountInline,)
    list_display = ("username", "email", "first_name", "last_name", "is_staff", "is_active")
    search_fields = ("username", "email", "first_name", "last_name")
    actions = ("anonymize_selected_users",)
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name", "email")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "user_permissions")}),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("username", "email", "password1", "password2", "is_staff", "is_superuser"),
            },
        ),
    )

    def get_actions(self, request):
        actions = super().get_actions(request)
        actions.pop("delete_selected", None)
        return actions

    def _anonymize_user(self, user: User) -> None:
        self.auth_service.anonymize_user(user)

    def delete_model(self, request, obj):
        self._anonymize_user(obj)
        request._anonymized_user_label = str(obj.pk)

    def delete_queryset(self, request, queryset):
        for user in queryset.prefetch_related("oauth_accounts"):
            self._anonymize_user(user)

    def response_delete(self, request, obj_display, obj_id):
        anonymized_user_label = getattr(request, "_anonymized_user_label", None)
        if anonymized_user_label is not None:
            self.message_user(
                request,
                f"User '{anonymized_user_label}' was anonymized instead of being deleted.",
                level=messages.SUCCESS,
            )
            return HttpResponseRedirect(reverse("admin:accounts_user_changelist"))
        return super().response_delete(request, obj_display, obj_id)

    @admin.action(description="Delete selected users")
    def anonymize_selected_users(self, request, queryset):
        anonymized_count = 0
        for user in queryset.prefetch_related("oauth_accounts"):
            self._anonymize_user(user)
            anonymized_count += 1

        self.message_user(
            request,
            f"Anonymized {anonymized_count} user(s) instead of deleting them.",
            level=messages.SUCCESS,
        )


@admin.register(OAuthAccount)
class OAuthAccountAdmin(admin.ModelAdmin):
    list_display = ("email", "provider", "provider_user_id", "email_verified", "user", "created_at")
    list_filter = ("provider", "email_verified")
    search_fields = ("email", "provider_user_id", "user__email", "user__username")
    readonly_fields = (
        "user",
        "provider",
        "provider_user_id",
        "email",
        "email_verified",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        if request.method in {"GET", "HEAD", "OPTIONS"}:
            return True
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False
