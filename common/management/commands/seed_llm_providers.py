from django.core.management.base import BaseCommand
from django.db import transaction

from common.management.commands.llm_seed_data import PROVIDER_SEEDS
from llm_arena.models import LLMProvider


class Command(BaseCommand):
    help = "Seed the default LLM providers for the arena."

    @transaction.atomic
    def handle(self, *args, **options) -> None:
        for provider_seed in PROVIDER_SEEDS:
            provider, created = LLMProvider.objects.update_or_create(
                name=provider_seed.name,
                defaults={
                    "display_name": provider_seed.display_name,
                    "description": provider_seed.description,
                    "api_base_url": provider_seed.api_base_url,
                },
            )
            action = "Created" if created else "Updated"
            self.stdout.write(f"{action} provider: {provider.name}")

        self.stdout.write(self.style.SUCCESS("LLM provider seeding completed."))
