from __future__ import annotations

from typing import Any, Sequence

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

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
            generation_config: dict[str, int | float] | None = None,
    ) -> dict[str, Any]:
        """
        Generate a response and normalized metadata for a catalog model.

        Args:
            model: Catalog model instance to invoke.
            prompt: The user prompt to send to the model.
            system_prompt: Optional system instruction prepended to the message list.
            generation_config: Optional runtime generation config for this request.

        Returns:
            dict[str, Any]: Response text and normalized provider metadata for persistence.

        Raises:
            MissingLLMConfigurationException: If provider credentials are missing.
            UnsupportedLLMProviderException: If the model cannot be routed to a supported provider.
            LLMInferenceException: If the provider call fails.
        """
        return self._generate_response_details(
            model=model,
            prompt=prompt,
            history_messages=None,
            system_prompt=system_prompt,
            generation_config=generation_config,
        )

    def generate_response_details_with_history(
            self,
            model: LLMModel,
            history_messages: Sequence[Any],
            prompt: str,
            system_prompt: str | None = None,
            generation_config: dict[str, int | float] | None = None,
    ) -> dict[str, Any]:
        """
        Generate a response using persisted conversation history plus the current prompt.

        Args:
            model: Catalog model instance to invoke.
            history_messages: Persisted prior messages used as chat memory.
            prompt: The user prompt to send to the model.
            system_prompt: Optional system instruction prepended to the message list.
            generation_config: Optional runtime generation config for this request.

        Returns:
            dict[str, Any]: Response text and normalized provider metadata for persistence.

        Raises:
            LLMInferenceException: If the provider call fails.
        """
        return self._generate_response_details(
            model=model,
            prompt=prompt,
            history_messages=history_messages,
            system_prompt=system_prompt,
            generation_config=generation_config,
        )

    def _generate_response_details(
            self,
            model: LLMModel,
            prompt: str,
            history_messages: Sequence[Any] | None,
            system_prompt: str | None,
            generation_config: dict[str, int | float] | None,
    ) -> dict[str, Any]:
        """
        Shared inference implementation for arena and chat flows.

        Args:
            model: Catalog model instance to invoke.
            prompt: The user prompt to send to the model.
            history_messages: Optional persisted prior messages used as chat memory.
            system_prompt: Optional system instruction prepended to the message list.
            generation_config: Optional runtime generation config for this request.

        Returns:
            dict[str, Any]: Response text and normalized provider metadata for persistence.

        Raises:
            LLMInferenceException: If the provider call fails.
        """
        normalized_prompt = prompt.strip()
        if not normalized_prompt:
            raise LLMInferenceException(detail="A prompt is required for inference.")

        runtime_model_name = model.external_model_id
        try:
            chat_model = self.llm_chat_factory_service.build_chat_model(
                provider_name=model.provider_name,
                model_name=runtime_model_name,
                generation_config=generation_config,
            )
            messages = self._build_messages(
                history_messages=history_messages,
                prompt=normalized_prompt,
                system_prompt=system_prompt,
            )
            response = chat_model.invoke(messages)
        except Exception as exc:
            raise LLMInferenceException(
                detail=f"Inference failed for model '{runtime_model_name}'."
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

    def _build_messages(self,
                        history_messages: Sequence[Any] | None,
                        prompt: str,
                        system_prompt: str | None,
                        ) -> list[BaseMessage]:
        """
        Build the LangChain message list for inference.

        Args:
            history_messages: Optional persisted chat history ordered oldest to newest.
            prompt: Current user prompt.
            system_prompt: Optional system instruction.

        Returns:
            list[BaseMessage]: Message list for provider invocation.
        """
        messages: list[BaseMessage] = []

        if system_prompt and system_prompt.strip():
            messages.append(SystemMessage(content=system_prompt.strip()))

        for history_message in history_messages or []:
            built_message = self._build_history_message(history_message)
            if built_message is not None:
                messages.append(built_message)

        messages.append(HumanMessage(content=prompt))
        return messages

    @staticmethod
    def _build_history_message(history_message: Any) -> BaseMessage | None:
        """
        Convert a persisted history message into its LangChain equivalent.

        Args:
            history_message: Persisted object exposing `role` and `content` attributes.

        Returns:
            BaseMessage | None: Converted LangChain message or None for unsupported roles.
        """
        role = str(getattr(history_message, "role", "")).strip().lower()
        content = getattr(history_message, "content", "")
        if role == "user":
            return HumanMessage(content=content)
        if role == "assistant":
            return AIMessage(content=content)
        if role == "system":
            return SystemMessage(content=content)
        return None
