from django.core.exceptions import ObjectDoesNotExist
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
    """Store battle-level experimental metadata for one arena battle."""

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

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"ExperimentConfig<{self.battle_id}>"

    def get_parameter_config(self, parameter_name: str) -> models.Model | None:
        """
        Return the child config model for one experimental parameter when present.

        Args:
            parameter_name: Parameter identifier to resolve.

        Returns:
            models.Model | None: Linked parameter config instance or None.
        """
        related_name = EXPERIMENT_PARAMETER_CONFIG_MAP[parameter_name]["related_name"]
        try:
            return getattr(self, related_name)
        except ObjectDoesNotExist:
            return None


class BaseExperimentParameterConfig(TimestampedModel):
    """Store one enabled parameter configuration for an experimental battle."""

    experiment_config = models.OneToOneField(
        ExperimentConfig,
        on_delete=models.CASCADE,
    )
    distribution = models.CharField(
        max_length=16,
        choices=ExperimentConfig.DistributionType.choices,
    )

    class Meta:
        abstract = True


class DecimalExperimentParameterConfig(BaseExperimentParameterConfig):
    """Base model for decimal-valued experimental parameters."""

    value_a = models.DecimalField(max_digits=6, decimal_places=4)
    value_b = models.DecimalField(max_digits=6, decimal_places=4)

    class Meta:
        abstract = True


class IntegerExperimentParameterConfig(BaseExperimentParameterConfig):
    """Base model for integer-valued experimental parameters."""

    value_a = models.PositiveIntegerField()
    value_b = models.PositiveIntegerField()

    class Meta:
        abstract = True


class TemperatureExperimentConfig(DecimalExperimentParameterConfig):
    """Store sampled temperature values for one experiment."""

    experiment_config = models.OneToOneField(
        ExperimentConfig,
        on_delete=models.CASCADE,
        related_name="temperature_config",
    )


class TopPExperimentConfig(DecimalExperimentParameterConfig):
    """Store sampled top-p values for one experiment."""

    experiment_config = models.OneToOneField(
        ExperimentConfig,
        on_delete=models.CASCADE,
        related_name="top_p_config",
    )


class TopKExperimentConfig(IntegerExperimentParameterConfig):
    """Store sampled top-k values for one experiment."""

    experiment_config = models.OneToOneField(
        ExperimentConfig,
        on_delete=models.CASCADE,
        related_name="top_k_config",
    )


class FrequencyPenaltyExperimentConfig(DecimalExperimentParameterConfig):
    """Store sampled frequency penalty values for one experiment."""

    experiment_config = models.OneToOneField(
        ExperimentConfig,
        on_delete=models.CASCADE,
        related_name="frequency_penalty_config",
    )


class PresencePenaltyExperimentConfig(DecimalExperimentParameterConfig):
    """Store sampled presence penalty values for one experiment."""

    experiment_config = models.OneToOneField(
        ExperimentConfig,
        on_delete=models.CASCADE,
        related_name="presence_penalty_config",
    )


EXPERIMENT_PARAMETER_CONFIG_MAP = {
    ParameterSamplingSpec.ParameterName.TEMPERATURE: {
        "model": TemperatureExperimentConfig,
        "related_name": "temperature_config",
        "value_type": ParameterSamplingSpec.ValueType.FLOAT,
    },
    ParameterSamplingSpec.ParameterName.TOP_P: {
        "model": TopPExperimentConfig,
        "related_name": "top_p_config",
        "value_type": ParameterSamplingSpec.ValueType.FLOAT,
    },
    ParameterSamplingSpec.ParameterName.TOP_K: {
        "model": TopKExperimentConfig,
        "related_name": "top_k_config",
        "value_type": ParameterSamplingSpec.ValueType.INTEGER,
    },
    ParameterSamplingSpec.ParameterName.FREQUENCY_PENALTY: {
        "model": FrequencyPenaltyExperimentConfig,
        "related_name": "frequency_penalty_config",
        "value_type": ParameterSamplingSpec.ValueType.FLOAT,
    },
    ParameterSamplingSpec.ParameterName.PRESENCE_PENALTY: {
        "model": PresencePenaltyExperimentConfig,
        "related_name": "presence_penalty_config",
        "value_type": ParameterSamplingSpec.ValueType.FLOAT,
    },
}
