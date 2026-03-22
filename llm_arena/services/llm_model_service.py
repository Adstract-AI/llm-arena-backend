from django.db.models import Q, QuerySet

from common.abstract import AbstractModelService
from llm_arena.exceptions import InactiveLLMModelException, LLMModelNotFoundException
from llm_arena.models import LLMModel


class LLMModelService(AbstractModelService[LLMModel]):
    """Manage LLM catalog lookup and provider metadata for arena models."""

    def get_queryset(self) -> QuerySet[LLMModel]:
        """
        Return the base LLM model queryset with provider data preloaded.

        Returns:
            QuerySet[LLMModel]: Catalog queryset joined with provider data.
        """
        return self.model.objects.select_related("provider").all()

    def get_active_models(self) -> QuerySet[LLMModel]:
        """
        Return all active LLM models that can be used in arena battles.

        Returns:
            QuerySet[LLMModel]: Active catalog models.
        """
        return self.get_queryset().filter(is_active=True)

    def get_model_by_name(self, model_name: str, require_active: bool = True) -> LLMModel:
        """
        Resolve a catalog model by seeded name or configured provider model identifier.

        Args:
            model_name: Catalog model name or provider-facing runtime model identifier.
            require_active: When true, reject models that are marked inactive.

        Returns:
            LLMModel: The matching catalog model.

        Raises:
            LLMModelNotFoundException: If no catalog model matches the provided name.
            InactiveLLMModelException: If the matched model is inactive and require_active is true.
        """
        normalized_model_name = model_name.strip()
        if not normalized_model_name:
            raise LLMModelNotFoundException(detail="A model name is required.")

        model = (
            self.get_queryset()
            .filter(
                Q(name=normalized_model_name)
                | Q(external_model_id=normalized_model_name)
            )
            .first()
        )
        if model is None:
            raise LLMModelNotFoundException(
                detail=f"LLM model '{normalized_model_name}' was not found in the arena catalog."
            )

        if require_active and not model.is_active:
            raise InactiveLLMModelException(
                detail=f"LLM model '{model.name}' is inactive and cannot be used for inference."
            )

        return model
