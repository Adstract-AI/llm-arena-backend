from rest_framework import status

from common.exceptions.general_exceptions import GeneralException


class LLMInferenceException(GeneralException):
    """Raised when model inference fails in the arena service layer."""

    status_code = status.HTTP_502_BAD_GATEWAY
    default_detail = "LLM inference failed."
    default_code = "llm_inference_failed"


class UnsupportedLLMProviderException(LLMInferenceException):
    """Raised when the service cannot route a model to a supported provider."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Unsupported LLM provider."
    default_code = "unsupported_llm_provider"


class MissingLLMConfigurationException(LLMInferenceException):
    """Raised when the runtime is missing required provider configuration."""

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = "Missing LLM provider configuration."
    default_code = "missing_llm_configuration"


class LLMModelNotFoundException(LLMInferenceException):
    """Raised when a requested LLM model does not exist in the arena catalog."""

    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "LLM model not found."
    default_code = "llm_model_not_found"


class InactiveLLMModelException(LLMInferenceException):
    """Raised when a requested LLM model exists but is disabled for inference."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "LLM model is inactive."
    default_code = "inactive_llm_model"
