import os

from dotenv import load_dotenv

from helpers.constants import (
    DEFAULT_ALLOWED_HOSTS,
    DEFAULT_DJANGO_DEBUG,
    DEFAULT_DJANGO_SECRET_KEY,
    DEFAULT_POSTGRES_DB,
    DEFAULT_POSTGRES_HOST,
    DEFAULT_POSTGRES_PASSWORD,
    DEFAULT_POSTGRES_PORT,
    DEFAULT_POSTGRES_USER,
    TRUE_ENV_VALUES,
)


def get_bool_env(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.lower() in TRUE_ENV_VALUES


def get_list_env(name: str, default: list[str]) -> list[str]:
    value = os.environ.get(name)
    if value is None:
        return default
    return [item.strip() for item in value.split(",") if item.strip()]


load_dotenv()

DJANGO_SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", DEFAULT_DJANGO_SECRET_KEY)
DJANGO_DEBUG = get_bool_env("DJANGO_DEBUG", default=DEFAULT_DJANGO_DEBUG)
DJANGO_ALLOWED_HOSTS = get_list_env("DJANGO_ALLOWED_HOSTS", default=DEFAULT_ALLOWED_HOSTS)

POSTGRES_HOST = os.environ.get("POSTGRES_HOST", DEFAULT_POSTGRES_HOST)
POSTGRES_PORT = os.environ.get("POSTGRES_PORT", DEFAULT_POSTGRES_PORT)

POSTGRES_USER = os.environ.get("POSTGRES_USER", DEFAULT_POSTGRES_USER)
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD", DEFAULT_POSTGRES_PASSWORD)
POSTGRES_DB = os.environ.get("POSTGRES_DB", DEFAULT_POSTGRES_DB)
