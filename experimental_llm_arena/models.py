from django.db import models

from common.models import TimestampedModel
from llm_arena.models import ArenaBattle


class ParameterSamplingSpec(TimestampedModel):
    """Store admin-configurable sampling settings for one experimental parameter."""

    class ParameterName(models.TextChoices):
        TEMPERATURE = "temperature", "Temperature"
        TOP_P = "top_p", "Top P"
        TOP_K = "top_k", "Top K"
        FREQUENCY_PENALTY = "frequency_penalty", "Frequency Penalty"
        PRESENCE_PENALTY = "presence_penalty", "Presence Penalty"

    class ValueType(models.TextChoices):
        FLOAT = "float", "Float"
        INTEGER = "int", "Integer"

    parameter_name = models.CharField(
        max_length=32,
        choices=ParameterName.choices,
        unique=True,
    )
    value_type = models.CharField(max_length=16, choices=ValueType.choices)
    minimum_value = models.DecimalField(max_digits=8, decimal_places=4)
    maximum_value = models.DecimalField(max_digits=8, decimal_places=4)
    uniform_min = models.DecimalField(max_digits=8, decimal_places=4)
    uniform_max = models.DecimalField(max_digits=8, decimal_places=4)
    normal_mean = models.DecimalField(max_digits=8, decimal_places=4)
    normal_std = models.DecimalField(max_digits=8, decimal_places=4)
    beta_alpha = models.DecimalField(max_digits=8, decimal_places=4)
    beta_beta = models.DecimalField(max_digits=8, decimal_places=4)

    class Meta:
        ordering = ["parameter_name"]

    def __str__(self) -> str:
        return self.parameter_name


class ExperimentConfig(TimestampedModel):
    """Store the sampled runtime generation configuration for one arena battle."""

    class ModelMode(models.TextChoices):
        SAME_MODEL = "same_model", "Same Model"
        DIFFERENT_MODELS = "different_models", "Different Models"

    class DistributionType(models.TextChoices):
        UNIFORM = "uniform", "Uniform"
        NORMAL = "normal", "Normal"
        BETA = "beta", "Beta"

    battle = models.OneToOneField(
        ArenaBattle,
        on_delete=models.CASCADE,
        related_name="experiment_config",
    )
    model_mode = models.CharField(max_length=24, choices=ModelMode.choices)
    share_values_across_models = models.BooleanField(null=True, blank=True)

    temperature_enabled = models.BooleanField(default=False)
    temperature_distribution = models.CharField(
        max_length=16,
        choices=DistributionType.choices,
        null=True,
        blank=True,
    )
    temperature_value_a = models.DecimalField(
        max_digits=6,
        decimal_places=4,
        null=True,
        blank=True,
    )
    temperature_value_b = models.DecimalField(
        max_digits=6,
        decimal_places=4,
        null=True,
        blank=True,
    )

    top_p_enabled = models.BooleanField(default=False)
    top_p_distribution = models.CharField(
        max_length=16,
        choices=DistributionType.choices,
        null=True,
        blank=True,
    )
    top_p_value_a = models.DecimalField(
        max_digits=6,
        decimal_places=4,
        null=True,
        blank=True,
    )
    top_p_value_b = models.DecimalField(
        max_digits=6,
        decimal_places=4,
        null=True,
        blank=True,
    )

    top_k_enabled = models.BooleanField(default=False)
    top_k_distribution = models.CharField(
        max_length=16,
        choices=DistributionType.choices,
        null=True,
        blank=True,
    )
    top_k_value_a = models.PositiveIntegerField(null=True, blank=True)
    top_k_value_b = models.PositiveIntegerField(null=True, blank=True)

    frequency_penalty_enabled = models.BooleanField(default=False)
    frequency_penalty_distribution = models.CharField(
        max_length=16,
        choices=DistributionType.choices,
        null=True,
        blank=True,
    )
    frequency_penalty_value_a = models.DecimalField(
        max_digits=6,
        decimal_places=4,
        null=True,
        blank=True,
    )
    frequency_penalty_value_b = models.DecimalField(
        max_digits=6,
        decimal_places=4,
        null=True,
        blank=True,
    )

    presence_penalty_enabled = models.BooleanField(default=False)
    presence_penalty_distribution = models.CharField(
        max_length=16,
        choices=DistributionType.choices,
        null=True,
        blank=True,
    )
    presence_penalty_value_a = models.DecimalField(
        max_digits=6,
        decimal_places=4,
        null=True,
        blank=True,
    )
    presence_penalty_value_b = models.DecimalField(
        max_digits=6,
        decimal_places=4,
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"ExperimentConfig<{self.battle_id}>"
