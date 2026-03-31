#!/usr/bin/env python3
"""Run the local application setup flow for the LLM Arena backend project."""

import argparse
import os
import subprocess
import sys
from collections.abc import Callable

from helpers.constants import ROOT


Step = tuple[str, Callable[[], subprocess.CompletedProcess[str] | bool | None]]


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
    """Ask for confirmation before a setup step."""
    if auto_confirm:
        print(f"[AUTO] Proceeding with {step_name}...")
        return True

    return input(f"Proceed with {step_name}? (y/N): ").strip().lower() == "y"


def python_command() -> list[str]:
    """Build a Python command using the currently active interpreter."""
    return [sys.executable, "manage.py"]


def create_default_superuser() -> subprocess.CompletedProcess[str] | None:
    """Create or update the default local admin superuser."""
    shell_code = (
        "from django.contrib.auth import get_user_model;"
        "User = get_user_model();"
        "user, _ = User.objects.get_or_create(username='admin', defaults={'is_staff': True, 'is_superuser': True});"
        "user.is_staff = True;"
        "user.is_superuser = True;"
        "user.set_password('admin');"
        "user.save();"
        "print('Default admin superuser is ready.')"
    )
    return run_command(python_command() + ["shell", "-c", shell_code])


def execute_steps(steps: list[Step], auto_confirm: bool = False) -> bool:
    """Execute a list of setup steps in order."""
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

    return True


def build_initial_setup_steps() -> list[Step]:
    """Build the shared non-destructive application setup steps."""
    return [
        ("Running migrations", lambda: run_command(python_command() + ["migrate"])),
        ("Collecting static files", lambda: run_command(python_command() + ["collectstatic", "--noinput"])),
        ("Seeding LLM providers", lambda: run_command(python_command() + ["seed_llm_providers"])),
        ("Seeding LLM models", lambda: run_command(python_command() + ["seed_llm_models"])),
        (
            "Seeding experimental parameter sampling specs",
            lambda: run_command(python_command() + ["seed_experiment_sampling_specs"]),
        ),
        ("Creating default admin user", create_default_superuser),
    ]


def perform_initial_setup(auto_confirm: bool = False) -> bool:
    """Run the local application setup flow for this project."""
    print("=" * 50)
    print("LLM ARENA PROJECT SETUP")
    print("=" * 50)
    print(
        "This will apply migrations, collect static files, seed the catalog and "
        "experimental sampling specs, and create the default admin user."
    )
    print("=" * 50)

    return execute_steps(build_initial_setup_steps(), auto_confirm=auto_confirm)


def main() -> None:
    """Run the local project setup flow from the command line."""
    parser = argparse.ArgumentParser(description="Set up the local LLM Arena project.")
    parser.add_argument(
        "--full-auto",
        action="store_true",
        help="Run all steps without confirmation prompts.",
    )
    args = parser.parse_args()
    perform_initial_setup(auto_confirm=args.full_auto)


if __name__ == "__main__":
    os.chdir(ROOT)
    main()
