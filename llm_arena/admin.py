from django import forms
from django.contrib import admin, messages
from django.contrib.admin.helpers import ACTION_CHECKBOX_NAME
from django.contrib.admin.helpers import ActionForm
from django.template.response import TemplateResponse

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
    fieldsets = (
        (
            "Catalog",
            {
                "fields": (
                    "provider",
                    "name",
                    "external_model_id",
                    "description",
                    "configuration",
                ),
            },
        ),
        (
            "Availability",
            {
                "fields": (
                    "is_active",
                    "is_fine_tuned",
                    "is_macedonian_optimized",
                ),
            },
        ),
        (
            "Experimental Support",
            {
                "fields": (
                    "supports_temperature",
                    "supports_top_p",
                    "supports_top_k",
                    "supports_frequency_penalty",
                    "supports_presence_penalty",
                ),
            },
        ),
    )


@admin.register(AgentPrompt)
class AgentPromptAdmin(admin.ModelAdmin):
    list_display = ("name", "agent_type", "is_active", "updated_at")
    list_filter = ("agent_type", "is_active")
    search_fields = ("name", "system_prompt")
    actions = ("delete_selected_agent_prompts",)

    def get_actions(self, request):
        actions = super().get_actions(request)
        actions.pop("delete_selected", None)
        return actions

    def has_delete_permission(self, request, obj=None) -> bool:
        if obj is None:
            return True
        return AgentPrompt.objects.filter(agent_type=obj.agent_type).count() > 1

    def delete_model(self, request, obj):
        if AgentPrompt.objects.filter(agent_type=obj.agent_type).count() <= 1:
            self.message_user(
                request,
                f"Cannot delete the last prompt for agent type '{obj.agent_type}'.",
                level=messages.ERROR,
            )
            return
        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        blocked_agent_types = []
        deletable_ids: list[int] = []

        selected_counts_by_agent_type = {}
        for prompt in queryset:
            selected_counts_by_agent_type[prompt.agent_type] = (
                selected_counts_by_agent_type.get(prompt.agent_type, 0) + 1
            )

        for agent_type, selected_count in selected_counts_by_agent_type.items():
            total_count = AgentPrompt.objects.filter(agent_type=agent_type).count()
            if total_count - selected_count <= 0:
                blocked_agent_types.append(agent_type)

        for prompt in queryset:
            if prompt.agent_type not in blocked_agent_types:
                deletable_ids.append(prompt.pk)

        if blocked_agent_types:
            blocked_summary = ", ".join(sorted(blocked_agent_types))
            self.message_user(
                request,
                f"Cannot delete the last remaining prompt for agent type(s): {blocked_summary}.",
                level=messages.ERROR,
            )

        if deletable_ids:
            super().delete_queryset(
                request,
                queryset.filter(pk__in=deletable_ids),
            )

    @admin.action(description="Delete selected agent prompts")
    def delete_selected_agent_prompts(self, request, queryset):
        blocked_agent_types = []
        deletable_ids: list[int] = []
        selected_counts_by_agent_type: dict[str, int] = {}

        for prompt in queryset:
            selected_counts_by_agent_type[prompt.agent_type] = (
                selected_counts_by_agent_type.get(prompt.agent_type, 0) + 1
            )

        for agent_type, selected_count in selected_counts_by_agent_type.items():
            total_count = AgentPrompt.objects.filter(agent_type=agent_type).count()
            if total_count - selected_count <= 0:
                blocked_agent_types.append(agent_type)

        for prompt in queryset:
            if prompt.agent_type not in blocked_agent_types:
                deletable_ids.append(prompt.pk)

        if blocked_agent_types:
            blocked_summary = ", ".join(sorted(blocked_agent_types))
            self.message_user(
                request,
                f"Cannot delete the last remaining prompt for agent type(s): {blocked_summary}.",
                level=messages.ERROR,
            )

        if deletable_ids:
            deleted_count, _ = AgentPrompt.objects.filter(pk__in=deletable_ids).delete()
            self.message_user(
                request,
                f"Successfully deleted {deleted_count} agent prompt(s).",
                level=messages.SUCCESS,
            )


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
            "Improvements",
            {
                "classes": ("collapse",),
                "fields": (
                    "improvement_a",
                    "improvement_b",
                ),
            },
        ),
        (
            "Diagnostics",
            {
                "classes": ("collapse",),
                "fields": (
                    "error_message",
                    "diagnostics_a",
                    "diagnostics_b",
                    "raw_metadata_a",
                    "raw_metadata_b",
                ),
            },
        ),
    )
    readonly_fields = (
        "turn_number",
        "status",
        "prompt",
        "answer_a",
        "answer_b",
        "improvement_a",
        "improvement_b",
        "error_message",
        "diagnostics_a",
        "diagnostics_b",
        "raw_metadata_a",
        "raw_metadata_b",
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

    @staticmethod
    def _get_response_improvement_text(obj: ArenaTurn, slot: str) -> str:
        response = obj.responses.filter(slot=slot).first()
        if response is None or not response.improvement_text:
            return "-"
        return response.improvement_text

    def improvement_a(self, obj: ArenaTurn) -> str:
        return self._get_response_improvement_text(obj, BattleResponse.ResponseSlot.A)

    improvement_a.short_description = "improvement A"

    def improvement_b(self, obj: ArenaTurn) -> str:
        return self._get_response_improvement_text(obj, BattleResponse.ResponseSlot.B)

    improvement_b.short_description = "improvement B"

    @staticmethod
    def _get_response(obj: ArenaTurn, slot: str) -> BattleResponse | None:
        return obj.responses.filter(slot=slot).first()

    @classmethod
    def _get_response_diagnostics(cls, obj: ArenaTurn, slot: str) -> str:
        response = cls._get_response(obj, slot)
        if response is None:
            return "-"

        return (
            f"status={response.status}, "
            f"finish_reason={response.finish_reason or '-'}, "
            f"prompt_tokens={response.prompt_tokens if response.prompt_tokens is not None else '-'}, "
            f"completion_tokens={response.completion_tokens if response.completion_tokens is not None else '-'}, "
            f"total_tokens={response.total_tokens if response.total_tokens is not None else '-'}, "
            f"latency_ms={response.latency_ms if response.latency_ms is not None else '-'}"
        )

    @classmethod
    def _get_response_raw_metadata(cls, obj: ArenaTurn, slot: str):
        response = cls._get_response(obj, slot)
        if response is None or not response.raw_metadata:
            return "-"
        return response.raw_metadata

    def diagnostics_a(self, obj: ArenaTurn) -> str:
        return self._get_response_diagnostics(obj, BattleResponse.ResponseSlot.A)

    diagnostics_a.short_description = "diagnostics A"

    def diagnostics_b(self, obj: ArenaTurn) -> str:
        return self._get_response_diagnostics(obj, BattleResponse.ResponseSlot.B)

    diagnostics_b.short_description = "diagnostics B"

    def raw_metadata_a(self, obj: ArenaTurn):
        return self._get_response_raw_metadata(obj, BattleResponse.ResponseSlot.A)

    raw_metadata_a.short_description = "raw metadata A"

    def raw_metadata_b(self, obj: ArenaTurn):
        return self._get_response_raw_metadata(obj, BattleResponse.ResponseSlot.B)

    raw_metadata_b.short_description = "raw metadata B"


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
    list_display = (
        "id",
        "user",
        "model_a",
        "model_b",
        "status",
        "user_vote_choice",
        "llm_judge_vote_choice",
        "created_at",
        "completed_at",
    )
    list_filter = ("status", "model_a__provider", "model_b__provider")
    search_fields = ("id", "user__email", "user__username", "model_a__name", "model_b__name", "error_message")
    fields = ("user", "model_a", "model_b", "status", "error_message", "completed_at", "created_at", "updated_at")
    inlines = (ExperimentConfigInline, ArenaTurnInline, BattleVoteInline, LLMJudgeVoteInline)
    actions = ("judge_selected_battles",)

    def get_queryset(self, request):
        """
        Return the battle admin queryset with related vote rows preloaded.

        Args:
            request: Active admin request.

        Returns:
            QuerySet[ArenaBattle]: Battle queryset with related objects selected.
        """
        return (
            super()
            .get_queryset(request)
            .select_related("vote", "llm_judge_vote")
        )

    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        if obj is None:
            return True
        return super().has_change_permission(request, obj=obj)

    def user_vote_choice(self, obj: ArenaBattle) -> str:
        """
        Return the human vote choice shown in the battle changelist.

        Args:
            obj: Battle row rendered in admin.

        Returns:
            str: Stored human vote choice or a dash when absent.
        """
        vote = getattr(obj, "vote", None)
        return vote.choice if vote is not None else "-"

    user_vote_choice.short_description = "user vote"
    user_vote_choice.admin_order_field = "vote__choice"

    def llm_judge_vote_choice(self, obj: ArenaBattle) -> str:
        """
        Return the LLM judge vote choice shown in the battle changelist.

        Args:
            obj: Battle row rendered in admin.

        Returns:
            str: Stored LLM judge vote choice or a dash when absent.
        """
        vote = getattr(obj, "llm_judge_vote", None)
        return vote.choice if vote is not None else "-"

    llm_judge_vote_choice.short_description = "llm judge vote"
    llm_judge_vote_choice.admin_order_field = "llm_judge_vote__choice"

    @admin.action(description="Judge selected battles with selected model")
    def judge_selected_battles(self, request, queryset):
        self.agent_service.set_user(request.user)
        judge_model = self._get_selected_judge_model(request)
        if judge_model is None:
            self.message_user(
                request,
                "Select an active judge model before running the judge action.",
                level=messages.ERROR,
            )
            return

        unvoted_battles = list(
            queryset
            .filter(vote__isnull=True)
            .order_by("created_at")
        )
        confirmed_unvoted = request.POST.get("confirm_unvoted_judging") == "yes"
        if unvoted_battles and not confirmed_unvoted:
            context = {
                **self.admin_site.each_context(request),
                "title": "Confirm judging battles without a human vote",
                "queryset": queryset.order_by("created_at"),
                "unvoted_battles": unvoted_battles,
                "judge_model": judge_model,
                "action_checkbox_name": ACTION_CHECKBOX_NAME,
                "action_name": "judge_selected_battles",
            }
            return TemplateResponse(
                request,
                "admin/llm_arena/arena_battle/judge_selected_confirmation.html",
                context,
            )

        judged_count = 0
        skipped_battles: dict[str, list[str]] = {}
        failed_battles: dict[str, list[str]] = {}

        for battle in queryset.order_by("created_at"):
            try:
                self.agent_service.judge_battle(
                    battle_id=battle.id,
                    judge_model=judge_model,
                    allow_without_human_vote=confirmed_unvoted,
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
        js = ("admin/js/arena_battle_actions.js",)
