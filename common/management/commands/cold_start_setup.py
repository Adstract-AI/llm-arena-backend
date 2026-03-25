from django.core.management.base import BaseCommand, CommandError

from helpers.cold_start_setup import perform_cold_start_setup


class Command(BaseCommand):
    help = "Run setup_project only when AUTO_START_SETUP is enabled."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--full-auto",
            action="store_true",
            help="Run setup without confirmation prompts when enabled.",
        )

    def handle(self, *args, **options) -> None:
        if not perform_cold_start_setup(auto_confirm=options["full_auto"]):
            raise CommandError("Cold-start setup did not complete successfully.")
