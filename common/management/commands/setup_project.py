from django.core.management.base import BaseCommand, CommandError

from helpers.project_setup import perform_initial_setup


class Command(BaseCommand):
    help = "Run the first-time local setup flow for the dockerized PostgreSQL database and catalog."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--full-auto",
            action="store_true",
            help="Run without confirmation prompts.",
        )

    def handle(self, *args, **options) -> None:
        if not perform_initial_setup(auto_confirm=options["full_auto"]):
            raise CommandError("Project setup did not complete successfully.")
