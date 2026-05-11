from django.core.management.base import BaseCommand

from platform_settings.models import PlatformSettings, RateLimits


DEFAULT_RATE_LIMITS = {
    "normal_arena_anonymous_per_minute": 5,
    "normal_arena_anonymous_per_hour": 50,
    "normal_arena_anonymous_per_day": 200,
    "normal_arena_user_per_minute": 5,
    "normal_arena_user_per_hour": 50,
    "normal_arena_user_per_day": 200,
    "experimental_arena_user_per_minute": 5,
    "experimental_arena_user_per_hour": 50,
    "experimental_arena_user_per_day": 200,
    "chat_user_per_minute": 5,
    "chat_user_per_hour": 50,
    "chat_user_per_day": 200,
}


class Command(BaseCommand):
    help = "Seed the default active platform settings and rate limits."

    def handle(self, *args, **options) -> None:
        rate_limits, created_rate_limits = RateLimits.objects.get_or_create(
            name="General Rate Limits",
            defaults=DEFAULT_RATE_LIMITS,
        )

        has_active_settings = PlatformSettings.objects.filter(is_active=True).exists()
        settings, created_settings = PlatformSettings.objects.get_or_create(
            name="General Settings",
            defaults={
                "is_active": not has_active_settings,
                "rate_limits": rate_limits,
            },
        )
        if not has_active_settings and not settings.is_active:
            settings.is_active = True
            settings.rate_limits = rate_limits
            settings.save(update_fields=["is_active", "rate_limits", "updated_at"])

        self.stdout.write(
            self.style.SUCCESS(
                "Seeded platform settings"
                + (" and rate limits." if created_rate_limits or created_settings else ".")
            )
        )
