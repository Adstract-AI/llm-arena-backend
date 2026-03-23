import uuid

from django.core.validators import MinValueValidator
from django.db import models

from llm_arena.models import LLMModel
from common.models import TimestampedModel


class ChatSession(TimestampedModel):
    """Persist one conversation thread bound to a single LLM model."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    llm_model = models.ForeignKey(
        LLMModel,
        on_delete=models.PROTECT,
        related_name="chat_sessions",
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["created_at"], name="chat_session_created_idx"),
        ]

    def __str__(self) -> str:
        return f"Chat session {self.id}"


class ChatMessage(TimestampedModel):
    """Store one user or assistant message that belongs to a chat session."""

    class MessageRole(models.TextChoices):
        USER = "user", "User"
        ASSISTANT = "assistant", "Assistant"

    session = models.ForeignKey(
        ChatSession,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    role = models.CharField(max_length=16, choices=MessageRole.choices)
    content = models.TextField(blank=True)
    error_message = models.TextField(null=True, blank=True)
    finish_reason = models.CharField(max_length=50, null=True, blank=True)
    prompt_tokens = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
    )
    completion_tokens = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
    )
    total_tokens = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
    )
    raw_metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["created_at", "id"]
        indexes = [
            models.Index(
                fields=["session", "created_at"],
                name="chat_msg_session_created_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.session_id} [{self.role}]"
