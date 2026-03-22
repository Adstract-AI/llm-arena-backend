from django.apps import AppConfig


class LlmArenaConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'llm_arena'

    def ready(self) -> None:
        from llm_arena.startup import (
            should_validate_llm_api_keys_on_startup,
            validate_required_llm_api_keys,
        )

        if should_validate_llm_api_keys_on_startup():
            validate_required_llm_api_keys()
