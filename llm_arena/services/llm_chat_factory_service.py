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

    def build_chat_model(self, provider_name: str, model_name: str) -> BaseChatModel:
        """
        Build the LangChain chat model for the resolved provider.

        Args:
            provider_name: Normalized provider name.
            model_name: Provider-facing model identifier.

        Returns:
            BaseChatModel: A configured LangChain chat model instance.

        Raises:
            MissingLLMConfigurationException: If credentials are missing.
            UnsupportedLLMProviderException: If the provider is unsupported.
        """
        if provider_name == "openai":
            return self._build_openai_chat_model(model_name)

        if provider_name == "anthropic":
            return self._build_anthropic_chat_model(model_name)

        if provider_name == "google":
            return self._build_google_chat_model(model_name)

        if provider_name == "finki":
            return ChatFinki(
                model_name=model_name,
                base_url=FINKI_BASE_URL,
                timeout_seconds=LLM_REQUEST_TIMEOUT_SECONDS,
            )

        raise UnsupportedLLMProviderException(detail=f"Provider '{provider_name}' is not supported.")

    @staticmethod
    def _build_openai_chat_model(model_name: str) -> BaseChatModel:
        """Create the LangChain OpenAI chat model client."""
        if not OPENAI_API_KEY:
            raise MissingLLMConfigurationException(detail="OPENAI_API_KEY is not configured.")

        return ChatOpenAI(
            model=model_name,
            api_key=OPENAI_API_KEY,
            timeout=LLM_REQUEST_TIMEOUT_SECONDS,
        )

    @staticmethod
    def _build_anthropic_chat_model(model_name: str) -> BaseChatModel:
        """Create the LangChain Anthropic chat model client."""
        if not ANTHROPIC_API_KEY:
            raise MissingLLMConfigurationException(detail="ANTHROPIC_API_KEY is not configured.")

        return ChatAnthropic(
            model_name=model_name,
            api_key=ANTHROPIC_API_KEY,
            timeout=LLM_REQUEST_TIMEOUT_SECONDS,
        )

    @staticmethod
    def _build_google_chat_model(model_name: str) -> BaseChatModel:
        """Create the LangChain Google Gemini chat model client."""
        if not GOOGLE_API_KEY:
            raise MissingLLMConfigurationException(detail="GOOGLE_API_KEY is not configured.")

        return ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=GOOGLE_API_KEY,
            timeout=LLM_REQUEST_TIMEOUT_SECONDS,
        )
