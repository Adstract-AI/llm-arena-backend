from rest_framework import status

from common.exceptions.general_exceptions import GeneralException


class PlatformSettingsException(GeneralException):
    """Base exception for runtime platform settings failures."""

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = "Platform settings are not configured correctly."
    default_code = "platform_settings_error"


class ActivePlatformSettingsNotFoundException(PlatformSettingsException):
    """Raised when no active platform settings profile exists."""

    default_detail = "No active platform settings profile is configured."
    default_code = "active_platform_settings_not_found"


class RateLimitExceededException(GeneralException):
    """Raised when a request exceeds a configured rate limit."""

    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_detail = "Rate limit exceeded."
    default_code = "rate_limit_exceeded"

    def __init__(self, detail=None, bucket: str | None = None, window: str | None = None, limit: int | None = None):
        payload = detail or {
            "detail": f"Rate limit exceeded for {bucket}.",
            "bucket": bucket,
            "window": window,
            "limit": limit,
        }
        super().__init__(payload)
