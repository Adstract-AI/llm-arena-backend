from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db import router
from django.db.models import Q

from common.models import TimestampedModel


class RateLimits(TimestampedModel):
    """Store section-level rate limits for platform generation endpoints."""

    name = models.CharField(max_length=120, unique=True)
    normal_arena_anonymous_per_minute = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    normal_arena_anonymous_per_hour = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    normal_arena_anonymous_per_day = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    normal_arena_user_per_minute = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    normal_arena_user_per_hour = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    normal_arena_user_per_day = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    experimental_arena_user_per_minute = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    experimental_arena_user_per_hour = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    experimental_arena_user_per_day = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    chat_user_per_minute = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    chat_user_per_hour = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    chat_user_per_day = models.PositiveIntegerField(validators=[MinValueValidator(1)])

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class PlatformSettings(TimestampedModel):
    """Select the active platform configuration used by runtime services."""

    name = models.CharField(max_length=120, unique=True)
    is_active = models.BooleanField(default=False)
    rate_limits = models.OneToOneField(
        RateLimits,
        on_delete=models.PROTECT,
        related_name="platform_settings",
    )

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["is_active"],
                condition=Q(is_active=True),
                name="unique_active_platform_settings",
            ),
        ]
        indexes = [
            models.Index(fields=["is_active"]),
        ]

    def __str__(self) -> str:
        return self.name

    def validate_constraints(self, exclude=None):
        """
        Let admin switch the active profile in one save.

        The database constraint still enforces one active profile, but model-form
        validation must not block the admin before save_model() can deactivate the
        previously active profile inside the same transaction.
        """
        constraints = self.get_constraints()
        using = router.db_for_write(self.__class__, instance=self)

        errors = {}
        for model_class, model_constraints in constraints:
            for constraint in model_constraints:
                if self.is_active and constraint.name == "unique_active_platform_settings":
                    continue
                try:
                    constraint.validate(model_class, self, exclude=exclude, using=using)
                except ValidationError as exc:
                    if getattr(exc, "code", None) == "unique" and len(constraint.fields) == 1:
                        errors.setdefault(constraint.fields[0], []).append(exc)
                    else:
                        errors = exc.update_error_dict(errors)
        if errors:
            raise ValidationError(errors)


class RateLimitUsage(TimestampedModel):
    """Track fixed-window rate-limit usage for one bucket and identity."""

    class Bucket(models.TextChoices):
        NORMAL_ARENA_ANONYMOUS = "normal_arena_anonymous", "Normal Arena Anonymous"
        NORMAL_ARENA_USER = "normal_arena_user", "Normal Arena User"
        EXPERIMENTAL_ARENA_USER = "experimental_arena_user", "Experimental Arena User"
        CHAT_USER = "chat_user", "Chat User"

    class IdentityType(models.TextChoices):
        IP = "ip", "IP"
        USER = "user", "User"

    class Window(models.TextChoices):
        MINUTE = "minute", "Minute"
        HOUR = "hour", "Hour"
        DAY = "day", "Day"

    bucket = models.CharField(max_length=40, choices=Bucket.choices)
    identity_type = models.CharField(max_length=8, choices=IdentityType.choices)
    identity = models.CharField(max_length=255)
    window = models.CharField(max_length=12, choices=Window.choices)
    window_start = models.DateTimeField()
    count = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)])

    class Meta:
        ordering = ["-window_start"]
        constraints = [
            models.UniqueConstraint(
                fields=["bucket", "identity_type", "identity", "window", "window_start"],
                name="unique_rate_limit_usage_window",
            ),
        ]
        indexes = [
            models.Index(fields=["bucket", "identity_type", "identity"]),
            models.Index(fields=["window_start"]),
        ]

    def __str__(self) -> str:
        return f"{self.bucket}:{self.identity_type}:{self.identity}:{self.window}:{self.window_start}"
