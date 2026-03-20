from __future__ import annotations

from typing import Any

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
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
from llm_arena.exceptions import (
    LLMInferenceException,
    MissingLLMConfigurationException,
    UnsupportedLLMProviderException,
)
from llm_arena.models import LLMModel
from llm_arena.services.chat_finki import ChatFinki
from llm_arena.services.llm_content_service import LLMContentService
from llm_arena.services.llm_model_service import LLMModelService


class ArenaInferenceService(AbstractService):
    """Route prompt inference to the correct LangChain chat model implementation."""

    content_service = LLMContentService()
    llm_model_service = LLMModelService()

    def generate_response_details(
        self,
        model: LLMModel,
        prompt: str,
        system_prompt: str | None = None,
    ) -> dict[str, Any]:
        """
        Generate a response and normalized metadata for a catalog model.

        Args:
            model: Catalog model instance to invoke.
            prompt: The user prompt to send to the model.
            system_prompt: Optional system instruction prepended to the message list.

        Returns:
            dict[str, Any]: Response text and normalized provider metadata for persistence.

        Raises:
            MissingLLMConfigurationException: If provider credentials are missing.
            UnsupportedLLMProviderException: If the model cannot be routed to a supported provider.
            LLMInferenceException: If the provider call fails.
        """
        normalized_prompt = prompt.strip()
        if not normalized_prompt:
            raise LLMInferenceException(detail="A prompt is required for inference.")

        runtime_model_name = self.llm_model_service.get_runtime_model_name(model)
        provider_name = self.llm_model_service.get_provider_name(model)
        chat_model = self._build_chat_model(provider_name=provider_name, model_name=runtime_model_name)

        messages: list[BaseMessage] = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt.strip()))
        messages.append(HumanMessage(content=normalized_prompt))

        try:
            response = chat_model.invoke(messages)
        except Exception as exc:
            raise LLMInferenceException(detail=f"Inference failed for model '{runtime_model_name}'.") from exc

        additional_kwargs = getattr(response, "additional_kwargs", {}) or {}
        response_metadata = getattr(response, "response_metadata", {}) or {}
        usage = additional_kwargs.get("usage") or response_metadata.get("token_usage") or response_metadata.get("usage") or {}

        return {
            "response_text": self.content_service.extract_response_content(response.content),
            "finish_reason": additional_kwargs.get("finish_reason") or response_metadata.get("finish_reason", ""),
            "prompt_tokens": usage.get("prompt_tokens"),
            "completion_tokens": usage.get("completion_tokens"),
            "total_tokens": usage.get("total_tokens"),
            "raw_metadata": {
                "additional_kwargs": additional_kwargs,
                "response_metadata": response_metadata,
            },
        }

    def generate_response(
        self,
        model: LLMModel,
        prompt: str,
        system_prompt: str | None = None,
    ) -> str:
        """
        Generate a text response for a prompt using the requested model.

        Args:
            model: Catalog model instance to invoke.
            prompt: The user prompt to send to the model.
            system_prompt: Optional system instruction prepended to the message list.

        Returns:
            The text content returned by the model.

        Raises:
            MissingLLMConfigurationException: If provider credentials are missing.
            UnsupportedLLMProviderException: If the model cannot be routed to a supported provider.
            LLMInferenceException: If the provider call fails.
        """
        return self.generate_response_details(
            model=model,
            prompt=prompt,
            system_prompt=system_prompt,
        )["response_text"]

    def _build_chat_model(self, provider_name: str, model_name: str) -> BaseChatModel:
        """
        Build the LangChain chat model for the resolved provider.

        Args:
            provider_name: Normalized provider name.
            model_name: Provider-facing model identifier.

        Returns:
            A configured LangChain chat model instance.

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

    def _build_openai_chat_model(self, model_name: str) -> BaseChatModel:
        """Create the LangChain OpenAI chat model client."""
        if not OPENAI_API_KEY:
            raise MissingLLMConfigurationException(detail="OPENAI_API_KEY is not configured.")

        return ChatOpenAI(
            model=model_name,
            api_key=OPENAI_API_KEY,
            timeout=LLM_REQUEST_TIMEOUT_SECONDS,
        )

    def _build_anthropic_chat_model(self, model_name: str) -> BaseChatModel:
        """Create the LangChain Anthropic chat model client."""
        if not ANTHROPIC_API_KEY:
            raise MissingLLMConfigurationException(detail="ANTHROPIC_API_KEY is not configured.")

        return ChatAnthropic(
            model_name=model_name,
            api_key=ANTHROPIC_API_KEY,
            timeout=LLM_REQUEST_TIMEOUT_SECONDS,
        )

    def _build_google_chat_model(self, model_name: str) -> BaseChatModel:
        """Create the LangChain Google Gemini chat model client."""
        if not GOOGLE_API_KEY:
            raise MissingLLMConfigurationException(detail="GOOGLE_API_KEY is not configured.")

        return ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=GOOGLE_API_KEY,
            timeout=LLM_REQUEST_TIMEOUT_SECONDS,
        )
