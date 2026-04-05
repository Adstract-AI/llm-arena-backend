from django.contrib import admin

from experimental_llm_arena.models import ParameterSamplingSpec


@admin.register(ParameterSamplingSpec)
class ParameterSamplingSpecAdmin(admin.ModelAdmin):
    list_display = (
        "parameter_name",
        "value_type",
        "minimum_value",
        "maximum_value",
        "uniform_min",
        "uniform_max",
        "normal_mean",
        "normal_std",
    )
    search_fields = ("parameter_name",)
    readonly_fields = ("parameter_name", "value_type")
    fieldsets = (
        (
            "Identity",
            {
                "fields": (
                    "parameter_name",
                    "value_type",
                ),
            },
        ),
        (
            "Allowed Range",
            {
                "fields": (
                    "minimum_value",
                    "maximum_value",
                ),
            },
        ),
        (
            "Uniform Distribution",
            {
                "fields": (
                    "uniform_min",
                    "uniform_max",
                ),
            },
        ),
        (
            "Normal Distribution",
            {
                "fields": (
                    "normal_mean",
                    "normal_std",
                ),
            },
        ),
        (
            "Beta Distribution",
            {
                "fields": (
                    "beta_alpha",
                    "beta_beta",
                ),
            },
        ),
    )

    def has_add_permission(self, request) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False
