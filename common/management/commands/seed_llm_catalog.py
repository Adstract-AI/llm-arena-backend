from dataclasses import dataclass

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import TextChoices

from llm_arena.models import LLMModel, LLMProvider


@dataclass(frozen=True)
class ProviderSeed:
    name: str
    provider_type: str
    api_base_url: str = ""


@dataclass(frozen=True)
class ModelSeed:
    provider_choice: str
    name: str
    external_model_id: str
    description: str
    is_active: bool = True
    is_fine_tuned: bool = False
    is_macedonian_optimized: bool = False


class ProviderSeedChoices(TextChoices):
    OPENAI = "openai", "OpenAI"
    ANTHROPIC = "anthropic", "Anthropic"
    OPENAI_COMPATIBLE = "openai_compatible", "OpenAI Compatible"


class ModelSeedChoices(TextChoices):
    GPT_4O = "gpt_4o", "GPT-4o"
    CLAUDE_35_SONNET = "claude_35_sonnet", "Claude 3.5 Sonnet"


PROVIDER_SEEDS = {
    ProviderSeedChoices.OPENAI: ProviderSeed(
        name="OpenAI",
        provider_type="openai",
        api_base_url="https://api.openai.com/v1",
    ),
    ProviderSeedChoices.ANTHROPIC: ProviderSeed(
        name="Anthropic",
        provider_type="anthropic",
        api_base_url="https://api.anthropic.com",
    ),
    ProviderSeedChoices.OPENAI_COMPATIBLE: ProviderSeed(
        name="OpenAI Compatible",
        provider_type="openai_compatible",
    ),
}

MODEL_SEEDS = {
    ModelSeedChoices.GPT_4O: ModelSeed(
        provider_choice=ProviderSeedChoices.OPENAI,
        name="GPT-4o",
        external_model_id="gpt-4o",
        description="General-purpose OpenAI model for arena comparisons.",
    ),
    ModelSeedChoices.CLAUDE_35_SONNET: ModelSeed(
        provider_choice=ProviderSeedChoices.ANTHROPIC,
        name="Claude 3.5 Sonnet",
        external_model_id="claude-3-5-sonnet-latest",
        description="General-purpose Anthropic model for arena comparisons.",
    ),
}


class Command(BaseCommand):
    help = "Seed the default LLM providers and LLM models for the arena."

    @transaction.atomic
    def handle(self, *args, **options) -> None:
        provider_lookup: dict[str, LLMProvider] = {}

        for provider_choice, provider_seed in PROVIDER_SEEDS.items():
            provider, created = LLMProvider.objects.update_or_create(
                name=provider_seed.name,
                defaults={
                    "provider_type": provider_seed.provider_type,
                    "api_base_url": provider_seed.api_base_url,
                },
            )
            provider_lookup[provider_choice] = provider

            action = "Created" if created else "Updated"
            self.stdout.write(f"{action} provider: {provider.name}")

        for _, model_seed in MODEL_SEEDS.items():
            provider = provider_lookup[model_seed.provider_choice]
            model, created = LLMModel.objects.update_or_create(
                provider=provider,
                external_model_id=model_seed.external_model_id,
                defaults={
                    "name": model_seed.name,
                    "description": model_seed.description,
                    "is_active": model_seed.is_active,
                    "is_fine_tuned": model_seed.is_fine_tuned,
                    "is_macedonian_optimized": model_seed.is_macedonian_optimized,
                },
            )

            action = "Created" if created else "Updated"
            self.stdout.write(f"{action} model: {model.name}")

        self.stdout.write(self.style.SUCCESS("LLM catalog seeding completed."))
