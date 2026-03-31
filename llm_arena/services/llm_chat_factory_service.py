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
from llm_arena.services.chat_finki import ChatFinki


class LLMChatFactoryService(AbstractService):
    """Create provider-specific LangChain chat model clients for arena inference."""

    OPENAI_SUPPORTED_PARAMETERS = frozenset(
        {"temperature", "top_p", "frequency_penalty", "presence_penalty"}
    )
    ANTHROPIC_SUPPORTED_PARAMETERS = frozenset({"temperature", "top_p", "top_k"})
    GOOGLE_SUPPORTED_PARAMETERS = frozenset({"temperature", "top_p", "top_k"})
    FINKI_SUPPORTED_PARAMETERS = frozenset(
        {"temperature", "top_p", "top_k", "frequency_penalty", "presence_penalty"}
    )

    def build_chat_model(
        self,
        provider_name: str,
        model_name: str,
        generation_config: dict[str, int | float] | None = None,
    ) -> BaseChatModel:
        """
        Build the LangChain chat model for the resolved provider.

        Args:
            provider_name: Normalized provider name.
            model_name: Provider-facing model identifier.
            generation_config: Optional runtime sampling parameters.

        Returns:
            BaseChatModel: A configured LangChain chat model instance.

        Raises:
            MissingLLMConfigurationException: If credentials are missing.
            UnsupportedLLMProviderException: If the provider is unsupported.
        """
        if provider_name == "openai":
            return self._build_openai_chat_model(model_name, generation_config)

        if provider_name == "anthropic":
            return self._build_anthropic_chat_model(model_name, generation_config)

        if provider_name == "google":
            return self._build_google_chat_model(model_name, generation_config)

        if provider_name == "finki":
            return ChatFinki(
                model_name=model_name,
                base_url=FINKI_BASE_URL,
                timeout_seconds=LLM_REQUEST_TIMEOUT_SECONDS,
                generation_config=self._filter_generation_config(
                    generation_config=generation_config,
                    supported_parameters=self.FINKI_SUPPORTED_PARAMETERS,
                ),
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
            **self._filter_generation_config(
                generation_config=generation_config,
                supported_parameters=self.OPENAI_SUPPORTED_PARAMETERS,
            ),
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
            **self._filter_generation_config(
                generation_config=generation_config,
                supported_parameters=self.ANTHROPIC_SUPPORTED_PARAMETERS,
            ),
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
            **self._filter_generation_config(
                generation_config=generation_config,
                supported_parameters=self.GOOGLE_SUPPORTED_PARAMETERS,
            ),
        )

    @staticmethod
    def _filter_generation_config(
        generation_config: dict[str, int | float] | None,
        supported_parameters: frozenset[str],
    ) -> dict[str, int | float]:
        """
        Remove unsupported and null generation parameters before provider client creation.

        Args:
            generation_config: Raw runtime generation config.
            supported_parameters: Parameter names accepted by the selected provider.

        Returns:
            dict[str, int | float]: Filtered generation kwargs safe for provider construction.
        """
        if not generation_config:
            return {}

        return {
            key: value
            for key, value in generation_config.items()
            if key in supported_parameters and value is not None
        }
