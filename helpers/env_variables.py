import os

from dotenv import load_dotenv

from helpers.constants import (
    DEFAULT_ALLOWED_HOSTS,
    DEFAULT_AUTO_START_SETUP,
    DEFAULT_CORS_ALLOWED_ORIGINS,
    DEFAULT_CSRF_TRUSTED_ORIGINS,
    DEFAULT_DJANGO_DEBUG,
    DEFAULT_DJANGO_SECRET_KEY,
    DEFAULT_FINKI_BASE_URL,
    DEFAULT_JWT_ACCESS_TOKEN_LIFETIME_MINUTES,
    DEFAULT_JWT_REFRESH_TOKEN_LIFETIME_DAYS,
    DEFAULT_LLM_REQUEST_TIMEOUT_SECONDS,
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


def get_int_env(name: str, default: int) -> int:
    value = os.environ.get(name)
    if value is None:
        return default
    return int(value)


def append_unique(values: list[str], value: str) -> list[str]:
    if value and value not in values:
        values.append(value)
    return values


load_dotenv()

DJANGO_SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", DEFAULT_DJANGO_SECRET_KEY)
DJANGO_DEBUG = get_bool_env("DJANGO_DEBUG", default=DEFAULT_DJANGO_DEBUG)
DJANGO_ALLOWED_HOSTS = get_list_env("DJANGO_ALLOWED_HOSTS", default=DEFAULT_ALLOWED_HOSTS)
CORS_ALLOWED_ORIGINS = get_list_env("CORS_ALLOWED_ORIGINS", default=DEFAULT_CORS_ALLOWED_ORIGINS)
CSRF_TRUSTED_ORIGINS = get_list_env("CSRF_TRUSTED_ORIGINS", default=DEFAULT_CSRF_TRUSTED_ORIGINS)
RENDER_EXTERNAL_HOSTNAME = os.environ.get("RENDER_EXTERNAL_HOSTNAME", "").strip()

if RENDER_EXTERNAL_HOSTNAME:
    append_unique(DJANGO_ALLOWED_HOSTS, RENDER_EXTERNAL_HOSTNAME)
    append_unique(CSRF_TRUSTED_ORIGINS, f"https://{RENDER_EXTERNAL_HOSTNAME}")

POSTGRES_HOST = os.environ.get("POSTGRES_HOST", DEFAULT_POSTGRES_HOST)
POSTGRES_PORT = os.environ.get("POSTGRES_PORT", DEFAULT_POSTGRES_PORT)

POSTGRES_USER = os.environ.get("POSTGRES_USER", DEFAULT_POSTGRES_USER)
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD", DEFAULT_POSTGRES_PASSWORD)
POSTGRES_DB = os.environ.get("POSTGRES_DB", DEFAULT_POSTGRES_DB)

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")
GOOGLE_OAUTH_CLIENT_ID = os.environ.get("GOOGLE_OAUTH_CLIENT_ID", "").strip()
GOOGLE_OAUTH_CLIENT_SECRET = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET", "").strip()
GOOGLE_OAUTH_REDIRECT_URI = os.environ.get("GOOGLE_OAUTH_REDIRECT_URI", "").strip()
GITHUB_OAUTH_CLIENT_ID = os.environ.get("GITHUB_OAUTH_CLIENT_ID", "").strip()
GITHUB_OAUTH_CLIENT_SECRET = os.environ.get("GITHUB_OAUTH_CLIENT_SECRET", "").strip()
GITHUB_OAUTH_REDIRECT_URI = os.environ.get("GITHUB_OAUTH_REDIRECT_URI", "").strip()

AUTO_START_SETUP = get_bool_env("AUTO_START_SETUP", default=DEFAULT_AUTO_START_SETUP)
FINKI_BASE_URL = os.environ.get("FINKI_BASE_URL", DEFAULT_FINKI_BASE_URL)
JWT_ACCESS_TOKEN_LIFETIME_MINUTES = get_int_env(
    "JWT_ACCESS_TOKEN_LIFETIME_MINUTES",
    default=DEFAULT_JWT_ACCESS_TOKEN_LIFETIME_MINUTES,
)
JWT_REFRESH_TOKEN_LIFETIME_DAYS = get_int_env(
    "JWT_REFRESH_TOKEN_LIFETIME_DAYS",
    default=DEFAULT_JWT_REFRESH_TOKEN_LIFETIME_DAYS,
)
LLM_REQUEST_TIMEOUT_SECONDS = get_int_env(
    "LLM_REQUEST_TIMEOUT_SECONDS",
    default=DEFAULT_LLM_REQUEST_TIMEOUT_SECONDS,
)
