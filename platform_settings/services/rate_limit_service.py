from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from accounts.services.auth_service import AuthService
from common.abstract import AbstractService
from platform_settings.exceptions import RateLimitExceededException
from platform_settings.models import RateLimitUsage
from platform_settings.services.settings_service import SettingsService


@dataclass(frozen=True)
class RateWindowConfig:
    window: str
    limit: int
    duration: timedelta


class RateLimitService(AbstractService):
    """Enforce admin-configured fixed-window rate limits for generation endpoints."""

    settings_service = SettingsService()
    auth_service = AuthService()

    def enforce_normal_arena_limit(self, request) -> None:
        current_user = self.auth_service.get_optional_authenticated_user()
        if current_user is None:
            self._enforce(
                bucket=RateLimitUsage.Bucket.NORMAL_ARENA_ANONYMOUS,
                identity_type=RateLimitUsage.IdentityType.IP,
                identity=self._get_client_ip(request),
            )
            return

        self._enforce(
            bucket=RateLimitUsage.Bucket.NORMAL_ARENA_USER,
            identity_type=RateLimitUsage.IdentityType.USER,
            identity=str(current_user.id),
        )

    def enforce_experimental_arena_limit(self) -> None:
        current_user = self.auth_service.require_authenticated_user(
            detail="Authentication is required to create experimental battles."
        )
        self._enforce(
            bucket=RateLimitUsage.Bucket.EXPERIMENTAL_ARENA_USER,
            identity_type=RateLimitUsage.IdentityType.USER,
            identity=str(current_user.id),
        )

    def enforce_chat_limit(self) -> None:
        current_user = self.auth_service.require_authenticated_user(
            detail="Authentication is required to use chat sessions."
        )
        self._enforce(
            bucket=RateLimitUsage.Bucket.CHAT_USER,
            identity_type=RateLimitUsage.IdentityType.USER,
            identity=str(current_user.id),
        )

    def _enforce(self, bucket: str, identity_type: str, identity: str) -> None:
        rate_limits = self.settings_service.get_rate_limits()
        with transaction.atomic():
            usages_and_limits = [
                (
                    self._get_locked_usage(
                        bucket=bucket,
                        identity_type=identity_type,
                        identity=identity,
                        window_config=window_config,
                    ),
                    window_config.limit,
                )
                for window_config in self._get_window_configs(bucket=bucket, rate_limits=rate_limits)
            ]
            for usage, limit in usages_and_limits:
                if usage.count >= limit:
                    raise RateLimitExceededException(
                        bucket=usage.bucket,
                        window=usage.window,
                        limit=limit,
                    )
            for usage, _ in usages_and_limits:
                usage.count += 1
                usage.save(update_fields=["count", "updated_at"])

    @staticmethod
    def _get_locked_usage(
        bucket: str,
        identity_type: str,
        identity: str,
        window_config: RateWindowConfig,
    ) -> RateLimitUsage:
        now = timezone.now()
        active_window_start_cutoff = now - window_config.duration
        usage = (
            RateLimitUsage.objects.select_for_update()
            .filter(
                bucket=bucket,
                identity_type=identity_type,
                identity=identity,
                window=window_config.window,
                window_start__gt=active_window_start_cutoff,
            )
            .order_by("-window_start")
            .first()
        )
        if usage is not None:
            return usage

        return RateLimitUsage.objects.create(
            bucket=bucket,
            identity_type=identity_type,
            identity=identity,
            window=window_config.window,
            window_start=now,
            count=0,
        )

    def _get_window_configs(self, bucket: str, rate_limits) -> list[RateWindowConfig]:
        return [
            RateWindowConfig(
                window=RateLimitUsage.Window.MINUTE,
                limit=getattr(rate_limits, f"{bucket}_per_minute"),
                duration=timedelta(minutes=1),
            ),
            RateWindowConfig(
                window=RateLimitUsage.Window.HOUR,
                limit=getattr(rate_limits, f"{bucket}_per_hour"),
                duration=timedelta(hours=1),
            ),
            RateWindowConfig(
                window=RateLimitUsage.Window.DAY,
                limit=getattr(rate_limits, f"{bucket}_per_day"),
                duration=timedelta(days=1),
            ),
        ]

    @staticmethod
    def _get_client_ip(request) -> str:
        forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "unknown")
