from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.management import call_command
from django.test import RequestFactory, TestCase

from platform_settings.exceptions import RateLimitExceededException
from platform_settings.management.commands.seed_platform_settings import DEFAULT_RATE_LIMITS
from platform_settings.models import PlatformSettings, RateLimitUsage, RateLimits
from platform_settings.services import RateLimitService, SettingsService

User = get_user_model()


class PlatformSettingsServiceTests(TestCase):
    def setUp(self) -> None:
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username="rate-user", email="rate@example.com")

    def test_seed_platform_settings_creates_active_profile(self):
        call_command("seed_platform_settings")

        settings = SettingsService().get_active_settings()
        self.assertEqual(settings.name, "General Settings")
        self.assertEqual(settings.rate_limits.name, "General Rate Limits")
        self.assertEqual(settings.rate_limits.chat_user_per_minute, 5)

    def test_seed_platform_settings_preserves_existing_active_profile(self):
        self._create_active_settings(name="High Demand Settings", rate_limit_name="High Demand Rate Limits")

        call_command("seed_platform_settings")

        settings = SettingsService().get_active_settings()
        self.assertEqual(settings.name, "High Demand Settings")
        self.assertTrue(PlatformSettings.objects.filter(name="General Settings", is_active=False).exists())

    def test_seed_platform_settings_reactivates_general_when_no_profile_is_active(self):
        rate_limits = RateLimits.objects.create(name="General Rate Limits", **DEFAULT_RATE_LIMITS)
        PlatformSettings.objects.create(
            name="General Settings",
            is_active=False,
            rate_limits=rate_limits,
        )

        call_command("seed_platform_settings")

        settings = SettingsService().get_active_settings()
        self.assertEqual(settings.name, "General Settings")

    def test_anonymous_normal_arena_limit_uses_ip_bucket(self):
        self._create_active_settings(
            normal_arena_anonymous_per_minute=1,
            normal_arena_anonymous_per_hour=10,
            normal_arena_anonymous_per_day=10,
        )
        request = self.factory.post(
            "/api/arena/battles/",
            REMOTE_ADDR="10.0.0.5",
        )
        request.user = AnonymousUser()

        service = RateLimitService(user=request.user)
        service.enforce_normal_arena_limit(request)

        with self.assertRaises(RateLimitExceededException):
            service.enforce_normal_arena_limit(request)

        usage = RateLimitUsage.objects.get(
            bucket=RateLimitUsage.Bucket.NORMAL_ARENA_ANONYMOUS,
            identity_type=RateLimitUsage.IdentityType.IP,
            identity="10.0.0.5",
            window=RateLimitUsage.Window.MINUTE,
        )
        self.assertEqual(usage.count, 1)

    def test_authenticated_normal_arena_limit_uses_user_bucket(self):
        self._create_active_settings(
            normal_arena_user_per_minute=1,
            normal_arena_user_per_hour=10,
            normal_arena_user_per_day=10,
        )
        request = self.factory.post("/api/arena/battles/")
        request.user = self.user

        service = RateLimitService(user=self.user)
        service.enforce_normal_arena_limit(request)

        with self.assertRaises(RateLimitExceededException):
            service.enforce_normal_arena_limit(request)

        usage = RateLimitUsage.objects.get(
            bucket=RateLimitUsage.Bucket.NORMAL_ARENA_USER,
            identity_type=RateLimitUsage.IdentityType.USER,
            identity=str(self.user.id),
            window=RateLimitUsage.Window.MINUTE,
        )
        self.assertEqual(usage.count, 1)

    def test_chat_limit_uses_user_bucket(self):
        self._create_active_settings(
            chat_user_per_minute=1,
            chat_user_per_hour=10,
            chat_user_per_day=10,
        )
        service = RateLimitService(user=self.user)
        service.enforce_chat_limit()

        with self.assertRaises(RateLimitExceededException):
            service.enforce_chat_limit()

    def test_experimental_arena_limit_uses_user_bucket(self):
        self._create_active_settings(
            experimental_arena_user_per_minute=1,
            experimental_arena_user_per_hour=10,
            experimental_arena_user_per_day=10,
        )
        service = RateLimitService(user=self.user)
        service.enforce_experimental_arena_limit()

        with self.assertRaises(RateLimitExceededException):
            service.enforce_experimental_arena_limit()

    @staticmethod
    def _create_active_settings(
        name: str = "Test Settings",
        rate_limit_name: str = "Test Rate Limits",
        **overrides,
    ) -> PlatformSettings:
        defaults = DEFAULT_RATE_LIMITS | overrides
        rate_limits = RateLimits.objects.create(name=rate_limit_name, **defaults)
        return PlatformSettings.objects.create(
            name=name,
            is_active=True,
            rate_limits=rate_limits,
        )
