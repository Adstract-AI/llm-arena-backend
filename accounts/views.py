from rest_framework import status
from rest_framework.generics import CreateAPIView, RetrieveAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenRefreshView

from accounts.serializers import (
    AuthenticatedUserSerializer,
    OAuthCodeRequestSerializer,
    OAuthLoginResponseSerializer,
)
from accounts.services.auth_service import AuthService
from common.abstract import ServiceView


class GoogleOAuthLoginView(ServiceView[AuthService], CreateAPIView):
    """Exchange a Google OAuth code for JWT tokens."""

    permission_classes = [AllowAny]
    service_class = AuthService
    serializer_class = OAuthCodeRequestSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = self.service.authenticate_with_google(serializer.validated_data["code"])
        return Response(
            OAuthLoginResponseSerializer(payload).data,
            status=status.HTTP_200_OK,
        )


class GitHubOAuthLoginView(ServiceView[AuthService], CreateAPIView):
    """Exchange a GitHub OAuth code for JWT tokens."""

    permission_classes = [AllowAny]
    service_class = AuthService
    serializer_class = OAuthCodeRequestSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = self.service.authenticate_with_github(serializer.validated_data["code"])
        return Response(
            OAuthLoginResponseSerializer(payload).data,
            status=status.HTTP_200_OK,
        )


class CurrentUserView(ServiceView[AuthService], RetrieveAPIView):
    """Return the currently authenticated user."""

    permission_classes = [IsAuthenticated]
    service_class = AuthService
    serializer_class = AuthenticatedUserSerializer

    def retrieve(self, request, *args, **kwargs):
        payload = self.service.get_current_user_payload()
        return Response(self.get_serializer(payload).data, status=status.HTTP_200_OK)


class JWTTokenRefreshView(TokenRefreshView):
    """Refresh an access token using a refresh token."""
