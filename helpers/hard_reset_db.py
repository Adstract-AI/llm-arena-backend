#!/usr/bin/env python3
"""Reset the local Postgres database and reseed the arena catalog."""

import argparse
import os
import subprocess
import sys
import time

from helpers.constants import ROOT
from helpers.env_variables import POSTGRES_DB, POSTGRES_USER


def run_command(command: list[str], capture_output: bool = False) -> subprocess.CompletedProcess[str] | None:
    """Run a subprocess command from the project root."""
    try:
        return subprocess.run(
            command,
            cwd=ROOT,
            capture_output=capture_output,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        print(f"Error running command: {' '.join(command)}")
        print(f"Return code: {exc.returncode}")
        if capture_output:
            print(f"stdout: {exc.stdout}")
            print(f"stderr: {exc.stderr}")
        return None


def confirm_step(step_name: str, auto_confirm: bool = False) -> bool:
    """Ask for confirmation before a destructive step."""
    if auto_confirm:
        print(f"[AUTO] Proceeding with {step_name}...")
        return True

    return input(f"Proceed with {step_name}? (y/N): ").strip().lower() == "y"


def wait_for_postgres() -> bool:
    """Wait for the dockerized Postgres service to become ready."""
    max_attempts = 30

    for attempt in range(1, max_attempts + 1):
        result = run_command(
            ["docker", "compose", "exec", "db", "pg_isready", "-U", POSTGRES_USER, "-d", POSTGRES_DB],
            capture_output=True,
        )
        if result is not None and result.returncode == 0:
            print("PostgreSQL is ready.")
            return True

        print(f"Attempt {attempt}/{max_attempts}: PostgreSQL not ready yet...")
        time.sleep(2)

    print("ERROR: PostgreSQL failed to start within the timeout period.")
    return False


def python_command() -> list[str]:
    """Build a Python command using the currently active interpreter."""
    return [sys.executable, "manage.py"]


def perform_hard_reset(auto_confirm: bool = False) -> bool:
    """Run the local database reset flow for this project."""

    print("=" * 50)
    print("LLM ARENA DATABASE HARD RESET")
    print("=" * 50)
    print("This will reset the local dockerized PostgreSQL database.")
    print("=" * 50)

    if not auto_confirm:
        confirm = input("Are you sure you want to continue? (y/N): ").strip().lower()
        if confirm != "y":
            print("Operation cancelled.")
            return False

    steps = [
        ("Resetting migration files", lambda: run_command(python_command() + ["reset_migrations", "--noinput"])),
        ("Stopping Docker services and removing volumes", lambda: run_command(["docker", "compose", "down", "-v"])),
        ("Starting PostgreSQL service", lambda: run_command(["docker", "compose", "up", "-d", "db"])),
        ("Waiting for PostgreSQL to be ready", wait_for_postgres),
        ("Running migrations", lambda: run_command(python_command() + ["migrate"])),
        ("Seeding LLM catalog", lambda: run_command(python_command() + ["seed_llm_catalog"])),
    ]

    for index, (step_name, step_function) in enumerate(steps, start=1):
        print(f"\n[{index}/{len(steps)}] {step_name}...")

        if not confirm_step(step_name, auto_confirm=auto_confirm):
            print(f"Skipping {step_name}.")
            continue

        result = step_function()
        if result is False or result is None:
            print(f"ERROR: {step_name} failed.")
            return False

        print(f"✓ {step_name} completed successfully")

    print("\nDatabase reset completed.")
    return True


def main() -> None:
    """Run the local database reset flow from the command line."""
    parser = argparse.ArgumentParser(description="Reset the local LLM Arena database.")
    parser.add_argument(
        "--full-auto",
        action="store_true",
        help="Run all steps without confirmation prompts.",
    )
    args = parser.parse_args()
    perform_hard_reset(auto_confirm=args.full_auto)


if __name__ == "__main__":
    os.chdir(ROOT)
    main()
