from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATABASE_MIGRATIONS_DIR = "migrations"
DJANGO_APPS = ["common", "llm_arena"]

DEFAULT_ALLOWED_HOSTS = ["localhost", "127.0.0.1"]
DEFAULT_DJANGO_DEBUG = True
DEFAULT_DJANGO_SECRET_KEY = "django-insecure-!7lt2nkdxe=yoj)ss^#e#da*-b$s3393$_!@^7ee_(xgm%f1wd"
DEFAULT_POSTGRES_DB = "llm_arena"
DEFAULT_POSTGRES_HOST = "localhost"
DEFAULT_POSTGRES_PASSWORD = "llm_arena"
DEFAULT_POSTGRES_PORT = "5432"
DEFAULT_POSTGRES_USER = "llm_arena"
DEFAULT_TIME_ZONE = "Europe/Skopje"
TRUE_ENV_VALUES = {"1", "true", "yes", "on"}
