from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models

from common.models import TimestampedModel


class User(AbstractUser):
    """Application user authenticated through OAuth providers."""

    email = models.EmailField(unique=True)

    class Meta:
        ordering = ["email", "username"]

    def __str__(self) -> str:
        return self.email or self.username


class OAuthAccount(TimestampedModel):
    """Map one external OAuth identity to one internal user."""

    class Provider(models.TextChoices):
        GOOGLE = "google", "Google"
        GITHUB = "github", "GitHub"

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="oauth_accounts",
    )
    provider = models.CharField(max_length=32, choices=Provider.choices)
    provider_user_id = models.CharField(max_length=255)
    email = models.EmailField()
    email_verified = models.BooleanField(default=False)

    class Meta:
        ordering = ["provider", "email"]
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "provider_user_id"],
                name="unique_oauth_provider_user_id",
            ),
        ]
        indexes = [
            models.Index(fields=["provider", "provider_user_id"]),
            models.Index(fields=["email"]),
        ]

    def __str__(self) -> str:
        return f"{self.get_provider_display()} - {self.email}"

    def clean(self) -> None:
        """Ensure OAuth accounts always retain an email address."""
        super().clean()
        if not self.email:
            raise ValidationError({"email": "OAuth accounts require an email address."})
