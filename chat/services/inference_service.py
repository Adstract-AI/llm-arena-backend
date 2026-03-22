from __future__ import annotations

from typing import Any, Sequence

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from chat.exceptions import ChatInferenceFailedException
from chat.models import ChatMessage
from common.abstract import AbstractService
from llm_arena.models import LLMModel
from llm_arena.services.llm_chat_factory_service import LLMChatFactoryService
from llm_arena.services.llm_content_service import LLMContentService


class ChatInferenceService(AbstractService):
    """Run single-model chat inference with persisted session memory."""

    llm_chat_factory_service = LLMChatFactoryService()
    content_service = LLMContentService()

    def generate_response_details(
            self,
            model: LLMModel,
            history_messages: Sequence[ChatMessage],
            prompt: str,
            system_prompt: str | None = None,
    ) -> dict[str, Any]:
        """
        Generate one assistant response using historical chat memory and a new prompt.

        Args:
            model: Catalog model used for inference.
            history_messages: Persisted session messages already stored in the database.
            prompt: New user prompt for the current turn.
            system_prompt: Optional system instruction prepended to the messages list.

        Returns:
            dict[str, Any]: Response text and provider metadata for persistence.

        Raises:
            ChatInferenceFailedException: If inference cannot be completed.
        """
        normalized_prompt = prompt.strip()
        if not normalized_prompt:
            raise ChatInferenceFailedException(detail="A prompt is required for inference.")

        try:
            chat_model = self.llm_chat_factory_service.build_chat_model(
                provider_name=model.provider_name,
                model_name=model.external_model_id,
            )

            messages: list[BaseMessage] = self._build_messages(
                history_messages=history_messages,
                prompt=normalized_prompt,
                system_prompt=system_prompt,
            )
            response = chat_model.invoke(messages)
        except ChatInferenceFailedException:
            raise
        except Exception as exc:
            raise ChatInferenceFailedException(
                detail=f"Inference failed for model '{model.external_model_id}'."
            ) from exc

        additional_kwargs = getattr(response, "additional_kwargs", {}) or {}
        response_metadata = getattr(response, "response_metadata", {}) or {}
        usage = (
                additional_kwargs.get("usage")
                or response_metadata.get("token_usage")
                or response_metadata.get("usage")
                or {}
        )

        return {
            "response_text": self.content_service.extract_response_content(response.content),
            "finish_reason": additional_kwargs.get("finish_reason")
                             or response_metadata.get("finish_reason", ""),
            "prompt_tokens": usage.get("prompt_tokens"),
            "completion_tokens": usage.get("completion_tokens"),
            "total_tokens": usage.get("total_tokens"),
            "raw_metadata": {
                "additional_kwargs": additional_kwargs,
                "response_metadata": response_metadata,
            },
        }

    @staticmethod
    def _build_messages(
            history_messages: Sequence[ChatMessage],
            prompt: str,
            system_prompt: str | None,
    ) -> list[BaseMessage]:
        """
        Convert persisted chat history into LangChain messages and append the new prompt.

        Args:
            history_messages: Ordered historical chat messages.
            prompt: Current user prompt.
            system_prompt: Optional system instruction.

        Returns:
            list[BaseMessage]: Message list for provider invocation.
        """
        messages: list[BaseMessage] = []

        if system_prompt and system_prompt.strip():
            messages.append(SystemMessage(content=system_prompt.strip()))

        for history_message in history_messages:
            if history_message.role == ChatMessage.MessageRole.USER:
                messages.append(HumanMessage(content=history_message.content))
            elif history_message.role == ChatMessage.MessageRole.ASSISTANT:
                messages.append(AIMessage(content=history_message.content))

        messages.append(HumanMessage(content=prompt))
        return messages
