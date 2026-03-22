from rest_framework import status

from common.exceptions.general_exceptions import GeneralException


class ChatException(GeneralException):
    """Base exception for chat-domain service failures."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Chat operation failed."
    default_code = "chat_error"


class InvalidChatProviderException(ChatException):
    """Raised when the chat endpoint receives an unsupported provider."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Only provider 'finki' is supported for chat."
    default_code = "invalid_chat_provider"


class ChatMessageValidationException(ChatException):
    """Raised when the incoming chat prompt payload is invalid."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "A message is required for chat."
    default_code = "chat_message_validation_failed"


class ChatSessionNotFoundException(ChatException):
    """Raised when a chat session UUID does not match a persisted session."""

    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "Chat session not found."
    default_code = "chat_session_not_found"


class ChatSessionModelMismatchException(ChatException):
    """Raised when request model and session model do not match."""

    status_code = status.HTTP_409_CONFLICT
    default_detail = "Requested model does not match the chat session model."
    default_code = "chat_session_model_mismatch"


class ChatInferenceFailedException(ChatException):
    """Raised when a provider inference call fails during chat generation."""

    status_code = status.HTTP_502_BAD_GATEWAY
    default_detail = "Failed to generate chat response."
    default_code = "chat_inference_failed"
