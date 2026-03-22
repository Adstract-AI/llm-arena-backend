from __future__ import annotations

from typing import Any

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

from common.abstract import AbstractService
from llm_arena.exceptions import LLMInferenceException
from llm_arena.models import LLMModel
from llm_arena.services.llm_chat_factory_service import LLMChatFactoryService
from llm_arena.services.llm_content_service import LLMContentService


class ArenaInferenceService(AbstractService):
    """Route prompt inference to the correct LangChain chat model implementation."""

    llm_chat_factory_service = LLMChatFactoryService()
    content_service = LLMContentService()

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

        runtime_model_name = model.external_model_id
        provider_name = model.provider_name
        chat_model = self.llm_chat_factory_service.build_chat_model(
            provider_name=provider_name,
            model_name=runtime_model_name,
        )

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
