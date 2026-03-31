from rest_framework import serializers

from experimental_llm_arena.models import ExperimentConfig


class ExperimentalParameterRequestSerializer(serializers.Serializer):
    enabled = serializers.BooleanField()
    distribution = serializers.ChoiceField(
        choices=ExperimentConfig.DistributionType.choices,
        allow_null=True,
        required=False,
    )

    def validate(self, attrs: dict) -> dict:
        enabled = attrs["enabled"]
        distribution = attrs.get("distribution")

        if enabled and distribution is None:
            raise serializers.ValidationError(
                {"distribution": "A distribution is required when the parameter is enabled."}
            )

        if not enabled and distribution is not None:
            raise serializers.ValidationError(
                {"distribution": "Disabled parameters must not provide a distribution."}
            )

        return attrs


class ExperimentalParameterSetRequestSerializer(serializers.Serializer):
    temperature = ExperimentalParameterRequestSerializer()
    top_p = ExperimentalParameterRequestSerializer()
    top_k = ExperimentalParameterRequestSerializer()
    frequency_penalty = ExperimentalParameterRequestSerializer()
    presence_penalty = ExperimentalParameterRequestSerializer()


class ExperimentalBattleCreateRequestSerializer(serializers.Serializer):
    prompt = serializers.CharField()
    model_mode = serializers.ChoiceField(choices=ExperimentConfig.ModelMode.choices)
    share_values_across_models = serializers.BooleanField(
        allow_null=True,
        required=False,
    )
    parameters = ExperimentalParameterSetRequestSerializer()

    def validate(self, attrs: dict) -> dict:
        model_mode = attrs["model_mode"]
        share_values_across_models = attrs.get("share_values_across_models")
        parameters = attrs["parameters"]

        if not any(parameter["enabled"] for parameter in parameters.values()):
            raise serializers.ValidationError(
                {"parameters": "At least one experimental parameter must be enabled."}
            )

        if model_mode == ExperimentConfig.ModelMode.SAME_MODEL and share_values_across_models is not None:
            raise serializers.ValidationError(
                {
                    "share_values_across_models": (
                        "This field must be null when the experiment uses the same model."
                    )
                }
            )

        if (
            model_mode == ExperimentConfig.ModelMode.DIFFERENT_MODELS
            and share_values_across_models is None
        ):
            raise serializers.ValidationError(
                {
                    "share_values_across_models": (
                        "This field is required when the experiment uses different models."
                    )
                }
            )

        return attrs

