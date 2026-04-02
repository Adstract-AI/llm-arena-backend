from django.urls import path

from accounts.views import (
    CurrentUserView,
    GitHubOAuthLoginView,
    GoogleOAuthLoginView,
    JWTTokenRefreshView,
)

urlpatterns = [
    path("google/", GoogleOAuthLoginView.as_view(), name="auth-google-login"),
    path("github/", GitHubOAuthLoginView.as_view(), name="auth-github-login"),
    path("token/refresh/", JWTTokenRefreshView.as_view(), name="auth-token-refresh"),
    path("me/", CurrentUserView.as_view(), name="auth-me"),
]
