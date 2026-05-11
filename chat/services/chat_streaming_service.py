from __future__ import annotations

import json
import logging
from typing import Any
from uuid import UUID

from common.abstract import AbstractService
from chat.exceptions import ChatInferenceFailedException
from chat.services.chat_service import ChatService
from llm_arena.exceptions import LLMInferenceException
from llm_arena.services.inference_service import ArenaInferenceService

logger = logging.getLogger(__name__)


class ChatStreamingService(AbstractService):
    """Stream a single chat assistant response over server-sent events."""

    chat_service = ChatService()
    inference_service = ArenaInferenceService()

    def stream_message(
        self,
        provider_name: str,
        model_name: str,
        message: str,
        session_id: UUID | None = None,
    ):
        """
        Persist the user message, stream the assistant response, then persist the final assistant message.

        Args:
            provider_name: Requested provider identifier from the API payload.
            model_name: Requested model identifier from the API payload.
            message: User prompt content.
            session_id: Existing session UUID for follow-up turns.
        """
        session, llm_model, normalized_message, history_messages = self.chat_service.prepare_message(
            provider_name=provider_name,
            model_name=model_name,
            message=message,
            session_id=session_id,
        )

        yield self._format_sse(
            "session_created" if session_id is None else "session_loaded",
            {
                "session_id": str(session.id),
                "model_name": llm_model.name,
                "provider_name": llm_model.provider.name,
            },
        )
        yield self._format_sse(
            "response_started",
            {
                "session_id": str(session.id),
            },
        )

        response_text = ""
        try:
            completed_details: dict[str, Any] | None = None
            for stream_event in self.inference_service.stream_response_details_with_history(
                model=llm_model,
                history_messages=history_messages,
                prompt=normalized_message,
            ):
                if stream_event["type"] == "delta":
                    response_text += stream_event["text"]
                    yield self._format_sse(
                        "response_delta",
                        {
                            "text": stream_event["text"],
                        },
                    )
                    continue
                completed_details = stream_event

            if completed_details is None:
                raise ChatInferenceFailedException()

            final_response_text = completed_details["response_text"] or response_text
            response_details = completed_details | {"response_text": final_response_text}
            self.chat_service.persist_assistant_message(
                session=session,
                response_details=response_details,
            )
            completed_payload = {
                "session_id": str(session.id),
                "response_text": final_response_text,
                "model_name": llm_model.name,
                "provider_name": llm_model.provider.name,
                "finish_reason": response_details["finish_reason"] or None,
                "prompt_tokens": response_details["prompt_tokens"],
                "completion_tokens": response_details["completion_tokens"],
                "total_tokens": response_details["total_tokens"],
                "latency_ms": response_details.get("latency_ms"),
            }
            yield self._format_sse("response_completed", completed_payload)
            yield self._format_sse(
                "done",
                {
                    "session_id": str(session.id),
                    "response_text": final_response_text,
                    "model_name": llm_model.name,
                    "provider_name": llm_model.provider.name,
                },
            )
        except LLMInferenceException as exc:
            logger.exception(
                f"Streaming chat inference failed for session {session.id} and model {llm_model.name}"
            )
            error_message = str(exc.detail)
            self.chat_service.persist_failed_assistant_message(
                session=session,
                error_message=error_message,
            )
            yield self._format_sse(
                "response_failed",
                {
                    "session_id": str(session.id),
                    "error_message": error_message,
                },
            )
        except Exception:
            logger.exception(
                f"Unexpected streaming chat inference failure for session {session.id} "
                f"and model {llm_model.name}"
            )
            error_message = "Chat inference failed."
            self.chat_service.persist_failed_assistant_message(
                session=session,
                error_message=error_message,
            )
            yield self._format_sse(
                "response_failed",
                {
                    "session_id": str(session.id),
                    "error_message": error_message,
                },
            )

    @staticmethod
    def _format_sse(event_name: str, payload: dict[str, Any]) -> str:
        return f"event: {event_name}\ndata: {json.dumps(payload, default=str)}\n\n"
