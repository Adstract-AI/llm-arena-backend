#!/usr/bin/env python3
"""
Django Database Hard Reset Script
This script completely resets the database and recreates everything from scratch.
"""

import argparse
import subprocess
import sys
import time
import os
from pathlib import Path
# from constants import ROOT

# Define the root directory of the adstract-backend project
ROOT = Path(__file__).resolve().parent.parent


def run_command(command, shell=True, capture_output=False):
    """Run a shell command and return the result."""
    try:
        result = subprocess.run(
            command,
            shell=shell,
            capture_output=capture_output,
            text=True,
            check=True
        )
        return result
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {command}")
        print(f"Return code: {e.returncode}")
        if capture_output:
            print(f"stdout: {e.stdout}")
            print(f"stderr: {e.stderr}")
        return None


def confirm_step(step_name, auto_confirm=False):
    """Ask for confirmation before proceeding with a step."""
    if auto_confirm:
        print(f"[AUTO] Proceeding with {step_name}...")
        return True

    response = input(f"Proceed with {step_name}? (y/N): ").strip().lower()
    return response == 'y'


def wait_for_postgres():
    """Wait for PostgreSQL to be ready."""
    print("Waiting for PostgreSQL to be ready...")
    max_attempts = 30
    attempt = 1

    while attempt <= max_attempts:
        result = run_command(
            "docker-compose exec postgres pg_isready -U postgres -d adstract_db",
            capture_output=True
        )

        if result and result.returncode == 0:
            print("PostgreSQL is ready!")
            return True

        print(f"Attempt {attempt}/{max_attempts}: PostgreSQL not ready yet...")
        time.sleep(3)
        attempt += 1

    print("ERROR: PostgreSQL failed to start within the timeout period")
    return False


def main():
    parser = argparse.ArgumentParser(description="Django Database Hard Reset Script")
    parser.add_argument(
        "--full-auto",
        action="store_true",
        help="Run all steps without confirmation prompts"
    )
    parser.add_argument(
        "--no-reset-vector-store",
        action="store_true",
        help="Skip vector store reset"
    )
    parser.add_argument(
        "--vector-collection",
        type=str,
        default="product_documents",
        help="Vector collection name to reset (default: product_documents)"
    )
    args = parser.parse_args()

    auto_confirm = args.full_auto
    reset_vector_store = not args.no_reset_vector_store
    vector_collection = args.vector_collection

    print("=" * 50)
    print("DATABASE HARD RESET SCRIPT")
    print("=" * 50)
    print("This will completely reset your database!")
    print("All data will be lost!")
    print("=" * 50)

    if not auto_confirm:
        confirm = input("Are you sure you want to continue? (y/N): ").strip().lower()
        if confirm != 'y':
            print("Operation cancelled.")
            sys.exit(1)
    else:
        print("[AUTO] Starting database reset process...")

    # Change to the project root directory
    project_root = ROOT
    os.chdir(project_root)
    print(f"Working directory: {os.getcwd()}")

    # Build steps list based on options
    steps = [
        ("Stopping Django development server", lambda: print("Please manually stop the Django server if it's running")),
        ("Running delete migrations script", delete_migrations),
        ("Stopping PostgreSQL container", lambda: run_command("docker-compose down")),
        ("Removing PostgreSQL volume", remove_postgres_volume),
        ("Starting PostgreSQL container", lambda: run_command("docker-compose up -d")),
        ("Waiting for PostgreSQL to be ready", wait_for_postgres),
        ("Making migrations", lambda: run_command("python manage.py makemigrations")),
        ("Running migrations", lambda: run_command("python manage.py migrate")),
        ("Creating common entities", lambda: run_command("python manage.py createcommonentities --force")),
        ("Creating OpenAI model catalog", lambda: run_command("python manage.py createopenaimodelcatalog")),
        ("Creating runtime constants", lambda: run_command("python manage.py createconstants")),
        ("Creating superuser", create_superuser),
        ("Creating advertiser types", lambda: run_command("python manage.py createadvertisertypes --force")),
        ("Creating product categories", lambda: run_command("python manage.py createproductcategories --force")),
        ("Creating platform entities", lambda: run_command("python manage.py createcampaignentities --force")),
        ("Creating ad injection entities", lambda: run_command("python manage.py createadinjectionentities --force")),
        ("Setting up permissions", lambda: run_command("python manage.py seed_privileges --assign-defaults")),
        ("Syncing privileges (safe)", lambda: run_command("python manage.py sync_privileges")),
        ("Setting up publisher types", lambda: run_command("python manage.py createpublisherentities --force")),
        ("Creating notification preferences", lambda: run_command("python manage.py create_notification_preferences")),
    ]

    # Add vector store reset step if requested
    if reset_vector_store:
        steps.append((f"Resetting vector store collection ({vector_collection})", lambda: reset_vector_store_fn(vector_collection)))

    for i, (step_name, step_function) in enumerate(steps, 1):
        print(f"\n[{i}/{len(steps)}] {step_name}...")

        if not confirm_step(step_name, auto_confirm):
            print(f"Skipping {step_name}")
            continue

        try:
            result = step_function()
            if result is False:
                print(f"ERROR: {step_name} failed!")
                if not auto_confirm:
                    continue_anyway = input("Continue with remaining steps? (y/N): ").strip().lower()
                    if continue_anyway != 'y':
                        print("Aborting script.")
                        sys.exit(1)
                else:
                    print("Continuing with remaining steps...")
            else:
                print(f"✓ {step_name} completed successfully")

        except Exception as e:
            print(f"ERROR during {step_name}: {str(e)}")
            if not auto_confirm:
                continue_anyway = input("Continue with remaining steps? (y/N): ").strip().lower()
                if continue_anyway != 'y':
                    print("Aborting script.")
                    sys.exit(1)
            else:
                print("Continuing with remaining steps...")

    print("\n" + "=" * 50)
    print("DATABASE HARD RESET COMPLETED!")
    print("=" * 50)
    print("Superuser credentials:")
    print("Username: admin")
    print("Email: admin@admin.com")
    print("Password: admin")
    if reset_vector_store:
        print("=" * 50)
        print("Vector Store:")
        print(f"Collection '{vector_collection}' has been reset and initialized")
        print("Ready for product document embeddings")
    print("=" * 50)


def delete_migrations():
    """Run the delete migrations script if it exists."""
    migrations_script = Path("helper_functions/reset_migrations.py")
    if migrations_script.exists():
        return run_command("python helper_functions/reset_migrations.py")
    else:
        print("Warning: reset_migrations.py not found, skipping...")
        return True


def remove_postgres_volume():
    """Remove the PostgreSQL Docker volume."""
    result = run_command("docker volume rm adstract-backend_postgres_data", capture_output=True)
    if result is None or result.returncode != 0:
        print("Warning: Volume might not exist or already removed")
    return True


def create_superuser():
    """Create a superuser account using the fastcreatesuperuser command."""
    result = run_command("python manage.py fastcreatesuperuser")
    return result is not None


def reset_vector_store_fn(collection_name):
    """Reset the vector store collection."""
    print(f"Resetting vector store collection: {collection_name}")

    # Check if collection exists and delete it
    check_result = run_command(f"python manage.py vector_store info --collection {collection_name}", capture_output=True)
    if check_result and "Collection exists" in check_result.stdout:
        print(f"Found existing collection '{collection_name}', deleting...")
        # Use cleanup command to delete the collection
        delete_result = run_command(f"echo 'yes' | python manage.py vector_store cleanup --collection {collection_name}")
        if delete_result is None:
            print(f"Warning: Failed to delete collection '{collection_name}' (may not exist or environment restrictions)")
    else:
        print(f"Collection '{collection_name}' does not exist, skipping deletion")

    # Create the collection
    print(f"Creating collection '{collection_name}'...")
    create_result = run_command(f"python manage.py vector_store init --collection {collection_name}")
    if create_result is None:
        print(f"ERROR: Failed to create collection '{collection_name}'")
        return False

    print(f"✓ Vector store collection '{collection_name}' reset successfully")
    return True


if __name__ == "__main__":
    main()
