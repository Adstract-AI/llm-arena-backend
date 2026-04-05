import sys

from django.apps import AppConfig
from django.core.exceptions import ImproperlyConfigured

from helpers.env_variables import (
    GITHUB_OAUTH_CLIENT_ID,
    GITHUB_OAUTH_CLIENT_SECRET,
    GITHUB_OAUTH_REDIRECT_URI,
    GOOGLE_OAUTH_CLIENT_ID,
    GOOGLE_OAUTH_CLIENT_SECRET,
    GOOGLE_OAUTH_REDIRECT_URI,
)


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "accounts"

    def ready(self) -> None:
        """Validate required OAuth configuration on real server startup."""
        if not self._should_validate_oauth_settings():
            return

        missing_settings = [
            setting_name
            for setting_name, setting_value in (
                ("GOOGLE_OAUTH_CLIENT_ID", GOOGLE_OAUTH_CLIENT_ID),
                ("GOOGLE_OAUTH_CLIENT_SECRET", GOOGLE_OAUTH_CLIENT_SECRET),
                ("GOOGLE_OAUTH_REDIRECT_URI", GOOGLE_OAUTH_REDIRECT_URI),
                ("GITHUB_OAUTH_CLIENT_ID", GITHUB_OAUTH_CLIENT_ID),
                ("GITHUB_OAUTH_CLIENT_SECRET", GITHUB_OAUTH_CLIENT_SECRET),
                ("GITHUB_OAUTH_REDIRECT_URI", GITHUB_OAUTH_REDIRECT_URI),
            )
            if not setting_value
        ]
        if missing_settings:
            raise ImproperlyConfigured(
                "Missing OAuth configuration setting(s): "
                + ", ".join(missing_settings)
                + "."
            )

    @staticmethod
    def _should_validate_oauth_settings() -> bool:
        """
        Restrict hard validation to actual server startup flows.

        This avoids blocking local management commands like `check`, `migrate`,
        or seeding workflows while still failing fast when the app boots to
        serve traffic.
        """
        startup_commands = {"runserver", "gunicorn", "uvicorn", "daphne"}
        return any(command in sys.argv for command in startup_commands)
