from django.core.management.base import BaseCommand, CommandError

from helpers.hard_reset_db import perform_hard_reset


class Command(BaseCommand):
    help = "Reset the local dockerized PostgreSQL database and reseed the catalog."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--full-auto",
            action="store_true",
            help="Run without confirmation prompts.",
        )

    def handle(self, *args, **options) -> None:
        if not perform_hard_reset(auto_confirm=options["full_auto"]):
            raise CommandError("Hard reset did not complete successfully.")
