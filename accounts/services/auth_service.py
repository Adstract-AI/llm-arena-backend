import re
from typing import Any

import requests
from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.exceptions import (
    AuthenticationRequiredException,
    InactiveUserException,
    OAuthCodeExchangeException,
    OAuthConfigurationException,
    OAuthEmailNotVerifiedException,
    ResourceOwnershipException,
)
from accounts.models import OAuthAccount
from common.abstract import AbstractService
from helpers.env_variables import (
    GITHUB_OAUTH_CLIENT_ID,
    GITHUB_OAUTH_CLIENT_SECRET,
    GITHUB_OAUTH_REDIRECT_URI,
    GOOGLE_OAUTH_CLIENT_ID,
    GOOGLE_OAUTH_CLIENT_SECRET,
    GOOGLE_OAUTH_REDIRECT_URI,
)


User = get_user_model()


class AuthService(AbstractService):
    """Handle OAuth login, account linking, and JWT issuance."""

    GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
    GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
    GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
    GITHUB_USER_URL = "https://api.github.com/user"
    GITHUB_EMAILS_URL = "https://api.github.com/user/emails"
    REQUEST_TIMEOUT_SECONDS = 20

    def require_authenticated_user(self, detail: str | None = None):
        """
        Return the current authenticated user or raise when the request is anonymous.

        Args:
            detail: Optional custom exception detail.

        Returns:
            User: The authenticated request user.

        Raises:
            AuthenticationRequiredException: If the current request has no authenticated user.
        """
        if self._user is None or not getattr(self._user, "is_authenticated", False):
            raise AuthenticationRequiredException(
                detail=detail or "Authentication is required for this operation."
            )
        if not getattr(self._user, "is_active", False):
            raise InactiveUserException()
        return self._user

    def get_optional_authenticated_user(self):
        """
        Return the current authenticated user when present, otherwise None.

        Returns:
            User | None: Authenticated user or None for anonymous requests.
        """
        if self._user is None or not getattr(self._user, "is_authenticated", False):
            return None
        if not getattr(self._user, "is_active", False):
            return None
        return self._user

    def anonymize_user(self, user) -> None:
        """
        Soft-delete a user by scrubbing identifying information and disabling access.

        Args:
            user: The user instance to anonymize.
        """
        user.username = f"deleted_user_{user.pk}"
        user.email = f"deleted_user_{user.pk}@deleted.local"
        user.first_name = "Deleted"
        user.last_name = "User"
        user.is_active = False
        user.set_unusable_password()
        user.save()

        for oauth_account in user.oauth_accounts.all():
            oauth_account.provider_user_id = f"deleted_oauth_{oauth_account.pk}"
            oauth_account.email = f"deleted_oauth_{oauth_account.pk}@deleted.local"
            oauth_account.email_verified = False
            oauth_account.save(update_fields=["provider_user_id", "email", "email_verified", "updated_at"])

    def delete_current_user(self) -> dict[str, str]:
        """
        Anonymize the currently authenticated user.

        Returns:
            dict[str, str]: Success payload for the API response.
        """
        user = self.require_authenticated_user(
            detail="Authentication is required to delete your account."
        )
        self.anonymize_user(user)
        return {"detail": "Your account was deleted successfully."}

    def validate_owned_resource_access(
        self,
        owner_id,
        resource_label: str,
        require_auth_for_owned_resource: bool = True,
    ) -> None:
        """
        Enforce owner-only access for a resource bound to one authenticated user.

        Args:
            owner_id: Persisted owner primary key for the resource.
            resource_label: Human-readable resource label used in exception messages.
            require_auth_for_owned_resource: Whether anonymous users should be rejected.

        Raises:
            AuthenticationRequiredException: If the resource is owned and the request is anonymous.
            ResourceOwnershipException: If the resource is owned by another user.
        """
        if owner_id is None:
            return

        current_user = self.get_optional_authenticated_user()
        if current_user is None:
            if require_auth_for_owned_resource:
                raise AuthenticationRequiredException(
                    detail=f"Authentication is required to access {resource_label}."
                )
            return

        if getattr(current_user, "is_superuser", False) or getattr(current_user, "is_staff", False):
            return

        if owner_id != current_user.id:
            raise ResourceOwnershipException(
                detail=f"{resource_label} does not belong to the current user."
            )

    def authenticate_with_google(self, code: str) -> dict[str, Any]:
        """Authenticate a user with a Google OAuth code and issue JWTs."""
        self._validate_provider_configuration(
            provider=OAuthAccount.Provider.GOOGLE,
            client_id=GOOGLE_OAUTH_CLIENT_ID,
            client_secret=GOOGLE_OAUTH_CLIENT_SECRET,
            redirect_uri=GOOGLE_OAUTH_REDIRECT_URI,
        )
        token_payload = self._exchange_google_code(code=code)
        profile = self._fetch_google_profile(access_token=token_payload["access_token"])

        email = (profile.get("email") or "").strip().lower()
        if not email or not profile.get("email_verified"):
            raise OAuthEmailNotVerifiedException(
                detail="Google login requires a verified email address."
            )

        user = self._resolve_user(
            provider=OAuthAccount.Provider.GOOGLE,
            provider_user_id=str(profile["sub"]),
            email=email,
            email_verified=True,
            first_name=(profile.get("given_name") or "").strip(),
            last_name=(profile.get("family_name") or "").strip(),
        )
        return self._build_auth_response(user)

    def authenticate_with_github(self, code: str) -> dict[str, Any]:
        """Authenticate a user with a GitHub OAuth code and issue JWTs."""
        self._validate_provider_configuration(
            provider=OAuthAccount.Provider.GITHUB,
            client_id=GITHUB_OAUTH_CLIENT_ID,
            client_secret=GITHUB_OAUTH_CLIENT_SECRET,
            redirect_uri=GITHUB_OAUTH_REDIRECT_URI,
        )
        token_payload = self._exchange_github_code(code=code)
        access_token = token_payload["access_token"]
        profile = self._fetch_github_profile(access_token=access_token)
        email_payload = self._fetch_verified_github_email(access_token=access_token)

        user = self._resolve_user(
            provider=OAuthAccount.Provider.GITHUB,
            provider_user_id=str(profile["id"]),
            email=email_payload["email"],
            email_verified=True,
            first_name="",
            last_name="",
        )
        return self._build_auth_response(user)

    def get_current_user_payload(self) -> dict[str, Any]:
        """Return the current authenticated user payload."""
        user = self.require_authenticated_user()
        return self._serialize_user(user)

    def _validate_provider_configuration(
        self,
        provider: str,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
    ) -> None:
        """Ensure OAuth credentials exist for the selected provider."""
        if client_id and client_secret and redirect_uri:
            return
        raise OAuthConfigurationException(
            detail=f"OAuth configuration is incomplete for provider '{provider}'."
        )

    def _exchange_google_code(self, code: str) -> dict[str, Any]:
        """Exchange a Google authorization code for an access token."""
        response = requests.post(
            self.GOOGLE_TOKEN_URL,
            data={
                "client_id": GOOGLE_OAUTH_CLIENT_ID,
                "client_secret": GOOGLE_OAUTH_CLIENT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": GOOGLE_OAUTH_REDIRECT_URI,
            },
            timeout=self.REQUEST_TIMEOUT_SECONDS,
        )
        if response.status_code != 200:
            raise OAuthCodeExchangeException(
                detail=f"Google token exchange failed: {response.text}"
            )
        return response.json()

    def _fetch_google_profile(self, access_token: str) -> dict[str, Any]:
        """Fetch the authenticated Google profile."""
        response = requests.get(
            self.GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=self.REQUEST_TIMEOUT_SECONDS,
        )
        if response.status_code != 200:
            raise OAuthCodeExchangeException(
                detail=f"Google profile fetch failed: {response.text}"
            )
        return response.json()

    def _exchange_github_code(self, code: str) -> dict[str, Any]:
        """Exchange a GitHub authorization code for an access token."""
        response = requests.post(
            self.GITHUB_TOKEN_URL,
            headers={"Accept": "application/json"},
            data={
                "client_id": GITHUB_OAUTH_CLIENT_ID,
                "client_secret": GITHUB_OAUTH_CLIENT_SECRET,
                "code": code,
                "redirect_uri": GITHUB_OAUTH_REDIRECT_URI,
            },
            timeout=self.REQUEST_TIMEOUT_SECONDS,
        )
        if response.status_code != 200:
            raise OAuthCodeExchangeException(
                detail=f"GitHub token exchange failed: {response.text}"
            )
        payload = response.json()
        if "access_token" not in payload:
            raise OAuthCodeExchangeException(
                detail=f"GitHub token exchange failed: {payload}"
            )
        return payload

    def _fetch_github_profile(self, access_token: str) -> dict[str, Any]:
        """Fetch the authenticated GitHub profile."""
        response = requests.get(
            self.GITHUB_USER_URL,
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {access_token}",
            },
            timeout=self.REQUEST_TIMEOUT_SECONDS,
        )
        if response.status_code != 200:
            raise OAuthCodeExchangeException(
                detail=f"GitHub profile fetch failed: {response.text}"
            )
        return response.json()

    def _fetch_verified_github_email(self, access_token: str) -> dict[str, Any]:
        """Resolve the primary verified GitHub email address."""
        response = requests.get(
            self.GITHUB_EMAILS_URL,
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {access_token}",
            },
            timeout=self.REQUEST_TIMEOUT_SECONDS,
        )
        if response.status_code != 200:
            raise OAuthCodeExchangeException(
                detail=f"GitHub email fetch failed: {response.text}"
            )

        verified_emails = [
            email_record
            for email_record in response.json()
            if email_record.get("verified") and email_record.get("email")
        ]
        primary_email = next(
            (record for record in verified_emails if record.get("primary")),
            None,
        )
        selected_email = primary_email or (verified_emails[0] if verified_emails else None)
        if selected_email is None:
            raise OAuthEmailNotVerifiedException(
                detail="GitHub login requires a verified email address."
            )
        return {
            "email": selected_email["email"].strip().lower(),
            "verified": True,
        }

    @transaction.atomic
    def _resolve_user(
        self,
        provider: str,
        provider_user_id: str,
        email: str,
        email_verified: bool,
        first_name: str,
        last_name: str,
    ):
        """Find or create one application user for an OAuth identity."""
        oauth_account = (
            OAuthAccount.objects
            .select_related("user")
            .filter(provider=provider, provider_user_id=provider_user_id)
            .first()
        )
        if oauth_account is not None:
            user = oauth_account.user
            self._update_user_names(user=user, first_name=first_name, last_name=last_name)
            self._update_oauth_account(
                oauth_account=oauth_account,
                email=email,
                email_verified=email_verified,
            )
            return user

        user = User.objects.filter(email=email).first()
        if user is None:
            user = User.objects.create_user(
                username=self._build_unique_username(email=email),
                email=email,
                first_name=first_name,
                last_name=last_name,
            )
        else:
            self._update_user_names(user=user, first_name=first_name, last_name=last_name)

        OAuthAccount.objects.create(
            user=user,
            provider=provider,
            provider_user_id=provider_user_id,
            email=email,
            email_verified=email_verified,
        )
        return user

    @staticmethod
    def _update_user_names(user, first_name: str, last_name: str) -> None:
        """Persist new provider names onto the existing user when present."""
        updated_fields: list[str] = []
        if first_name and user.first_name != first_name:
            user.first_name = first_name
            updated_fields.append("first_name")
        if last_name and user.last_name != last_name:
            user.last_name = last_name
            updated_fields.append("last_name")
        if updated_fields:
            updated_fields.append("updated_at") if hasattr(user, "updated_at") else None
            user.save(update_fields=updated_fields)

    @staticmethod
    def _update_oauth_account(
        oauth_account: OAuthAccount,
        email: str,
        email_verified: bool,
    ) -> None:
        """Refresh OAuth account metadata from the provider."""
        updated_fields: list[str] = []
        if oauth_account.email != email:
            oauth_account.email = email
            updated_fields.append("email")
        if oauth_account.email_verified != email_verified:
            oauth_account.email_verified = email_verified
            updated_fields.append("email_verified")
        if updated_fields:
            updated_fields.append("updated_at")
            oauth_account.save(update_fields=updated_fields)

    @staticmethod
    def _build_unique_username(email: str) -> str:
        """Generate a unique username from the user's email address."""
        base_username = re.sub(r"[^a-z0-9_]+", "_", email.split("@", 1)[0].lower()).strip("_")
        base_username = base_username or "user"
        candidate = base_username
        suffix = 1
        while User.objects.filter(username=candidate).exists():
            suffix += 1
            candidate = f"{base_username}_{suffix}"
        return candidate

    def _build_auth_response(self, user) -> dict[str, Any]:
        """Return JWT tokens and a public user payload."""
        refresh = RefreshToken.for_user(user)
        return {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": self._serialize_user(user),
        }

    @staticmethod
    def _serialize_user(user) -> dict[str, Any]:
        """Return the public user representation for auth endpoints."""
        return {
            "email": user.email,
            "username": user.username,
        }
