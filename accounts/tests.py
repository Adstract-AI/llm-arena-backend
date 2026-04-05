from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import OAuthAccount


User = get_user_model()


class OAuthAuthenticationTests(APITestCase):
    def setUp(self) -> None:
        self.google_url = reverse("auth-google-login")
        self.github_url = reverse("auth-github-login")
        self.me_url = reverse("auth-me")
        self.refresh_url = reverse("auth-token-refresh")

    @patch("accounts.services.auth_service.requests.get")
    @patch("accounts.services.auth_service.requests.post")
    def test_google_oauth_login_creates_user_and_returns_jwts(self, mock_post, mock_get):
        mock_post.return_value = self._mock_response(
            200,
            {"access_token": "google-access-token"},
        )
        mock_get.return_value = self._mock_response(
            200,
            {
                "sub": "google-user-1",
                "email": "oauth@example.com",
                "email_verified": True,
                "given_name": "OAuth",
                "family_name": "User",
            },
        )

        response = self.client.post(
            self.google_url,
            {"code": "google-code"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertEqual(response.data["user"]["email"], "oauth@example.com")
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(OAuthAccount.objects.count(), 1)

    @patch("accounts.services.auth_service.requests.get")
    @patch("accounts.services.auth_service.requests.post")
    def test_github_login_links_existing_user_by_verified_email(self, mock_post, mock_get):
        existing_user = User.objects.create_user(
            username="oauth_user",
            email="oauth@example.com",
        )

        mock_post.return_value = self._mock_response(
            200,
            {"access_token": "github-access-token"},
        )
        mock_get.side_effect = [
            self._mock_response(
                200,
                {
                    "id": 123,
                    "login": "octocat",
                },
            ),
            self._mock_response(
                200,
                [
                    {
                        "email": "oauth@example.com",
                        "verified": True,
                        "primary": True,
                    }
                ],
            ),
        ]

        response = self.client.post(
            self.github_url,
            {"code": "github-code"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["user"]["email"], str(existing_user.email))
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(
            OAuthAccount.objects.get(provider=OAuthAccount.Provider.GITHUB).user_id,
            existing_user.id,
        )

    @patch("accounts.services.auth_service.requests.get")
    @patch("accounts.services.auth_service.requests.post")
    def test_me_and_refresh_endpoints_work_with_jwts(self, mock_post, mock_get):
        mock_post.return_value = self._mock_response(
            200,
            {"access_token": "google-access-token"},
        )
        mock_get.return_value = self._mock_response(
            200,
            {
                "sub": "google-user-2",
                "email": "me@example.com",
                "email_verified": True,
                "given_name": "Me",
                "family_name": "User",
            },
        )

        login_response = self.client.post(
            self.google_url,
            {"code": "google-code"},
            format="json",
        )
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}")
        me_response = self.client.get(self.me_url)
        self.assertEqual(me_response.status_code, status.HTTP_200_OK)
        self.assertEqual(me_response.data["email"], "me@example.com")

        refresh_response = self.client.post(
            self.refresh_url,
            {"refresh": login_response.data["refresh"]},
            format="json",
        )
        self.assertEqual(refresh_response.status_code, status.HTTP_200_OK)
        self.assertIn("access", refresh_response.data)

    @staticmethod
    def _mock_response(status_code: int, payload):
        class MockResponse:
            def __init__(self, response_status: int, response_payload):
                self.status_code = response_status
                self._payload = response_payload
                self.text = str(response_payload)

            def json(self):
                return self._payload

        return MockResponse(status_code, payload)
