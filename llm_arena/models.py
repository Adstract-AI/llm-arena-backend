import uuid

from django.core.validators import MinValueValidator
from django.db import models
from common.models import TimestampedModel


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
    """Represent a multi-turn blind comparison session between two fixed models."""

    class BattleStatus(models.TextChoices):
        IN_PROGRESS = "in_progress", "In Progress"
        AWAITING_VOTE = "awaiting_vote", "Awaiting Vote"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    model_a = models.ForeignKey(
        LLMModel,
        on_delete=models.PROTECT,
        related_name="arena_battles_as_model_a",
    )
    model_b = models.ForeignKey(
        LLMModel,
        on_delete=models.PROTECT,
        related_name="arena_battles_as_model_b",
    )
    status = models.CharField(
        max_length=16,
        choices=BattleStatus.choices,
        default=BattleStatus.IN_PROGRESS,
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

    def get_model_for_slot(self, slot: str) -> LLMModel:
        """
        Return the fixed model assigned to an anonymized slot for this battle.

        Args:
            slot: Response slot identifier.

        Returns:
            LLMModel: The model assigned to the selected slot.
        """
        if slot == BattleResponse.ResponseSlot.A:
            return self.model_a
        return self.model_b


class ArenaTurn(TimestampedModel):
    """Store one user prompt turn within an arena battle conversation."""

    class TurnStatus(models.TextChoices):
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    battle = models.ForeignKey(
        ArenaBattle,
        on_delete=models.CASCADE,
        related_name="turns",
    )
    turn_number = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    prompt = models.TextField()
    status = models.CharField(
        max_length=16,
        choices=TurnStatus.choices,
        default=TurnStatus.IN_PROGRESS,
    )
    error_message = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ["turn_number", "created_at", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["battle", "turn_number"],
                name="unique_battle_turn_number",
            ),
        ]
        indexes = [
            models.Index(fields=["battle", "turn_number"]),
            models.Index(fields=["battle", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.battle} - Turn {self.turn_number}"


class BattleResponse(TimestampedModel):
    """Store one slot-specific model output generated during a battle turn."""

    class ResponseSlot(models.TextChoices):
        A = "A", "Answer A"
        B = "B", "Answer B"

    class ResponseStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    turn = models.ForeignKey(
        ArenaTurn,
        on_delete=models.CASCADE,
        related_name="responses",
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
                fields=["turn", "slot"],
                name="unique_turn_response_slot",
            ),
        ]
        indexes = [
            models.Index(fields=["turn", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.turn} - {self.get_slot_display()}"

    @property
    def battle(self) -> ArenaBattle:
        """Return the parent battle for this response."""
        return self.turn.battle

    @property
    def llm_model(self) -> LLMModel:
        """Return the fixed model assigned to this response slot."""
        return self.turn.battle.get_model_for_slot(self.slot)


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
