from django import forms
from django.contrib import admin, messages
from django.contrib.admin.helpers import ActionForm

from experimental_llm_arena.models import ExperimentConfig
from helpers.env_variables import ANTHROPIC_API_KEY, GOOGLE_API_KEY, OPENAI_API_KEY
from llm_arena.exceptions import (
    ActiveAgentPromptNotFoundException,
    ArenaBattleAlreadyHasJudgeVoteException,
    ArenaBattleMissingHumanVoteException,
    LLMInferenceException,
)
from llm_arena.models import (
    AgentPrompt,
    ArenaBattle,
    ArenaTurn,
    BattleResponse,
    BattleVote,
    LLMJudgeVote,
    LLMModel,
    LLMProvider,
)
from llm_arena.services.agent_service import AgentService


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


class ArenaBattleJudgeActionForm(ActionForm):
    judge_model = forms.ModelChoiceField(
        queryset=LLMModel.objects.none(),
        required=False,
        label="Judge model",
    )

    def __init__(self, *args, **kwargs):
        """
        Populate the judge-model choices with active arena models.

        Args:
            *args: Positional form arguments.
            **kwargs: Keyword form arguments.
        """
        super().__init__(*args, **kwargs)
        self.fields["judge_model"].queryset = (
            LLMModel.objects
            .select_related("provider")
            .filter(is_active=True)
            .order_by("name")
        )


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
        "supports_temperature",
        "supports_top_p",
        "supports_top_k",
        "supports_frequency_penalty",
        "supports_presence_penalty",
    )
    list_filter = (
        "provider",
        "is_active",
        "is_fine_tuned",
        "is_macedonian_optimized",
        "supports_temperature",
        "supports_top_p",
        "supports_top_k",
        "supports_frequency_penalty",
        "supports_presence_penalty",
    )
    search_fields = ("name", "external_model_id", "description", "provider__name")
    actions = (make_models_active, make_models_inactive)


@admin.register(AgentPrompt)
class AgentPromptAdmin(admin.ModelAdmin):
    list_display = ("name", "agent_type", "is_active", "updated_at")
    list_filter = ("agent_type", "is_active")
    search_fields = ("name", "system_prompt")


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
            "Parameter Summaries",
            {
                "classes": ("collapse",),
                "fields": (
                    "temperature_summary",
                    "top_p_summary",
                    "top_k_summary",
                    "frequency_penalty_summary",
                    "presence_penalty_summary",
                ),
            },
        ),
    )
    readonly_fields = (
        "model_mode",
        "share_values_across_models",
        "temperature_summary",
        "top_p_summary",
        "top_k_summary",
        "frequency_penalty_summary",
        "presence_penalty_summary",
    )

    @staticmethod
    def _build_parameter_summary(obj: ExperimentConfig, parameter_name: str) -> str:
        parameter_config = obj.get_parameter_config(parameter_name)
        if parameter_config is None:
            return "disabled"

        return (
            f"{parameter_config.distribution}: "
            f"A={parameter_config.value_a}, B={parameter_config.value_b}"
        )

    def temperature_summary(self, obj: ExperimentConfig) -> str:
        return self._build_parameter_summary(obj, "temperature")

    temperature_summary.short_description = "temperature"

    def top_p_summary(self, obj: ExperimentConfig) -> str:
        return self._build_parameter_summary(obj, "top_p")

    top_p_summary.short_description = "top p"

    def top_k_summary(self, obj: ExperimentConfig) -> str:
        return self._build_parameter_summary(obj, "top_k")

    top_k_summary.short_description = "top k"

    def frequency_penalty_summary(self, obj: ExperimentConfig) -> str:
        return self._build_parameter_summary(obj, "frequency_penalty")

    frequency_penalty_summary.short_description = "frequency penalty"

    def presence_penalty_summary(self, obj: ExperimentConfig) -> str:
        return self._build_parameter_summary(obj, "presence_penalty")

    presence_penalty_summary.short_description = "presence penalty"


class BattleVoteInline(ReadOnlyInlineMixin, admin.StackedInline):
    model = BattleVote
    extra = 0
    can_delete = False
    readonly_fields = ("choice", "feedback", "created_at")


class LLMJudgeVoteInline(ReadOnlyInlineMixin, admin.StackedInline):
    model = LLMJudgeVote
    extra = 0
    can_delete = False
    readonly_fields = ("judge_model", "choice", "reasoning", "created_at")


@admin.register(ArenaBattle)
class ArenaBattleAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    agent_service = AgentService()
    action_form = ArenaBattleJudgeActionForm
    list_display = ("id", "model_a", "model_b", "status", "created_at", "completed_at")
    list_filter = ("status", "model_a__provider", "model_b__provider")
    search_fields = ("id", "model_a__name", "model_b__name", "error_message")
    fields = ("model_a", "model_b", "status", "error_message", "completed_at", "created_at", "updated_at")
    inlines = (ExperimentConfigInline, ArenaTurnInline, BattleVoteInline, LLMJudgeVoteInline)
    actions = ("judge_selected_battles",)

    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        if obj is None:
            return True
        return super().has_change_permission(request, obj=obj)

    @admin.action(description="Judge selected battles with selected model")
    def judge_selected_battles(self, request, queryset):
        judge_model = self._get_selected_judge_model(request)
        if judge_model is None:
            self.message_user(
                request,
                "Select an active judge model before running the judge action.",
                level=messages.ERROR,
            )
            return

        judged_count = 0
        skipped_battles: dict[str, list[str]] = {}
        failed_battles: dict[str, list[str]] = {}

        for battle in queryset.order_by("created_at"):
            try:
                self.agent_service.judge_battle(
                    battle_id=battle.id,
                    judge_model=judge_model,
                )
                judged_count += 1
            except (ArenaBattleMissingHumanVoteException, ArenaBattleAlreadyHasJudgeVoteException) as exc:
                skipped_battles.setdefault(str(exc.detail), []).append(str(battle.id))
            except (ActiveAgentPromptNotFoundException, LLMInferenceException) as exc:
                failed_battles.setdefault(str(exc.detail), []).append(str(battle.id))

        if judged_count:
            self.message_user(
                request,
                f"Created {judged_count} LLM judge vote(s) using '{judge_model.name}'.",
                level=messages.SUCCESS,
            )
        for reason, battle_ids in skipped_battles.items():
            self.message_user(
                request,
                f"Skipped {len(battle_ids)} battle(s): {reason} ({', '.join(battle_ids)}).",
                level=messages.WARNING,
            )
        for reason, battle_ids in failed_battles.items():
            self.message_user(
                request,
                f"Failed to judge {len(battle_ids)} battle(s): {reason} ({', '.join(battle_ids)}).",
                level=messages.ERROR,
            )

    @staticmethod
    def _get_selected_judge_model(request) -> LLMModel | None:
        judge_model_id = (request.POST.get("judge_model") or "").strip()
        if not judge_model_id:
            return None

        return (
            LLMModel.objects
            .select_related("provider")
            .filter(pk=judge_model_id, is_active=True)
            .first()
        )

    class Media:
        css = {"all": ("admin/css/compact_inline.css",)}
