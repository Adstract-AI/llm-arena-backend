from rest_framework import status

from common.exceptions.general_exceptions import GeneralException


class AuthenticationException(GeneralException):
    """Base exception for authentication and authorization failures."""

    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = "Authentication failed."
    default_code = "authentication_failed"


class AuthenticationRequiredException(AuthenticationException):
    """Raised when an operation requires a logged-in user."""

    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = "Authentication is required for this operation."
    default_code = "authentication_required"


class ResourceOwnershipException(AuthenticationException):
    """Raised when a user attempts to access another user's resource."""

    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "You do not have access to this resource."
    default_code = "resource_ownership_forbidden"


class OAuthCodeExchangeException(AuthenticationException):
    """Raised when an OAuth code exchange or profile fetch fails."""

    status_code = status.HTTP_502_BAD_GATEWAY
    default_detail = "OAuth authentication failed."
    default_code = "oauth_code_exchange_failed"


class OAuthEmailNotVerifiedException(AuthenticationException):
    """Raised when the provider does not return a verified email."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "A verified email is required for OAuth login."
    default_code = "oauth_email_not_verified"


class OAuthConfigurationException(AuthenticationException):
    """Raised when OAuth credentials are missing for a provider."""

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = "OAuth provider configuration is missing."
    default_code = "oauth_configuration_missing"
