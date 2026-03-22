import os
import sys
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

from helpers.env_variables import ANTHROPIC_API_KEY, GOOGLE_API_KEY, OPENAI_API_KEY


SERVER_COMMAND_NAMES = {"runserver", "gunicorn", "uvicorn", "daphne"}


def validate_required_llm_api_keys() -> None:
    """Raise when required provider API keys are missing during server startup."""
    missing_env_names = []
    if not OPENAI_API_KEY:
        missing_env_names.append("OPENAI_API_KEY")
    # if not ANTHROPIC_API_KEY:
    #     missing_env_names.append("ANTHROPIC_API_KEY")
    # if not GOOGLE_API_KEY:
    #     missing_env_names.append("GOOGLE_API_KEY")

    if missing_env_names:
        raise ImproperlyConfigured(
            "Missing required LLM API keys: " + ", ".join(missing_env_names)
        )


def should_validate_llm_api_keys_on_startup() -> bool:
    """Return whether the current process looks like a server startup context."""
    argv = sys.argv
    executable_name = Path(argv[0]).name.lower() if argv else ""

    if any(command_name in executable_name for command_name in SERVER_COMMAND_NAMES):
        return True

    if any(argument in SERVER_COMMAND_NAMES for argument in argv[1:]):
        return True

    # Common WSGI/ASGI process startup paths that do not expose the command name cleanly.
    if os.environ.get("RUN_MAIN") == "true":
        return True

    return False
