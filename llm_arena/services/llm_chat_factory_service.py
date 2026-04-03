from langchain_anthropic import ChatAnthropic
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from common.abstract import AbstractService
from helpers.env_variables import (
    ANTHROPIC_API_KEY,
    FINKI_BASE_URL,
    GOOGLE_API_KEY,
    LLM_REQUEST_TIMEOUT_SECONDS,
    OPENAI_API_KEY,
)
from llm_arena.exceptions import MissingLLMConfigurationException, UnsupportedLLMProviderException
from llm_arena.models import LLMModel
from llm_arena.services.chat_finki import ChatFinki


class LLMChatFactoryService(AbstractService):
    """Create provider-specific LangChain chat model clients for arena inference."""

    def build_chat_model(
        self,
        model: LLMModel,
        generation_config: dict[str, int | float] | None = None,
    ) -> BaseChatModel:
        """
        Build the LangChain chat model for the resolved provider.

        Args:
            model: Catalog model whose provider and runtime configuration should be used.
            generation_config: Optional runtime sampling parameters.

        Returns:
            BaseChatModel: A configured LangChain chat model instance.

        Raises:
            MissingLLMConfigurationException: If credentials are missing.
            UnsupportedLLMProviderException: If the provider is unsupported.
        """
        provider_name = model.provider_name
        model_name = model.external_model_id
        sanitized_generation_config = self._sanitize_generation_config(
            model=model,
            generation_config=generation_config,
        )

        if provider_name == "openai":
            return self._build_openai_chat_model(model_name, sanitized_generation_config)

        if provider_name == "anthropic":
            return self._build_anthropic_chat_model(model_name, sanitized_generation_config)

        if provider_name == "google":
            return self._build_google_chat_model(model_name, sanitized_generation_config)

        if provider_name == "finki":
            return ChatFinki(
                model_name=model_name,
                base_url=FINKI_BASE_URL,
                timeout_seconds=LLM_REQUEST_TIMEOUT_SECONDS,
                generation_config=sanitized_generation_config,
            )

        raise UnsupportedLLMProviderException(detail=f"Provider '{provider_name}' is not supported.")

    def _build_openai_chat_model(
        self,
        model_name: str,
        generation_config: dict[str, int | float] | None,
    ) -> BaseChatModel:
        """Create the LangChain OpenAI chat model client."""
        if not OPENAI_API_KEY:
            raise MissingLLMConfigurationException(detail="OPENAI_API_KEY is not configured.")

        return ChatOpenAI(
            model=model_name,
            api_key=OPENAI_API_KEY,
            timeout=LLM_REQUEST_TIMEOUT_SECONDS,
            **(generation_config or {}),
        )

    def _build_anthropic_chat_model(
        self,
        model_name: str,
        generation_config: dict[str, int | float] | None,
    ) -> BaseChatModel:
        """Create the LangChain Anthropic chat model client."""
        if not ANTHROPIC_API_KEY:
            raise MissingLLMConfigurationException(detail="ANTHROPIC_API_KEY is not configured.")

        return ChatAnthropic(
            model_name=model_name,
            api_key=ANTHROPIC_API_KEY,
            timeout=LLM_REQUEST_TIMEOUT_SECONDS,
            **(generation_config or {}),
        )

    def _build_google_chat_model(
        self,
        model_name: str,
        generation_config: dict[str, int | float] | None,
    ) -> BaseChatModel:
        """Create the LangChain Google Gemini chat model client."""
        if not GOOGLE_API_KEY:
            raise MissingLLMConfigurationException(detail="GOOGLE_API_KEY is not configured.")

        return ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=GOOGLE_API_KEY,
            timeout=LLM_REQUEST_TIMEOUT_SECONDS,
            **(generation_config or {}),
        )

    def _sanitize_generation_config(
        self,
        model: LLMModel,
        generation_config: dict[str, int | float] | None,
    ) -> dict[str, int | float]:
        """
        Remove unsupported and null generation parameters before provider client creation.

        Args:
            model: Catalog model whose support flags determine valid generation parameters.
            generation_config: Raw runtime generation config.

        Returns:
            dict[str, int | float]: Provider kwargs safe for this model.
        """
        if not generation_config:
            return {}

        supported_parameters = {
            parameter_name
            for parameter_name, support_enabled in {
                "temperature": model.supports_temperature,
                "top_p": model.supports_top_p,
                "top_k": model.supports_top_k,
                "frequency_penalty": model.supports_frequency_penalty,
                "presence_penalty": model.supports_presence_penalty,
            }.items()
            if support_enabled
        }

        return {
            key: value
            for key, value in generation_config.items()
            if key in supported_parameters and value is not None
        }
