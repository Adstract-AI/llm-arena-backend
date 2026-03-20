#!/usr/bin/env python3
"""Reset migration files for the local Django apps in this project."""

import shutil

from helpers.constants import DATABASE_MIGRATIONS_DIR, DJANGO_APPS, ROOT


def delete_migration_files(app_name: str) -> tuple[bool, str]:
    """Delete migration files for a single Django app while keeping __init__.py."""
    app_path = ROOT / app_name
    migrations_path = app_path / DATABASE_MIGRATIONS_DIR

    if not app_path.exists():
        return False, f"App directory '{app_name}' does not exist"

    if not migrations_path.exists():
        return True, f"Migrations directory for '{app_name}' does not exist"

    try:
        deleted_files: list[str] = []

        for file_path in migrations_path.iterdir():
            if file_path.is_file() and file_path.name != "__init__.py":
                file_path.unlink()
                deleted_files.append(file_path.name)

        pycache_path = migrations_path / "__pycache__"
        if pycache_path.exists():
            shutil.rmtree(pycache_path)
            deleted_files.append("__pycache__/")

        if not deleted_files:
            return True, "No migration files to delete"

        return True, f"Deleted {len(deleted_files)} items: {', '.join(deleted_files)}"
    except Exception as exc:
        return False, f"Error deleting migrations for '{app_name}': {exc}"


def reset_all_migrations() -> tuple[int, int]:
    """Reset migrations for all configured Django apps."""
    success_count = 0
    error_count = 0

    for app_name in DJANGO_APPS:
        success, message = delete_migration_files(app_name)
        status_icon = "✓" if success else "✗"
        print(f"{status_icon} {app_name}: {message}")

        if success:
            success_count += 1
        else:
            error_count += 1

    return success_count, error_count


def main() -> None:
    """Run the migration reset script with a confirmation prompt."""
    print("WARNING: This will delete migration files for the local Django apps.")
    response = input("Do you want to continue? (yes/no): ").strip().lower()

    if response not in {"yes", "y"}:
        print("Migration reset cancelled.")
        return

    success_count, error_count = reset_all_migrations()
    print(f"Completed migration reset. Successes: {success_count}, Errors: {error_count}")


if __name__ == "__main__":
    main()
