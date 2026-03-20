from __future__ import annotations

from typing import Any

import requests
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from helpers.env_variables import FINKI_BASE_URL, LLM_REQUEST_TIMEOUT_SECONDS
from llm_arena.services.llm_content_service import LLMContentService


class ChatFinki(BaseChatModel):
    """LangChain-compatible chat model for the FINKI Macedonian endpoint."""

    model_name: str
    base_url: str = FINKI_BASE_URL
    timeout_seconds: int = LLM_REQUEST_TIMEOUT_SECONDS

    @property
    def _llm_type(self) -> str:
        return "finki_openai_compatible"

    def _generate(
            self,
            messages: list[BaseMessage],
            stop: list[str] | None = None,
            run_manager: Any | None = None,
            **kwargs: Any,
    ) -> ChatResult:
        payload: dict[str, Any] = {
            "model": self.model_name,
            "messages": [self._serialize_message(message) for message in messages],
        }
        if stop:
            payload["stop"] = stop

        response = requests.post(
            f"{self.base_url.rstrip('/')}/chat/completions",
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()

        response_data = response.json()
        choice_data = response_data["choices"][0]
        message_data = choice_data["message"]
        content = LLMContentService.extract_response_content(message_data.get("content", ""))

        return ChatResult(
            generations=[
                ChatGeneration(
                    message=AIMessage(
                        content=content,
                        additional_kwargs={
                            "finish_reason": choice_data.get("finish_reason"),
                            "response_id": response_data.get("id"),
                            "response_model": response_data.get("model"),
                            "system_fingerprint": response_data.get("system_fingerprint"),
                            "usage": response_data.get("usage", {}),
                            "raw_response": response_data,
                        },
                    )
                )
            ],
            llm_output={
                "response_id": response_data.get("id"),
                "created": response_data.get("created"),
                "model": response_data.get("model"),
                "system_fingerprint": response_data.get("system_fingerprint"),
                "usage": response_data.get("usage", {}),
                "raw_response": response_data,
            },
        )

    @staticmethod
    def _serialize_message(message: BaseMessage) -> dict[str, str]:
        """Convert LangChain messages into the OpenAI-compatible payload shape."""
        role_map = {
            "human": "user",
            "system": "system",
            "ai": "assistant",
        }
        return {
            "role": role_map.get(message.type, "user"),
            "content": LLMContentService.stringify_content(message.content),
        }
