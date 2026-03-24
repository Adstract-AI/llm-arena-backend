from django.contrib import admin

from llm_arena.models import ArenaBattle, ArenaTurn, BattleResponse, BattleVote, LLMModel, LLMProvider


@admin.action(description="Mark selected models as active")
def make_models_active(modeladmin, request, queryset):
    queryset.update(is_active=True)


@admin.action(description="Mark selected models as inactive")
def make_models_inactive(modeladmin, request, queryset):
    queryset.update(is_active=False)


@admin.register(LLMProvider)
class LLMProviderAdmin(admin.ModelAdmin):
    list_display = ("name", "display_name", "api_base_url", "created_at")
    search_fields = ("name", "display_name", "description", "api_base_url")


@admin.register(LLMModel)
class LLMModelAdmin(admin.ModelAdmin):
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


class ArenaTurnInline(admin.TabularInline):
    model = ArenaTurn
    extra = 0
    fields = ("turn_number", "status", "prompt", "error_message", "created_at")
    readonly_fields = ("turn_number", "status", "prompt", "error_message", "created_at")
    show_change_link = True


class BattleResponseInline(admin.TabularInline):
    model = BattleResponse
    extra = 0
    fields = ("slot", "status", "response_text", "error_message", "finish_reason", "latency_ms")
    readonly_fields = ("slot", "status", "response_text", "error_message", "finish_reason", "latency_ms")


class BattleVoteInline(admin.StackedInline):
    model = BattleVote
    extra = 0
    can_delete = False


@admin.register(ArenaBattle)
class ArenaBattleAdmin(admin.ModelAdmin):
    list_display = ("id", "model_a", "model_b", "status", "created_at", "completed_at")
    list_filter = ("status", "model_a__provider", "model_b__provider")
    search_fields = ("id", "model_a__name", "model_b__name", "error_message")
    inlines = (ArenaTurnInline, BattleVoteInline)


@admin.register(ArenaTurn)
class ArenaTurnAdmin(admin.ModelAdmin):
    list_display = ("id", "battle", "turn_number", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("battle__id", "prompt", "error_message")
    inlines = (BattleResponseInline,)


@admin.register(BattleResponse)
class BattleResponseAdmin(admin.ModelAdmin):
    list_display = ("id", "turn", "slot", "get_model_name", "status", "latency_ms")
    list_filter = ("slot", "status")
    search_fields = ("turn__battle__id", "turn__prompt", "error_message", "response_text")

    @staticmethod
    def get_model_name(obj):
        return obj.llm_model.name

    get_model_name.short_description = "model"


@admin.register(BattleVote)
class BattleVoteAdmin(admin.ModelAdmin):
    list_display = ("id", "battle", "choice", "created_at")
    list_filter = ("choice",)
    search_fields = ("battle__id", "battle__model_a__name", "battle__model_b__name", "feedback")
