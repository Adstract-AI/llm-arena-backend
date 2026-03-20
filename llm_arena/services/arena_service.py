import logging
import random
from typing import Sequence
from uuid import UUID

from django.db import transaction
from django.utils import timezone

from common.abstract import AbstractService
from llm_arena.exceptions import (
    ArenaBattleAlreadyVotedException,
    ArenaBattleGenerationFailedException,
    ArenaBattleNotFoundException,
    ArenaBattleNotReadyForVoteException,
    InsufficientActiveLLMModelsException,
    LLMInferenceException,
)
from llm_arena.models import ArenaBattle, BattleResponse, BattleVote, LLMModel
from llm_arena.services.inference_service import ArenaInferenceService
from llm_arena.services.llm_model_service import LLMModelService

logger = logging.getLogger(__name__)


class ArenaService(AbstractService):
    """Own battle creation, model execution, persistence, and vote submission workflows."""

    llm_model_service = LLMModelService()
    inference_service = ArenaInferenceService()

    @transaction.atomic
    def create_battle(self, prompt: str) -> ArenaBattle:
        """
        Create a battle, run two random active models, and persist all generated outputs.

        Args:
            prompt: The user prompt to compare across two models.

        Returns:
            ArenaBattle: The completed persisted battle.

        Raises:
            InsufficientActiveLLMModelsException: If fewer than two active models are available.
            ArenaBattleGenerationFailedException: If one or more model generations fail.
        """
        normalized_prompt = prompt.strip()
        if not normalized_prompt:
            raise LLMInferenceException(detail="A prompt is required to create a battle.")

        selected_models = self._select_random_models()
        battle = ArenaBattle.objects.create(
            prompt=normalized_prompt,
            status=ArenaBattle.BattleStatus.CREATED,
        )

        shuffled_slots = list(BattleResponse.ResponseSlot.values)
        random.shuffle(shuffled_slots)
        persisted_responses = self._create_pending_responses(
            battle=battle,
            selected_models=selected_models,
            shuffled_slots=shuffled_slots,
        )

        generation_errors: list[str] = []
        for persisted_response in persisted_responses:
            try:
                response_details = self.inference_service.generate_response_details(
                    model=persisted_response.llm_model,
                    prompt=normalized_prompt,
                )
                persisted_response.response_text = response_details["response_text"]
                persisted_response.status = BattleResponse.ResponseStatus.COMPLETED
                persisted_response.error_message = None
                persisted_response.finish_reason = response_details["finish_reason"]
                persisted_response.prompt_tokens = response_details["prompt_tokens"]
                persisted_response.completion_tokens = response_details["completion_tokens"]
                persisted_response.total_tokens = response_details["total_tokens"]
                persisted_response.raw_metadata = response_details["raw_metadata"]
                persisted_response.save()
            except LLMInferenceException as exc:
                logger.exception(
                    f"Battle generation failed for battle {battle.battle_id} and model "
                    f"{persisted_response.llm_model.name}"
                )
                persisted_response.status = BattleResponse.ResponseStatus.FAILED
                persisted_response.error_message = str(exc.detail)
                persisted_response.finish_reason = None
                persisted_response.save()
                generation_errors.append(str(exc.detail))
            except Exception as exc:
                logger.exception(
                    f"Unexpected battle generation failure for battle {battle.battle_id} and model "
                    f"{persisted_response.llm_model.name}"
                )
                persisted_response.status = BattleResponse.ResponseStatus.FAILED
                persisted_response.error_message = "Model generation failed."
                persisted_response.finish_reason = None
                persisted_response.save()
                generation_errors.append("Model generation failed.")

        if generation_errors:
            battle.status = ArenaBattle.BattleStatus.FAILED
            battle.error_message = " | ".join(generation_errors)
            battle.completed_at = timezone.now()
            battle.save()
            raise ArenaBattleGenerationFailedException()

        battle.status = ArenaBattle.BattleStatus.AWAITING_VOTE
        battle.error_message = None
        battle.completed_at = timezone.now()
        battle.save()
        return battle

    @transaction.atomic
    def submit_vote(self, battle_id: UUID, choice: str, feedback: str = "") -> BattleVote:
        """
        Persist a vote for a completed battle that has not been voted on yet.

        Args:
            battle_id: Public UUID identifier for the battle.
            choice: The selected vote choice.
            feedback: Optional free-text user feedback.

        Returns:
            BattleVote: The persisted vote instance.

        Raises:
            ArenaBattleNotFoundException: If the battle UUID does not exist.
            ArenaBattleNotReadyForVoteException: If the battle is not completed.
            ArenaBattleAlreadyVotedException: If a vote already exists for the battle.
        """
        battle = self.get_battle_by_battle_id(battle_id)
        if battle.status != ArenaBattle.BattleStatus.AWAITING_VOTE:
            raise ArenaBattleNotReadyForVoteException()

        if hasattr(battle, "vote"):
            raise ArenaBattleAlreadyVotedException()

        vote = BattleVote.objects.create(
            battle=battle,
            choice=choice,
            feedback=feedback.strip(),
        )
        battle.status = ArenaBattle.BattleStatus.COMPLETED
        battle.save(update_fields=["status", "updated_at"])
        return vote

    def get_battle_by_battle_id(self, battle_id: UUID) -> ArenaBattle:
        """
        Retrieve a battle by its public UUID with related responses and vote preloaded.

        Args:
            battle_id: Public UUID identifier for the battle.

        Returns:
            ArenaBattle: The matched persisted battle.

        Raises:
            ArenaBattleNotFoundException: If no battle matches the provided UUID.
        """
        battle = (
            ArenaBattle.objects
            .prefetch_related("responses__llm_model__provider")
            .select_related("vote")
            .filter(battle_id=battle_id)
            .first()
        )
        if battle is None:
            raise ArenaBattleNotFoundException()
        return battle

    def _select_random_models(self) -> list[LLMModel]:
        """
        Select two random active models for a new battle.

        Returns:
            list[LLMModel]: Two distinct active models.

        Raises:
            InsufficientActiveLLMModelsException: If fewer than two active models are available.
        """
        active_models = list(self.llm_model_service.get_active_models())
        if len(active_models) < 2:
            raise InsufficientActiveLLMModelsException()
        return random.sample(active_models, 2)

    @staticmethod
    def _create_pending_responses(
        battle: ArenaBattle,
        selected_models: Sequence[LLMModel],
        shuffled_slots: Sequence[str],
    ) -> list[BattleResponse]:
        """
        Create pending response rows for the selected models and slot assignment.

        Args:
            battle: The battle that owns the generated responses.
            selected_models: The two selected models for this battle.
            shuffled_slots: The randomized response slots to assign.

        Returns:
            list[BattleResponse]: Persisted response rows in slot order.
        """
        created_responses: list[BattleResponse] = []
        for index, llm_model in enumerate(selected_models):
            created_responses.append(
                BattleResponse.objects.create(
                    battle=battle,
                    llm_model=llm_model,
                    slot=shuffled_slots[index],
                    status=BattleResponse.ResponseStatus.PENDING,
                )
            )
        return created_responses
