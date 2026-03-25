from django.db import models

class TimestampedModel(models.Model):
    """Provide created and updated timestamps for concrete arena models."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
