from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from accounts.models import OAuthAccount, User


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
    inlines = (OAuthAccountInline,)
    list_display = ("username", "email", "first_name", "last_name", "is_staff", "is_active")
    search_fields = ("username", "email", "first_name", "last_name")


@admin.register(OAuthAccount)
class OAuthAccountAdmin(admin.ModelAdmin):
    list_display = ("email", "provider", "provider_user_id", "email_verified", "user", "created_at")
    list_filter = ("provider", "email_verified")
    search_fields = ("email", "provider_user_id", "user__email", "user__username")
    readonly_fields = ("created_at", "updated_at")
