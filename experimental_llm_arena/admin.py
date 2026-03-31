from django.contrib import admin

from experimental_llm_arena.models import ExperimentConfig


@admin.register(ExperimentConfig)
class ExperimentConfigAdmin(admin.ModelAdmin):
    list_display = ("battle", "model_mode", "share_values_across_models", "created_at")
    list_filter = ("model_mode", "share_values_across_models")
    search_fields = ("battle__id",)
    readonly_fields = (
        "battle",
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
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request) -> bool:
        return False
