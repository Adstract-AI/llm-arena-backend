from __future__ import annotations

from typing import Any

import requests
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from helpers.env_variables import FINKI_BASE_URL, LLM_REQUEST_TIMEOUT_SECONDS


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
        content = self._extract_response_content(message_data.get("content", ""))

        return ChatResult(
            generations=[
                ChatGeneration(
                    message=AIMessage(
                        content=content,
                        additional_kwargs={
                            "finish_reason": choice_data.get("finish_reason"),
                            "raw_response": response_data,
                        },
                    )
                )
            ],
            llm_output={"raw_response": response_data},
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
            "content": ChatFinki._stringify_content(message.content),
        }

    @staticmethod
    def _stringify_content(content: Any) -> str:
        """Normalize message content into plain text for the Macedonian endpoint."""
        if isinstance(content, str):
            return content

        if isinstance(content, list):
            text_parts = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text_parts.append(str(item.get("text", "")))
                elif isinstance(item, str):
                    text_parts.append(item)
            return "\n".join(part for part in text_parts if part)

        return str(content)

    @staticmethod
    def _extract_response_content(content: Any) -> str:
        """Normalize completion content from either string or content-block formats."""
        return ChatFinki._stringify_content(content)
