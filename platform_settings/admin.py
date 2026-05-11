from django import forms
from django.contrib import admin, messages
from django.db import transaction
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.http import unquote

from platform_settings.models import PlatformSettings, RateLimitUsage, RateLimits


class PlatformSettingsAdminForm(forms.ModelForm):
    class Meta:
        model = PlatformSettings
        fields = "__all__"

    def clean(self):
        cleaned_data = super().clean()
        is_active = cleaned_data.get("is_active")
        if not is_active:
            active_queryset = PlatformSettings.objects.filter(is_active=True)
            if self.instance.pk:
                active_queryset = active_queryset.exclude(pk=self.instance.pk)
            active_count = active_queryset.count()
            if active_count == 0:
                raise forms.ValidationError("At least one platform settings profile must stay active.")
        return cleaned_data


@admin.register(PlatformSettings)
class PlatformSettingsAdmin(admin.ModelAdmin):
    form = PlatformSettingsAdminForm
    list_display = ("name", "is_active", "rate_limits", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("name", "rate_limits__name")
    fieldsets = (
        (
            "Settings",
            {
                "fields": (
                    "name",
                    "is_active",
                    "rate_limits",
                ),
            },
        ),
    )
    actions = ("delete_selected_platform_settings",)

    def save_model(self, request, obj, form, change):
        with transaction.atomic():
            if obj.is_active:
                PlatformSettings.objects.exclude(pk=obj.pk).update(is_active=False)
            super().save_model(request, obj, form, change)

    def has_delete_permission(self, request, obj=None) -> bool:
        return super().has_delete_permission(request, obj=obj)

    def get_actions(self, request):
        actions = super().get_actions(request)
        actions.pop("delete_selected", None)
        return actions

    def delete_view(self, request, object_id, extra_context=None):
        obj = self.get_object(request, unquote(object_id))
        if obj is not None and self._is_delete_blocked(obj):
            self.message_user(request, self._get_delete_block_message(obj), messages.ERROR)
            return HttpResponseRedirect(self._get_change_url(obj))
        return super().delete_view(request, object_id, extra_context=extra_context)

    def delete_model(self, request, obj):
        if self._is_delete_blocked(obj):
            self.message_user(request, self._get_delete_block_message(obj), messages.ERROR)
            return
        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        blocked_count = queryset.filter(is_active=True).count()
        deletable_queryset = queryset.filter(is_active=False)
        if PlatformSettings.objects.count() - deletable_queryset.count() < 1:
            blocked_count += deletable_queryset.count()
            deletable_queryset = PlatformSettings.objects.none()

        deleted_count = deletable_queryset.count()
        if deleted_count:
            deletable_queryset.delete()
            self.message_user(request, f"Deleted {deleted_count} inactive settings profile(s).", messages.SUCCESS)
        if blocked_count:
            self.message_user(
                request,
                "Skipped settings profile deletion because one active profile must remain.",
                messages.ERROR,
            )

    @admin.action(description="Delete selected platform settings")
    def delete_selected_platform_settings(self, request, queryset):
        self.delete_queryset(request, queryset)

    @staticmethod
    def _is_delete_blocked(obj: PlatformSettings) -> bool:
        return obj.is_active or PlatformSettings.objects.count() <= 1

    @staticmethod
    def _get_delete_block_message(obj: PlatformSettings) -> str:
        if obj.is_active:
            return "Active platform settings cannot be deleted. Make another settings profile active first."
        return "The last platform settings profile cannot be deleted."

    def _get_change_url(self, obj: PlatformSettings) -> str:
        return reverse(
            f"admin:{self.model._meta.app_label}_{self.model._meta.model_name}_change",
            args=(obj.pk,),
            current_app=self.admin_site.name,
        )


@admin.register(RateLimits)
class RateLimitsAdmin(admin.ModelAdmin):
    list_display = ("name", "updated_at")
    search_fields = ("name",)
    fieldsets = (
        (
            "Identity",
            {
                "fields": ("name",),
            },
        ),
        (
            "Normal Arena Anonymous",
            {
                "fields": (
                    "normal_arena_anonymous_per_minute",
                    "normal_arena_anonymous_per_hour",
                    "normal_arena_anonymous_per_day",
                ),
            },
        ),
        (
            "Normal Arena User",
            {
                "fields": (
                    "normal_arena_user_per_minute",
                    "normal_arena_user_per_hour",
                    "normal_arena_user_per_day",
                ),
            },
        ),
        (
            "Experimental Arena User",
            {
                "fields": (
                    "experimental_arena_user_per_minute",
                    "experimental_arena_user_per_hour",
                    "experimental_arena_user_per_day",
                ),
            },
        ),
        (
            "Chat User",
            {
                "fields": (
                    "chat_user_per_minute",
                    "chat_user_per_hour",
                    "chat_user_per_day",
                ),
            },
        ),
    )
    actions = ("delete_selected_rate_limits",)

    def has_delete_permission(self, request, obj=None) -> bool:
        return super().has_delete_permission(request, obj=obj)

    def get_actions(self, request):
        actions = super().get_actions(request)
        actions.pop("delete_selected", None)
        return actions

    def delete_view(self, request, object_id, extra_context=None):
        obj = self.get_object(request, unquote(object_id))
        if obj is not None and self._is_delete_blocked(obj):
            self.message_user(
                request,
                "This rate limit profile cannot be deleted because a platform settings profile uses it.",
                messages.ERROR,
            )
            return HttpResponseRedirect(self._get_change_url(obj))
        return super().delete_view(request, object_id, extra_context=extra_context)

    def delete_model(self, request, obj):
        if self._is_delete_blocked(obj):
            self.message_user(
                request,
                "This rate limit profile cannot be deleted because a platform settings profile uses it.",
                messages.ERROR,
            )
            return
        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        linked_queryset = queryset.filter(platform_settings__isnull=False)
        deletable_queryset = queryset.filter(platform_settings__isnull=True)
        deleted_count = deletable_queryset.count()
        if deleted_count:
            deletable_queryset.delete()
            self.message_user(request, f"Deleted {deleted_count} rate limit profile(s).", messages.SUCCESS)
        if linked_queryset.exists():
            self.message_user(
                request,
                "Skipped rate limit profile deletion because linked settings profiles still use them.",
                messages.ERROR,
            )

    @admin.action(description="Delete selected rate limit profiles")
    def delete_selected_rate_limits(self, request, queryset):
        self.delete_queryset(request, queryset)

    @staticmethod
    def _is_delete_blocked(obj: RateLimits) -> bool:
        return hasattr(obj, "platform_settings")

    def _get_change_url(self, obj: RateLimits) -> str:
        return reverse(
            f"admin:{self.model._meta.app_label}_{self.model._meta.model_name}_change",
            args=(obj.pk,),
            current_app=self.admin_site.name,
        )


@admin.register(RateLimitUsage)
class RateLimitUsageAdmin(admin.ModelAdmin):
    list_display = ("bucket", "identity_type", "identity", "window", "window_start", "count")
    list_filter = ("bucket", "identity_type", "window")
    search_fields = ("identity",)
    readonly_fields = (
        "bucket",
        "identity_type",
        "identity",
        "window",
        "window_start",
        "count",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        if request.method in {"GET", "HEAD", "OPTIONS"}:
            return True
        return False
