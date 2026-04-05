from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.settings import api_settings

from accounts.exceptions import InactiveUserException
from accounts.models import User


class OAuthCodeRequestSerializer(serializers.Serializer):
    code = serializers.CharField()


class AuthenticatedUserSerializer(serializers.Serializer):
    email = serializers.EmailField()
    username = serializers.CharField()


class OAuthLoginResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()
    user = AuthenticatedUserSerializer()


class AccountDeleteResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()


class ActiveUserTokenRefreshSerializer(TokenRefreshSerializer):
    """Prevent refresh token usage for inactive or deleted users."""

    def validate(self, attrs):
        refresh = RefreshToken(attrs["refresh"])
        user_id = refresh.get(api_settings.USER_ID_CLAIM)
        user = User.objects.filter(pk=user_id).first()
        if user is None or not user.is_active:
            raise InactiveUserException()
        return super().validate(attrs)
