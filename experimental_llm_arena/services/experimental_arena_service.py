from __future__ import annotations

import random
from decimal import Decimal
from typing import Any

from common.abstract import AbstractService
from experimental_llm_arena.exceptions import (
    ExperimentalArenaIncompatibleModelsException,
    ExperimentalArenaMissingSamplingSpecException,
    ExperimentalArenaSamplingException,
)
from experimental_llm_arena.models import ExperimentConfig, ParameterSamplingSpec
from llm_arena.models import ArenaBattle, LLMModel
from llm_arena.services.arena_service import ArenaService
from llm_arena.services.llm_model_service import LLMModelService


class ExperimentalArenaService(AbstractService):
    """Validate, sample, and start experiment-configured arena battles."""

    llm_model_service = LLMModelService()
    arena_service = ArenaService()

    SAME_MODEL_MAX_RESAMPLES = 25
    FLOAT_QUANTIZER = Decimal("0.0001")
    PARAMETER_SUPPORT_FIELD_MAP = {
        ParameterSamplingSpec.ParameterName.TEMPERATURE: "supports_temperature",
        ParameterSamplingSpec.ParameterName.TOP_P: "supports_top_p",
        ParameterSamplingSpec.ParameterName.TOP_K: "supports_top_k",
        ParameterSamplingSpec.ParameterName.FREQUENCY_PENALTY: "supports_frequency_penalty",
        ParameterSamplingSpec.ParameterName.PRESENCE_PENALTY: "supports_presence_penalty",
    }

    def create_battle(
        self,
        prompt: str,
        model_mode: str,
        share_values_across_models: bool | None,
        parameters: dict[str, dict[str, Any]],
    ) -> ArenaBattle:
        """
        Start a new experimental battle and persist the sampled experiment configuration.

        Args:
            prompt: Initial user prompt for the battle.
            model_mode: Same-model or different-model experiment mode.
            share_values_across_models: Whether different-model experiments reuse sampled values.
            parameters: Enabled parameter flags and chosen distributions.

        Returns:
            ArenaBattle: Newly created battle with its linked experiment config.

        Raises:
            ExperimentalArenaIncompatibleModelsException: If no compatible active model pool exists.
            ExperimentalArenaMissingSamplingSpecException: If required sampling specs are missing.
            ExperimentalArenaSamplingException: If same-model slot sampling cannot create a real comparison.
        """
        enabled_parameter_names = self._get_enabled_parameter_names(parameters)
        sampling_specs = self._get_sampling_specs(enabled_parameter_names)
        compatible_models = self._get_compatible_models(enabled_parameter_names)
        model_a, model_b = self._select_models(
            compatible_models=compatible_models,
            model_mode=model_mode,
        )
        experiment_config_fields = self._build_experiment_config_fields(
            model_mode=model_mode,
            share_values_across_models=share_values_across_models,
            parameters=parameters,
            sampling_specs=sampling_specs,
        )

        return self.arena_service.create_battle_with_models(
            prompt=prompt,
            model_a=model_a,
            model_b=model_b,
            experiment_config_fields=experiment_config_fields,
        )

    def _get_enabled_parameter_names(self, parameters: dict[str, dict[str, Any]]) -> list[str]:
        """
        Return the subset of experimental parameter names enabled by the request.

        Args:
            parameters: Request parameter config keyed by parameter name.

        Returns:
            list[str]: Enabled parameter names.
        """
        return [
            parameter_name
            for parameter_name, parameter_config in parameters.items()
            if parameter_config["enabled"]
        ]

    def _get_sampling_specs(
        self,
        enabled_parameter_names: list[str],
    ) -> dict[str, ParameterSamplingSpec]:
        """
        Load the sampling spec rows required for the enabled experimental parameters.

        Args:
            enabled_parameter_names: Enabled experimental parameter names.

        Returns:
            dict[str, ParameterSamplingSpec]: Sampling specs keyed by parameter name.

        Raises:
            ExperimentalArenaMissingSamplingSpecException: If any enabled parameter lacks a DB spec row.
        """
        sampling_specs = {
            spec.parameter_name: spec
            for spec in ParameterSamplingSpec.objects.filter(
                parameter_name__in=enabled_parameter_names,
            )
        }
        missing_parameter_names = sorted(
            set(enabled_parameter_names) - set(sampling_specs.keys())
        )
        if missing_parameter_names:
            raise ExperimentalArenaMissingSamplingSpecException(
                detail=(
                    "Missing sampling specs for parameter(s): "
                    + ", ".join(missing_parameter_names)
                    + "."
                )
            )
        return sampling_specs

    def _get_compatible_models(self, enabled_parameter_names: list[str]) -> list[LLMModel]:
        """
        Filter active models down to those supporting all requested parameters.

        Args:
            enabled_parameter_names: Enabled experimental parameter names.

        Returns:
            list[LLMModel]: Compatible active model pool.

        Raises:
            ExperimentalArenaIncompatibleModelsException: If no compatible model remains.
        """
        if not enabled_parameter_names:
            raise ExperimentalArenaIncompatibleModelsException(
                detail="At least one experimental parameter must be enabled."
            )

        compatible_models = []
        for model in self.llm_model_service.get_active_models():
            if all(
                getattr(model, self.PARAMETER_SUPPORT_FIELD_MAP[parameter_name])
                for parameter_name in enabled_parameter_names
            ):
                compatible_models.append(model)

        if not compatible_models:
            raise ExperimentalArenaIncompatibleModelsException()
        return compatible_models

    def _select_models(
        self,
        compatible_models: list[LLMModel],
        model_mode: str,
    ) -> tuple[LLMModel, LLMModel]:
        """
        Randomly choose battle models from the compatible active pool.

        Args:
            compatible_models: Active models that support the requested experiment.
            model_mode: Same-model or different-model experiment mode.

        Returns:
            tuple[LLMModel, LLMModel]: Models assigned to slots A and B.

        Raises:
            ExperimentalArenaIncompatibleModelsException: If the compatible pool is too small.
        """
        if model_mode == ExperimentConfig.ModelMode.SAME_MODEL:
            return_model = random.choice(compatible_models)
            return return_model, return_model

        if len(compatible_models) < 2:
            raise ExperimentalArenaIncompatibleModelsException(
                detail="At least two compatible active models are required for this experiment."
            )

        selected_models = random.sample(compatible_models, 2)
        return selected_models[0], selected_models[1]

    def _build_experiment_config_fields(
        self,
        model_mode: str,
        share_values_across_models: bool | None,
        parameters: dict[str, dict[str, Any]],
        sampling_specs: dict[str, ParameterSamplingSpec],
    ) -> dict[str, Any]:
        """
        Build the persisted experiment configuration field payload for one battle.

        Args:
            model_mode: Same-model or different-model experiment mode.
            share_values_across_models: Whether different-model slots reuse sampled values.
            parameters: Request parameter config keyed by parameter name.
            sampling_specs: Loaded sampling specs keyed by parameter name.

        Returns:
            dict[str, Any]: Model fields for ExperimentConfig creation.

        Raises:
            ExperimentalArenaSamplingException: If same-model sampling cannot produce distinct slots.
        """
        fields: dict[str, Any] = {
            "model_mode": model_mode,
            "share_values_across_models": share_values_across_models,
        }

        if model_mode == ExperimentConfig.ModelMode.SAME_MODEL:
            sampled_values = self._sample_same_model_values(
                parameters=parameters,
                sampling_specs=sampling_specs,
            )
        else:
            sampled_values = self._sample_different_model_values(
                parameters=parameters,
                sampling_specs=sampling_specs,
                share_values_across_models=bool(share_values_across_models),
            )

        for parameter_name, parameter_config in parameters.items():
            fields[f"{parameter_name}_enabled"] = parameter_config["enabled"]
            fields[f"{parameter_name}_distribution"] = parameter_config.get("distribution")
            fields[f"{parameter_name}_value_a"] = sampled_values[parameter_name]["value_a"]
            fields[f"{parameter_name}_value_b"] = sampled_values[parameter_name]["value_b"]

        return fields

    def _sample_same_model_values(
        self,
        parameters: dict[str, dict[str, Any]],
        sampling_specs: dict[str, ParameterSamplingSpec],
    ) -> dict[str, dict[str, Any]]:
        """
        Sample two slot configurations for a same-model experiment until they differ.

        Args:
            parameters: Request parameter config keyed by parameter name.
            sampling_specs: Loaded sampling specs keyed by parameter name.

        Returns:
            dict[str, dict[str, Any]]: Persistable per-parameter slot values.

        Raises:
            ExperimentalArenaSamplingException: If distinct slot values cannot be produced.
        """
        for _ in range(self.SAME_MODEL_MAX_RESAMPLES):
            sampled_values = self._sample_different_model_values(
                parameters=parameters,
                sampling_specs=sampling_specs,
                share_values_across_models=False,
            )
            if self._has_any_slot_difference(sampled_values, parameters):
                return sampled_values

        raise ExperimentalArenaSamplingException()

    def _sample_different_model_values(
        self,
        parameters: dict[str, dict[str, Any]],
        sampling_specs: dict[str, ParameterSamplingSpec],
        share_values_across_models: bool,
    ) -> dict[str, dict[str, Any]]:
        """
        Sample per-slot parameter values for a different-model experiment.

        Args:
            parameters: Request parameter config keyed by parameter name.
            sampling_specs: Loaded sampling specs keyed by parameter name.
            share_values_across_models: Whether both slots should reuse the same sampled value.

        Returns:
            dict[str, dict[str, Any]]: Persistable per-parameter slot values.
        """
        sampled_values: dict[str, dict[str, Any]] = {}

        for parameter_name, parameter_config in parameters.items():
            if not parameter_config["enabled"]:
                sampled_values[parameter_name] = {
                    "value_a": None,
                    "value_b": None,
                }
                continue

            spec = sampling_specs[parameter_name]
            distribution = parameter_config["distribution"]
            value_a = self._sample_parameter_value(spec=spec, distribution=distribution)
            value_b = (
                value_a
                if share_values_across_models
                else self._sample_parameter_value(spec=spec, distribution=distribution)
            )
            sampled_values[parameter_name] = {
                "value_a": value_a,
                "value_b": value_b,
            }

        return sampled_values

    def _sample_parameter_value(
        self,
        spec: ParameterSamplingSpec,
        distribution: str,
    ) -> Decimal | int:
        """
        Sample one parameter value according to the requested distribution family.

        Args:
            spec: Sampling spec row for the requested parameter.
            distribution: Distribution family selected by the request.

        Returns:
            Decimal | int: Normalized sampled value ready for persistence.
        """
        minimum_value = float(spec.minimum_value)
        maximum_value = float(spec.maximum_value)
        raw_value: float

        if distribution == ExperimentConfig.DistributionType.UNIFORM:
            raw_value = random.uniform(float(spec.uniform_min), float(spec.uniform_max))
        elif distribution == ExperimentConfig.DistributionType.NORMAL:
            raw_value = random.gauss(float(spec.normal_mean), float(spec.normal_std))
        else:
            beta_value = random.betavariate(float(spec.beta_alpha), float(spec.beta_beta))
            raw_value = minimum_value + (beta_value * (maximum_value - minimum_value))

        clipped_value = min(max(raw_value, minimum_value), maximum_value)
        if spec.value_type == ParameterSamplingSpec.ValueType.INTEGER:
            return int(round(clipped_value))

        return Decimal(str(clipped_value)).quantize(self.FLOAT_QUANTIZER)

    @staticmethod
    def _has_any_slot_difference(
        sampled_values: dict[str, dict[str, Any]],
        parameters: dict[str, dict[str, Any]],
    ) -> bool:
        """
        Check whether two slot configurations differ on any enabled parameter.

        Args:
            sampled_values: Persistable per-parameter slot values.
            parameters: Request parameter config keyed by parameter name.

        Returns:
            bool: True when slot A and B differ on at least one enabled parameter.
        """
        for parameter_name, parameter_config in parameters.items():
            if not parameter_config["enabled"]:
                continue
            if sampled_values[parameter_name]["value_a"] != sampled_values[parameter_name]["value_b"]:
                return True
        return False
