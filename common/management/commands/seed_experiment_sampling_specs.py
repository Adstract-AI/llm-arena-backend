from django.core.management.base import BaseCommand
from django.db import transaction

from common.management.commands.llm_seed_data import PARAMETER_SAMPLING_SPEC_SEEDS
from experimental_llm_arena.models import ParameterSamplingSpec


class Command(BaseCommand):
    help = "Seed the default experimental parameter sampling specs."

    @transaction.atomic
    def handle(self, *args, **options) -> None:
        for spec_seed in PARAMETER_SAMPLING_SPEC_SEEDS:
            spec, created = ParameterSamplingSpec.objects.update_or_create(
                parameter_name=spec_seed.parameter_name,
                defaults={
                    "value_type": spec_seed.value_type,
                    "minimum_value": spec_seed.minimum_value,
                    "maximum_value": spec_seed.maximum_value,
                    "uniform_min": spec_seed.uniform_min,
                    "uniform_max": spec_seed.uniform_max,
                    "normal_mean": spec_seed.normal_mean,
                    "normal_std": spec_seed.normal_std,
                    "beta_alpha": spec_seed.beta_alpha,
                    "beta_beta": spec_seed.beta_beta,
                },
            )
            action = "Created" if created else "Updated"
            self.stdout.write(f"{action} sampling spec: {spec.parameter_name}")

        self.stdout.write(self.style.SUCCESS("Experimental sampling spec seeding completed."))
