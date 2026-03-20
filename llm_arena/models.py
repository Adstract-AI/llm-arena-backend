import uuid

from django.core.validators import MinValueValidator
from django.db import models


class TimestampedModel(models.Model):
    """Provide created and updated timestamps for concrete arena models."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class LLMProvider(TimestampedModel):
    """Store the provider responsible for serving one or more arena models."""

    name = models.CharField(max_length=100, unique=True)
    display_name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    api_base_url = models.URLField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class LLMModel(TimestampedModel):
    """Define a concrete LLM that can participate in arena battles."""

    provider = models.ForeignKey(
        LLMProvider,
        on_delete=models.PROTECT,
        related_name="models",
    )
    name = models.CharField(max_length=150)
    external_model_id = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    is_fine_tuned = models.BooleanField(default=False)
    is_macedonian_optimized = models.BooleanField(default=False)
    configuration = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "external_model_id"],
                name="unique_provider_external_model_id",
            ),
        ]
        indexes = [
            models.Index(fields=["is_active"]),
            models.Index(fields=["is_fine_tuned"]),
            models.Index(fields=["is_macedonian_optimized"]),
        ]

    def __str__(self) -> str:
        return self.name

    @property
    def provider_name(self) -> str:
        """Return the normalized provider identifier for this model."""
        return self.provider.name.strip().lower()


class ArenaBattle(TimestampedModel):
    """Represent a single blind comparison request for one submitted prompt."""

    class BattleStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        AWAITING_VOTE = "awaiting_vote", "Awaiting Vote"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    battle_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    prompt = models.TextField()
    status = models.CharField(
        max_length=16,
        choices=BattleStatus.choices,
        default=BattleStatus.PENDING,
    )
    error_message = models.TextField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self) -> str:
        return f"Battle #{self.pk}"


class BattleResponse(TimestampedModel):
    """Store one model output generated during a battle."""

    class ResponseSlot(models.TextChoices):
        A = "A", "Answer A"
        B = "B", "Answer B"

    class ResponseStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    battle = models.ForeignKey(
        ArenaBattle,
        on_delete=models.CASCADE,
        related_name="responses",
    )
    llm_model = models.ForeignKey(
        LLMModel,
        on_delete=models.PROTECT,
        related_name="battle_responses",
    )
    slot = models.CharField(max_length=1, choices=ResponseSlot.choices)
    status = models.CharField(
        max_length=16,
        choices=ResponseStatus.choices,
        default=ResponseStatus.PENDING,
    )
    response_text = models.TextField(blank=True)
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
    latency_ms = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
    )
    raw_metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["slot"]
        constraints = [
            models.UniqueConstraint(
                fields=["battle", "slot"],
                name="unique_battle_response_slot",
            ),
            models.UniqueConstraint(
                fields=["battle", "llm_model"],
                name="unique_battle_response_model",
            ),
        ]
        indexes = [
            models.Index(fields=["battle", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.battle} - {self.get_slot_display()}"


class BattleVote(TimestampedModel):
    """Capture the user preference submitted for a completed battle."""

    class VoteChoice(models.TextChoices):
        A = "A", "Answer A"
        B = "B", "Answer B"
        TIE = "tie", "Tie"

    battle = models.OneToOneField(
        ArenaBattle,
        on_delete=models.CASCADE,
        related_name="vote",
    )
    choice = models.CharField(max_length=4, choices=VoteChoice.choices)
    feedback = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["choice"]),
        ]

    def __str__(self) -> str:
        return f"Vote for {self.battle}"
