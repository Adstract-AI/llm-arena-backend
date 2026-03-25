from django.core.management.base import BaseCommand, CommandError

from helpers.reset_migrations import reset_all_migrations


class Command(BaseCommand):
    help = "Delete migration files for the local Django apps."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--noinput",
            action="store_true",
            help="Run without an interactive confirmation prompt.",
        )

    def handle(self, *args, **options) -> None:
        if not options["noinput"]:
            confirmed = input("Delete migration files for local Django apps? (yes/no): ").strip().lower()
            if confirmed not in {"yes", "y"}:
                self.stdout.write(self.style.WARNING("Migration reset cancelled."))
                return

        success_count, error_count = reset_all_migrations()

        if error_count:
            raise CommandError(f"Migration reset finished with {error_count} error(s).")

        self.stdout.write(
            self.style.SUCCESS(
                f"Migration reset completed successfully for {success_count} app(s)."
            )
        )
