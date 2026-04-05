from django.core.management.base import BaseCommand
from django.db import transaction

from common.management.commands.llm_seed_data import AGENT_PROMPT_SEEDS
from llm_arena.models import AgentPrompt


class Command(BaseCommand):
    help = "Seed the default internal agent system prompts."

    @transaction.atomic
    def handle(self, *args, **options) -> None:
        for prompt_seed in AGENT_PROMPT_SEEDS:
            if prompt_seed.is_active:
                AgentPrompt.objects.filter(agent_type=prompt_seed.agent_type).exclude(
                    name=prompt_seed.name
                ).update(is_active=False)

            prompt, created = AgentPrompt.objects.update_or_create(
                agent_type=prompt_seed.agent_type,
                name=prompt_seed.name,
                defaults={
                    "system_prompt": prompt_seed.system_prompt,
                    "is_active": prompt_seed.is_active,
                },
            )
            action = "Created" if created else "Updated"
            self.stdout.write(f"{action} agent prompt: {prompt.name}")

        self.stdout.write(self.style.SUCCESS("Agent prompt seeding completed."))
