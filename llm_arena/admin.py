from django.contrib import admin

from llm_arena.models import ArenaBattle, BattleResponse, BattleVote, LLMModel, LLMProvider


@admin.register(LLMProvider)
class LLMProviderAdmin(admin.ModelAdmin):
    list_display = ("name", "provider_type", "is_active", "created_at")
    list_filter = ("provider_type", "is_active")
    search_fields = ("name", "slug")


@admin.register(LLMModel)
class LLMModelAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "provider",
        "external_model_id",
        "is_active",
        "is_fine_tuned",
        "is_macedonian_optimized",
    )
    list_filter = ("provider", "is_active", "is_fine_tuned", "is_macedonian_optimized")
    search_fields = ("name", "slug", "external_model_id")


class BattleResponseInline(admin.TabularInline):
    model = BattleResponse
    extra = 0


class BattleVoteInline(admin.StackedInline):
    model = BattleVote
    extra = 0
    can_delete = False


@admin.register(ArenaBattle)
class ArenaBattleAdmin(admin.ModelAdmin):
    list_display = ("id", "status", "prompt_language", "created_at", "completed_at")
    list_filter = ("status", "prompt_language")
    search_fields = ("prompt", "requester_identifier")
    inlines = (BattleResponseInline, BattleVoteInline)


@admin.register(BattleResponse)
class BattleResponseAdmin(admin.ModelAdmin):
    list_display = ("id", "battle", "slot", "llm_model", "status", "latency_ms")
    list_filter = ("slot", "status", "llm_model__provider")
    search_fields = ("battle__prompt", "llm_model__name", "llm_model__external_model_id")


@admin.register(BattleVote)
class BattleVoteAdmin(admin.ModelAdmin):
    list_display = ("id", "battle", "choice", "created_at")
    list_filter = ("choice",)
    search_fields = ("battle__prompt", "voter_identifier")
