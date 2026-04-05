from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed


class ActiveUserJWTAuthentication(JWTAuthentication):
    """Reject JWT-authenticated requests for inactive or anonymized users."""

    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        if not getattr(user, "is_active", False):
            raise AuthenticationFailed("This account has been deleted or deactivated.", code="inactive_user")
        return user
