from common.abstract import AbstractService
from platform_settings.exceptions import ActivePlatformSettingsNotFoundException
from platform_settings.models import PlatformSettings, RateLimits


class SettingsService(AbstractService):
    """Read active platform settings and linked subsettings."""

    def get_active_settings(self) -> PlatformSettings:
        settings = (
            PlatformSettings.objects
            .select_related("rate_limits")
            .filter(is_active=True)
            .first()
        )
        if settings is None:
            raise ActivePlatformSettingsNotFoundException()
        return settings

    def get_rate_limits(self) -> RateLimits:
        return self.get_active_settings().rate_limits
