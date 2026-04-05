from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from common.management.commands.llm_seed_data import MODEL_SEEDS
from llm_arena.models import LLMModel, LLMProvider


class Command(BaseCommand):
    help = "Seed the default LLM models for the arena."

    @transaction.atomic
    def handle(self, *args, **options) -> None:
        provider_lookup = {
            provider.name: provider
            for provider in LLMProvider.objects.all()
        }

        missing_provider_names = sorted(
            {
                model_seed.provider_name
                for model_seed in MODEL_SEEDS
                if model_seed.provider_name not in provider_lookup
            }
        )
        if missing_provider_names:
            raise CommandError(
                "Missing provider records for model seeding: "
                + ", ".join(missing_provider_names)
                + ". Run `python manage.py seed_llm_providers` first."
            )

        for model_seed in MODEL_SEEDS:
            provider = provider_lookup[model_seed.provider_name]
            model, created = LLMModel.objects.update_or_create(
                provider=provider,
                external_model_id=model_seed.external_model_id,
                defaults={
                    "name": model_seed.name,
                    "description": model_seed.description,
                    "is_active": model_seed.is_active,
                    "is_fine_tuned": model_seed.is_fine_tuned,
                    "is_macedonian_optimized": model_seed.is_macedonian_optimized,
                    "supports_temperature": model_seed.supports_temperature,
                    "supports_top_p": model_seed.supports_top_p,
                    "supports_top_k": model_seed.supports_top_k,
                    "supports_frequency_penalty": model_seed.supports_frequency_penalty,
                    "supports_presence_penalty": model_seed.supports_presence_penalty,
                    "configuration": model_seed.configuration,
                },
            )

            action = "Created" if created else "Updated"
            self.stdout.write(f"{action} model: {model.name}")

        self.stdout.write(self.style.SUCCESS("LLM model seeding completed."))
