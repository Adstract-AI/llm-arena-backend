import logging
from typing import Any
from uuid import UUID

from django.db import transaction
from django.db.models import QuerySet

from accounts.services.auth_service import AuthService
from chat.exceptions import (
    ChatInferenceFailedException,
    ChatMessageValidationException,
    ChatSessionModelMismatchException,
    ChatSessionNotFoundException,
    InvalidChatProviderException,
)
from chat.models import ChatMessage, ChatSession
from common.abstract import AbstractService
from llm_arena.models import LLMModel
from llm_arena.exceptions import LLMInferenceException
from llm_arena.services.inference_service import ArenaInferenceService
from llm_arena.services.llm_model_service import LLMModelService

logger = logging.getLogger(__name__)


class ChatService(AbstractService):
    """Coordinate session management, memory retrieval, inference, and persistence for chat."""

    SUPPORTED_PROVIDER_NAME = "finki"
    MEMORY_WINDOW_SIZE = 20

    llm_model_service = LLMModelService()
    inference_service = ArenaInferenceService()
    auth_service = AuthService()

    def get_chat_supported_models(self) -> QuerySet[LLMModel]:
        """
        Return active models available for FINKI chat.

        Returns:
            QuerySet[LLMModel]: Active catalog models served by the finki provider.
        """
        return self.llm_model_service.get_active_models_by_provider(
            provider_name=self.SUPPORTED_PROVIDER_NAME,
        )

    @transaction.atomic
    def send_message(
            self,
            provider_name: str,
            model_name: str,
            message: str,
            session_id: UUID | None = None,
    ) -> dict[str, Any]:
        """
        Send a user message to the selected FINKI model and persist both chat turns.

        Args:
            provider_name: Requested provider identifier from the API payload.
            model_name: Requested model identifier from the API payload.
            message: User prompt content.
            session_id: Existing session UUID for follow-up turns.

        Returns:
            dict[str, Any]: Public API response payload for the new assistant reply.

        Raises:
            InvalidChatProviderException: If provider is not finki.
            ChatMessageValidationException: If the prompt is empty.
            ChatSessionNotFoundException: If session_id does not exist.
            ChatSessionModelMismatchException: If model does not match the session model.
            ChatInferenceFailedException: If the provider inference call fails.
        """
        normalized_provider_name = self._normalize_provider_name(provider_name)
        normalized_message = self._normalize_message(message)
        authenticated_user = self.auth_service.require_authenticated_user(
            detail="Authentication is required to use chat sessions."
        )

        llm_model = self.llm_model_service.get_model_by_name_for_provider(
            model_name=model_name,
            provider_name=normalized_provider_name,
            require_active=True,
        )
        session = self._resolve_session(
            session_id=session_id,
            llm_model=llm_model,
            user=authenticated_user,
        )
        history_messages = self._get_history_messages(
            session=session,
            limit=self.MEMORY_WINDOW_SIZE,
        )

        ChatMessage.objects.create(
            session=session,
            role=ChatMessage.MessageRole.USER,
            content=normalized_message,
        )

        try:
            response_details = self.inference_service.generate_response_details_with_history(
                model=llm_model,
                history_messages=history_messages,
                prompt=normalized_message,
            )
        except LLMInferenceException as exc:
            logger.exception(
                f"Chat inference failed for session {session.id} and model {llm_model.name}"
            )
            raise ChatInferenceFailedException(detail=str(exc.detail)) from exc

        ChatMessage.objects.create(
            session=session,
            role=ChatMessage.MessageRole.ASSISTANT,
            content=response_details["response_text"],
            error_message=None,
            finish_reason=response_details["finish_reason"],
            prompt_tokens=response_details["prompt_tokens"],
            completion_tokens=response_details["completion_tokens"],
            total_tokens=response_details["total_tokens"],
            raw_metadata=response_details["raw_metadata"],
        )

        return {
            "session_id": session.id,
            "response_text": response_details["response_text"],
            "model_name": llm_model.name,
            "provider_name": llm_model.provider.name,
        }

    def prepare_message(
            self,
            provider_name: str,
            model_name: str,
            message: str,
            session_id: UUID | None = None,
    ) -> tuple[ChatSession, LLMModel, str, list[ChatMessage]]:
        """
        Validate and persist the user turn without invoking the model.

        Streaming chat uses this to create the session/message before returning
        the SSE response, while keeping validation and ownership identical to
        the synchronous chat endpoint.
        """
        normalized_provider_name = self._normalize_provider_name(provider_name)
        normalized_message = self._normalize_message(message)
        authenticated_user = self.auth_service.require_authenticated_user(
            detail="Authentication is required to use chat sessions."
        )

        llm_model = self.llm_model_service.get_model_by_name_for_provider(
            model_name=model_name,
            provider_name=normalized_provider_name,
            require_active=True,
        )
        session = self._resolve_session(
            session_id=session_id,
            llm_model=llm_model,
            user=authenticated_user,
        )
        history_messages = self._get_history_messages(
            session=session,
            limit=self.MEMORY_WINDOW_SIZE,
        )

        ChatMessage.objects.create(
            session=session,
            role=ChatMessage.MessageRole.USER,
            content=normalized_message,
        )

        return session, llm_model, normalized_message, history_messages

    @staticmethod
    def persist_assistant_message(
        session: ChatSession,
        response_details: dict[str, Any],
    ) -> ChatMessage:
        """
        Persist one completed assistant message for a chat session.

        Args:
            session: Session that owns the assistant response.
            response_details: Normalized inference metadata.

        Returns:
            ChatMessage: Persisted assistant message.
        """
        return ChatMessage.objects.create(
            session=session,
            role=ChatMessage.MessageRole.ASSISTANT,
            content=response_details["response_text"],
            error_message=None,
            finish_reason=response_details["finish_reason"],
            prompt_tokens=response_details["prompt_tokens"],
            completion_tokens=response_details["completion_tokens"],
            total_tokens=response_details["total_tokens"],
            raw_metadata=response_details["raw_metadata"],
        )

    @staticmethod
    def persist_failed_assistant_message(session: ChatSession, error_message: str) -> ChatMessage:
        """
        Persist a failed assistant message so chat history reflects the failed turn.

        Args:
            session: Session that owns the failed assistant response.
            error_message: Failure message to persist.

        Returns:
            ChatMessage: Persisted failed assistant message.
        """
        return ChatMessage.objects.create(
            session=session,
            role=ChatMessage.MessageRole.ASSISTANT,
            content="",
            error_message=error_message,
        )

    def _normalize_provider_name(self, provider_name: str) -> str:
        """
        Normalize and validate the provider name for chat.

        Args:
            provider_name: Provider name from request payload.

        Returns:
            str: Normalized provider name.

        Raises:
            InvalidChatProviderException: If provider is missing or not finki.
        """
        normalized_provider_name = provider_name.strip().lower()
        if normalized_provider_name != self.SUPPORTED_PROVIDER_NAME:
            raise InvalidChatProviderException(
                detail=(
                    f"Provider '{normalized_provider_name or provider_name}' is not supported for chat. "
                    "Only provider 'finki' is allowed."
                )
            )
        return normalized_provider_name

    @staticmethod
    def _normalize_message(message: str) -> str:
        """
        Normalize and validate an incoming chat message.

        Args:
            message: Raw user message from request payload.

        Returns:
            str: Trimmed message content.

        Raises:
            ChatMessageValidationException: If the message is empty after trimming.
        """
        normalized_message = message.strip()
        if not normalized_message:
            raise ChatMessageValidationException()
        return normalized_message

    def _resolve_session(self, session_id: UUID | None, llm_model: LLMModel, user) -> ChatSession:
        """
        Resolve an existing session or create a new one for first-message requests.

        Args:
            session_id: Existing session UUID if provided.
            llm_model: Model chosen for the request.

        Returns:
            ChatSession: Existing or newly created session.

        Raises:
            ChatSessionNotFoundException: If session_id does not exist.
            ChatSessionModelMismatchException: If session model differs from request model.
        """
        if session_id is None:
            return ChatSession.objects.create(user=user, llm_model=llm_model)

        session = (
            ChatSession.objects
            .select_related("llm_model__provider")
            .filter(id=session_id)
            .first()
        )
        if session is None:
            raise ChatSessionNotFoundException(
                detail=f"Chat session '{session_id}' was not found."
            )
        self.auth_service.validate_owned_resource_access(
            owner_id=session.user_id,
            resource_label=f"Chat session '{session_id}'",
        )

        if session.llm_model_id != llm_model.id:
            raise ChatSessionModelMismatchException(
                detail=(
                    f"Session model '{session.llm_model.name}' does not match requested model "
                    f"'{llm_model.name}'."
                )
            )

        return session

    @staticmethod
    def _get_history_messages(session: ChatSession, limit: int) -> list[ChatMessage]:
        """
        Fetch the most recent persisted chat messages for inference memory context.

        Args:
            session: Session whose history should be loaded.
            limit: Maximum number of historical messages to include.

        Returns:
            list[ChatMessage]: Oldest-to-newest history slice for model invocation.
        """
        recent_messages = list(
            ChatMessage.objects
            .filter(session=session)
            .order_by("-created_at", "-id")[:limit]
        )
        recent_messages.reverse()
        return recent_messages
