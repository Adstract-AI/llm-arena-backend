#!/usr/bin/env python3
"""Conditionally run project setup for backend container cold starts."""

import argparse
import os

from helpers.constants import ROOT
from helpers.env_variables import AUTO_START_SETUP
from helpers.project_setup import perform_initial_setup


def should_run_auto_start_setup() -> bool:
    """Return whether AUTO_START_SETUP explicitly enables setup."""
    return AUTO_START_SETUP


def perform_cold_start_setup(auto_confirm: bool = False) -> bool:
    """Run project setup only when AUTO_START_SETUP is enabled."""
    if not should_run_auto_start_setup():
        print("AUTO_START_SETUP is not enabled. Skipping project setup.")
        return True

    print("AUTO_START_SETUP is enabled. Running project setup.")
    return perform_initial_setup(auto_confirm=auto_confirm)


def main() -> None:
    """Run the cold-start setup flow from the command line."""
    parser = argparse.ArgumentParser(description="Conditionally run project setup for cold starts.")
    parser.add_argument(
        "--full-auto",
        action="store_true",
        help="Run setup without confirmation prompts when enabled.",
    )
    args = parser.parse_args()
    perform_cold_start_setup(auto_confirm=args.full_auto)


if __name__ == "__main__":
    os.chdir(ROOT)
    main()
