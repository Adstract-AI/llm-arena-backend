from django import forms
from django.contrib import admin, messages

from experimental_llm_arena.models import ExperimentConfig
from helpers.env_variables import ANTHROPIC_API_KEY, GOOGLE_API_KEY, OPENAI_API_KEY
from llm_arena.models import ArenaBattle, ArenaTurn, BattleResponse, BattleVote, LLMModel, LLMProvider


PROVIDER_REQUIRED_API_KEYS = {
    "openai": ("OPENAI_API_KEY", OPENAI_API_KEY),
    "anthropic": ("ANTHROPIC_API_KEY", ANTHROPIC_API_KEY),
    "google": ("GOOGLE_API_KEY", GOOGLE_API_KEY),
}


def get_missing_provider_api_key(provider_name: str) -> str | None:
    """Return the required missing API key name for a provider, if any."""
    env_requirement = PROVIDER_REQUIRED_API_KEYS.get(provider_name.strip().lower())
    if env_requirement is None:
        return None

    env_name, env_value = env_requirement
    return None if env_value else env_name


class LLMModelAdminForm(forms.ModelForm):
    class Meta:
        model = LLMModel
        fields = "__all__"

    def clean(self):
        cleaned_data = super().clean()
        provider = cleaned_data.get("provider")
        is_active = cleaned_data.get("is_active")

        if provider and is_active:
            missing_env_name = get_missing_provider_api_key(provider.name)
            if missing_env_name:
                raise forms.ValidationError(
                    f"Cannot activate models from provider '{provider.display_name}' because "
                    f"{missing_env_name} is not configured."
                )

        return cleaned_data


class ReadOnlyAdminMixin:
    def get_readonly_fields(self, request, obj=None):
        return [field.name for field in self.model._meta.fields]

    def has_change_permission(self, request, obj=None) -> bool:
        if request.method in {"GET", "HEAD", "OPTIONS"}:
            return True
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False


class ReadOnlyInlineMixin:
    can_delete = False

    def has_add_permission(self, request, obj=None) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False


@admin.action(description="Mark selected models as active")
def make_models_active(modeladmin, request, queryset):
    blocked_messages: dict[str, str] = {}
    activatable_ids: list[int] = []

    for model in queryset.select_related("provider"):
        missing_env_name = get_missing_provider_api_key(model.provider_name)
        if missing_env_name:
            blocked_messages[model.provider.display_name] = missing_env_name
            continue
        activatable_ids.append(model.pk)

    updated_count = 0
    if activatable_ids:
        updated_count = queryset.filter(pk__in=activatable_ids).update(is_active=True)
        modeladmin.message_user(
            request,
            f"Activated {updated_count} model(s).",
            level=messages.SUCCESS,
        )

    if blocked_messages:
        blocked_summary = ", ".join(
            f"{provider_name} ({env_name})"
            for provider_name, env_name in sorted(blocked_messages.items())
        )
        modeladmin.message_user(
            request,
            f"Skipped activation for provider(s) missing API keys: {blocked_summary}.",
            level=messages.ERROR,
        )


@admin.action(description="Mark selected models as inactive")
def make_models_inactive(modeladmin, request, queryset):
    queryset.update(is_active=False)


@admin.register(LLMProvider)
class LLMProviderAdmin(admin.ModelAdmin):
    list_display = ("name", "display_name", "api_base_url", "created_at")
    search_fields = ("name", "display_name", "description", "api_base_url")

    def has_add_permission(self, request) -> bool:
        return False


@admin.register(LLMModel)
class LLMModelAdmin(admin.ModelAdmin):
    form = LLMModelAdminForm
    list_display = (
        "name",
        "external_model_id",
        "provider",
        "is_active",
        "is_fine_tuned",
        "is_macedonian_optimized",
    )
    list_filter = ("provider", "is_active", "is_fine_tuned", "is_macedonian_optimized")
    search_fields = ("name", "external_model_id", "description", "provider__name")
    actions = (make_models_active, make_models_inactive)


class ArenaTurnInline(ReadOnlyInlineMixin, admin.StackedInline):
    model = ArenaTurn
    extra = 0
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "turn_number",
                    "status",
                    "prompt",
                    "answer_a",
                    "answer_b",
                    "created_at",
                ),
            },
        ),
        (
            "Diagnostics",
            {
                "classes": ("collapse",),
                "fields": ("error_message",),
            },
        ),
    )
    readonly_fields = (
        "turn_number",
        "status",
        "prompt",
        "answer_a",
        "answer_b",
        "error_message",
        "created_at",
    )

    @staticmethod
    def _get_response_text(obj: ArenaTurn, slot: str) -> str:
        response = obj.responses.filter(slot=slot).first()
        if response is None:
            return "-"
        text = (response.response_text or "").strip()
        return text or "-"

    def answer_a(self, obj: ArenaTurn) -> str:
        return self._get_response_text(obj, BattleResponse.ResponseSlot.A)

    answer_a.short_description = "answer A"

    def answer_b(self, obj: ArenaTurn) -> str:
        return self._get_response_text(obj, BattleResponse.ResponseSlot.B)

    answer_b.short_description = "answer B"


class ExperimentConfigInline(ReadOnlyInlineMixin, admin.StackedInline):
    model = ExperimentConfig
    extra = 0
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "model_mode",
                    "share_values_across_models",
                ),
            },
        ),
        (
            "Temperature",
            {
                "classes": ("collapse",),
                "fields": (
                    "temperature_enabled",
                    "temperature_distribution",
                    "temperature_value_a",
                    "temperature_value_b",
                ),
            },
        ),
        (
            "Top P",
            {
                "classes": ("collapse",),
                "fields": (
                    "top_p_enabled",
                    "top_p_distribution",
                    "top_p_value_a",
                    "top_p_value_b",
                ),
            },
        ),
        (
            "Top K",
            {
                "classes": ("collapse",),
                "fields": (
                    "top_k_enabled",
                    "top_k_distribution",
                    "top_k_value_a",
                    "top_k_value_b",
                ),
            },
        ),
        (
            "Penalties",
            {
                "classes": ("collapse",),
                "fields": (
                    "frequency_penalty_enabled",
                    "frequency_penalty_distribution",
                    "frequency_penalty_value_a",
                    "frequency_penalty_value_b",
                    "presence_penalty_enabled",
                    "presence_penalty_distribution",
                    "presence_penalty_value_a",
                    "presence_penalty_value_b",
                ),
            },
        ),
    )
    readonly_fields = (
        "model_mode",
        "share_values_across_models",
        "temperature_enabled",
        "temperature_distribution",
        "temperature_value_a",
        "temperature_value_b",
        "top_p_enabled",
        "top_p_distribution",
        "top_p_value_a",
        "top_p_value_b",
        "top_k_enabled",
        "top_k_distribution",
        "top_k_value_a",
        "top_k_value_b",
        "frequency_penalty_enabled",
        "frequency_penalty_distribution",
        "frequency_penalty_value_a",
        "frequency_penalty_value_b",
        "presence_penalty_enabled",
        "presence_penalty_distribution",
        "presence_penalty_value_a",
        "presence_penalty_value_b",
    )


class BattleVoteInline(ReadOnlyInlineMixin, admin.StackedInline):
    model = BattleVote
    extra = 0
    can_delete = False

@admin.register(ArenaBattle)
class ArenaBattleAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ("id", "model_a", "model_b", "status", "created_at", "completed_at")
    list_filter = ("status", "model_a__provider", "model_b__provider")
    search_fields = ("id", "model_a__name", "model_b__name", "error_message")
    fields = ("model_a", "model_b", "status", "error_message", "completed_at", "created_at", "updated_at")
    inlines = (ExperimentConfigInline, ArenaTurnInline, BattleVoteInline)

    def has_add_permission(self, request) -> bool:
        return False

    class Media:
        css = {"all": ("admin/css/compact_inline.css",)}
