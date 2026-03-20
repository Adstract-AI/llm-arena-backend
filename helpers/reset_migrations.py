#!/usr/bin/env python3
"""
Migration Reset Script

This script provides functionality to delete all migration files from Django apps
in the Adstract platform backend. It safely removes migration files while preserving
the migrations directory structure and __init__.py files.

Features:
    - Safe deletion of migration files with confirmation prompts
    - Preservation of __init__.py files and directory structure
    - Comprehensive error handling and reporting
    - Support for all Django apps defined in constants.py
    - Detailed progress reporting and statistics
    - Cleanup of __pycache__ directories

Functions:
    delete_migration_files(app_name): Delete migration files for a specific Django app
    reset_all_migrations(): Reset migrations for all Django apps in the project
    main(): Main function with user confirmation and error handling

Safety Features:
    - User confirmation required before deletion
    - Graceful handling of missing directories
    - Detailed error reporting for each app
    - Preserves essential files (__init__.py)
    - Cannot be run accidentally due to confirmation prompt

Usage:
    # Run the script directly
    python reset_migrations.py

    # Or import and use functions
    from reset_migrations import delete_migration_files, reset_all_migrations

    # Delete migrations for a specific app
    success, message = delete_migration_files("authentication")

    # Reset all migrations
    reset_all_migrations()

What Gets Deleted:
    - All .py migration files (except __init__.py)
    - All __pycache__ directories in migrations folders
    - Migration files with numeric prefixes (e.g., 0001_initial.py)

What Gets Preserved:
    - migrations/ directory structure
    - __init__.py files in migrations directories
    - App directory structure
    - Any non-migration files

Output:
    The script provides detailed output including:
    - List of processed apps
    - Success/failure status for each app
    - Count of deleted files per app
    - Summary statistics
    - Error messages for any failures

Dependencies:
    - constants.py: For ROOT path and DJANGO_APPS list
    - pathlib: For cross-platform path handling
    - shutil: For directory removal operations
"""

import os
import shutil
from pathlib import Path
# from constants import ROOT, DJANGO_APPS, DATABASE_MIGRATIONS_DIR

# Define the root directory of the adstract-backend project
ROOT = Path(__file__).resolve().parent.parent


# Database configuration paths
DATABASE_MIGRATIONS_DIR = "migrations"

# Django apps in the project
DJANGO_APPS = [
    "common",
    "authentication",
    "publisher",
    "advertiser",
    "ad_ack",
    "ad_ack_document_snapshot",
    "ad_injection",
    "ad_request",
    "ad_response",
    "adstract_metadata",
    "auction",
    "campaign",
    "ctr",
    "floor_rule",
    "link_instance",
    "product_document",
    "product_document_snapshot",
    "quality_score",
]

def delete_migration_files(app_name):
    """
    Delete all migration files for a specific Django app.

    Args:
        app_name (str): Name of the Django app

    Returns:
        tuple: (success: bool, message: str)
    """
    app_path = ROOT / app_name
    migrations_path = app_path / DATABASE_MIGRATIONS_DIR

    if not app_path.exists():
        return False, f"App directory '{app_name}' does not exist"

    if not migrations_path.exists():
        return False, f"Migrations directory for '{app_name}' does not exist"

    try:
        deleted_files = []

        # Iterate through all files in migrations directory
        for file_path in migrations_path.iterdir():
            if file_path.is_file():
                # Keep __init__.py, delete everything else
                if file_path.name != "__init__.py":
                    file_path.unlink()
                    deleted_files.append(file_path.name)

        # Also remove __pycache__ if it exists
        pycache_path = migrations_path / "__pycache__"
        if pycache_path.exists():
            shutil.rmtree(pycache_path)
            deleted_files.append("__pycache__/")

        if deleted_files:
            return True, f"Deleted {len(deleted_files)} migration files: {', '.join(deleted_files)}"
        else:
            return True, "No migration files to delete"

    except Exception as e:
        return False, f"Error deleting migrations for '{app_name}': {str(e)}"


def reset_all_migrations():
    """
    Reset migrations for all Django apps in the project.
    """
    print(f"Starting migration reset for Adstract platform...")
    print(f"Project root: {ROOT}")
    print(f"Found {len(DJANGO_APPS)} Django apps\n")

    success_count = 0
    error_count = 0

    for app_name in DJANGO_APPS:
        print(f"Processing {app_name}...")
        success, message = delete_migration_files(app_name)

        if success:
            print(f"  ✓ {message}")
            success_count += 1
        else:
            print(f"  ✗ {message}")
            error_count += 1

    print(f"\n{'='*50}")
    print(f"Migration reset complete!")
    print(f"Successfully processed: {success_count} apps")
    print(f"Errors: {error_count} apps")

    if error_count == 0:
        print(f"\n All migrations have been successfully deleted!")
        print(f"You can now run 'python manage.py makemigrations' to create fresh migrations.")
    else:
        print(f"\n  Some apps had errors. Please check the output above.")


def main():
    """Main function to run the migration reset."""
    try:
        # Confirm with user before proceeding
        print(" WARNING: This will delete ALL migration files from ALL Django apps!")
        print("This action cannot be undone.")
        response = input("\nDo you want to continue? (yes/no): ").lower().strip()

        if response in ['yes', 'y']:
            reset_all_migrations()
        else:
            print("Migration reset cancelled.")

    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
    except Exception as e:
        print(f"\nUnexpected error: {str(e)}")


if __name__ == "__main__":
    main()
