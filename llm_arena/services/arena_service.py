import logging
import random
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from django.db import transaction
from django.db.models import Max, Prefetch
from django.utils import timezone

from common.abstract import AbstractService
from experimental_llm_arena.models import ExperimentConfig
from llm_arena.exceptions import (
    ArenaBattleAlreadyVotedException,
    ArenaBattleGenerationFailedException,
    ArenaBattleNotContinuableException,
    ArenaBattleNotFoundException,
    ArenaBattleNotReadyForVoteException,
    InsufficientActiveLLMModelsException,
    LLMInferenceException,
)
from llm_arena.models import ArenaBattle, ArenaTurn, BattleResponse, BattleVote, LLMModel
from llm_arena.services.inference_service import ArenaInferenceService
from llm_arena.services.llm_model_service import LLMModelService

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ArenaHistoryMessage:
    """Minimal history message adapter for inference service conversation memory."""

    role: str
    content: str


class ArenaService(AbstractService):
    """Own battle creation, continuation, persistence, transcript shaping, and voting."""

    llm_model_service = LLMModelService()
    inference_service = ArenaInferenceService()

    def create_battle(self, prompt: str) -> ArenaBattle:
        """
        Create a new battle, run the first turn for both selected models, and persist the transcript.

        Args:
            prompt: The initial user prompt for the conversation battle.

        Returns:
            ArenaBattle: Persisted battle with its first completed turn.

        Raises:
            InsufficientActiveLLMModelsException: If fewer than two active models are available.
            ArenaBattleGenerationFailedException: If one or more model generations fail.
        """
        normalized_prompt = self._normalize_prompt(prompt)
        model_a, model_b = self._select_random_models()
        return self.create_battle_with_models(
            prompt=normalized_prompt,
            model_a=model_a,
            model_b=model_b,
        )

    def create_battle_with_models(
        self,
        prompt: str,
        model_a: LLMModel,
        model_b: LLMModel,
        experiment_config_fields: dict[str, Any] | None = None,
    ) -> ArenaBattle:
        """
        Create a new battle for explicitly selected models and run the first turn.

        Args:
            prompt: The initial user prompt for the conversation battle.
            model_a: Fixed model assigned to slot A.
            model_b: Fixed model assigned to slot B.
            experiment_config_fields: Optional experiment config fields to persist before generation.

        Returns:
            ArenaBattle: Persisted battle with its first completed turn.
        """
        normalized_prompt = self._normalize_prompt(prompt)
        battle = ArenaBattle.objects.create(
            model_a=model_a,
            model_b=model_b,
            status=ArenaBattle.BattleStatus.IN_PROGRESS,
            error_message=None,
            completed_at=None,
        )
        if experiment_config_fields is not None:
            ExperimentConfig.objects.create(
                battle=battle,
                **experiment_config_fields,
            )

        turn = self._create_turn(battle=battle, prompt=normalized_prompt)
        self._generate_turn(battle=battle, turn=turn)
        return self.get_battle(battle.id)

    def continue_battle(self, battle_id: UUID, prompt: str) -> ArenaBattle:
        """
        Continue an existing battle with a new prompt turn for both fixed models.

        Args:
            battle_id: UUID primary key for the battle.
            prompt: The follow-up user prompt to append to the battle.

        Returns:
            ArenaBattle: Persisted battle including the new completed turn.

        Raises:
            ArenaBattleNotFoundException: If the battle UUID does not exist.
            ArenaBattleNotContinuableException: If the battle is terminal.
            ArenaBattleGenerationFailedException: If one or more model generations fail.
        """
        normalized_prompt = self._normalize_prompt(prompt)
        battle = self.get_battle(battle_id)
        self._validate_battle_can_continue(battle)

        battle.status = ArenaBattle.BattleStatus.IN_PROGRESS
        battle.error_message = None
        battle.save(update_fields=["status", "error_message", "updated_at"])

        turn = self._create_turn(battle=battle, prompt=normalized_prompt)
        self._generate_turn(battle=battle, turn=turn)
        return self.get_battle(battle.id)

    @transaction.atomic
    def submit_vote(self, battle_id: UUID, choice: str, feedback: str = "") -> BattleVote:
        """
        Persist a vote for a battle transcript that is ready for voting.

        Args:
            battle_id: UUID primary key for the battle.
            choice: The selected vote choice.
            feedback: Optional free-text user feedback.

        Returns:
            BattleVote: The persisted vote instance.

        Raises:
            ArenaBattleNotFoundException: If the battle UUID does not exist.
            ArenaBattleNotReadyForVoteException: If the battle is not ready for voting.
            ArenaBattleAlreadyVotedException: If a vote already exists for the battle.
        """
        battle = self._get_battle_for_update(battle_id)
        if battle.status != ArenaBattle.BattleStatus.AWAITING_VOTE:
            raise ArenaBattleNotReadyForVoteException()

        if BattleVote.objects.filter(battle=battle).exists():
            raise ArenaBattleAlreadyVotedException()

        vote = BattleVote.objects.create(
            battle=battle,
            choice=choice,
            feedback=feedback.strip(),
        )
        battle.status = ArenaBattle.BattleStatus.COMPLETED
        battle.completed_at = timezone.now()
        battle.save(update_fields=["status", "completed_at", "updated_at"])
        return vote

    def get_battle(self, battle_id: UUID) -> ArenaBattle:
        """
        Retrieve a battle by UUID with all battle-level relations preloaded.

        Args:
            battle_id: UUID primary key for the battle.

        Returns:
            ArenaBattle: The matched persisted battle.

        Raises:
            ArenaBattleNotFoundException: If no battle matches the provided UUID.
        """
        battle = (
            ArenaBattle.objects
            .select_related("model_a__provider", "model_b__provider", "experiment_config")
            .prefetch_related(
                Prefetch(
                    "turns",
                    queryset=(
                        ArenaTurn.objects.order_by("turn_number")
                        .prefetch_related(
                            Prefetch(
                                "responses",
                                queryset=BattleResponse.objects.order_by("slot"),
                            )
                        )
                    ),
                )
            )
            .filter(id=battle_id)
            .first()
        )
        if battle is None:
            raise ArenaBattleNotFoundException()
        return battle

    def build_battle_snapshot(self, battle: ArenaBattle) -> dict[str, Any]:
        """
        Build the anonymous battle transcript payload returned by create, continue, and detail endpoints.

        Args:
            battle: Persisted battle with turns and responses preloaded.

        Returns:
            dict[str, Any]: Public battle snapshot without model identity reveal.
        """
        return {
            "id": battle.id,
            "status": battle.status,
            "can_vote": battle.status == ArenaBattle.BattleStatus.AWAITING_VOTE,
            "turns": [
                {
                    "turn_number": turn.turn_number,
                    "prompt": turn.prompt,
                    "responses": [
                        {
                            "slot": response.slot,
                            "response_text": response.response_text,
                        }
                        for response in turn.responses.all()
                    ],
                }
                for turn in battle.turns.all()
            ],
        }

    def build_vote_snapshot(self, battle: ArenaBattle) -> dict[str, Any]:
        """
        Build the revealed battle transcript payload returned by the vote endpoint.

        Args:
            battle: Persisted battle with vote, turns, and model relations available.

        Returns:
            dict[str, Any]: Vote response payload with revealed model identities.
        """
        vote = battle.vote
        winner_model = self._get_winner_model(battle=battle, choice=vote.choice)
        response_payload = {
            "id": battle.id,
            "status": battle.status,
            "choice": vote.choice,
            "feedback": vote.feedback,
            "winner_provider_name": winner_model.provider.name if winner_model else None,
            "winner_model_name": winner_model.name if winner_model else None,
            "models": [
                self._build_revealed_model_entry(
                    slot=BattleResponse.ResponseSlot.A,
                    model=battle.model_a,
                    winning_slot=vote.choice,
                ),
                self._build_revealed_model_entry(
                    slot=BattleResponse.ResponseSlot.B,
                    model=battle.model_b,
                    winning_slot=vote.choice,
                ),
            ],
            "turns": [
                {
                    "turn_number": turn.turn_number,
                    "prompt": turn.prompt,
                    "responses": [
                        {
                            "slot": response.slot,
                            "response_text": response.response_text,
                            "is_winner": vote.choice != BattleVote.VoteChoice.TIE and response.slot == vote.choice,
                        }
                        for response in turn.responses.all()
                    ],
                }
                for turn in battle.turns.all()
            ],
        }
        experiment_payload = self._build_experiment_reveal_payload(
            self._get_experiment_config(battle)
        )
        if experiment_payload is not None:
            response_payload["experiment"] = experiment_payload
        return response_payload

    def _generate_turn(self, battle: ArenaBattle, turn: ArenaTurn) -> None:
        """
        Generate both slot responses for a turn and update battle/turn state accordingly.

        Args:
            battle: Parent battle containing the fixed slot-to-model mapping.
            turn: Newly created turn awaiting generation.

        Raises:
            ArenaBattleGenerationFailedException: If either model generation fails.
        """
        responses = {
            response.slot: response
            for response in BattleResponse.objects.filter(turn=turn).order_by("slot")
        }
        generation_errors: list[str] = []

        for slot in BattleResponse.ResponseSlot.values:
            persisted_response = responses[slot]
            llm_model = battle.get_model_for_slot(slot)
            history_messages = self._build_slot_history_messages(
                battle=battle,
                slot=slot,
            )

            try:
                generation_config = self._get_slot_generation_config(
                    battle=battle,
                    slot=slot,
                )
                response_details = self.inference_service.generate_response_details_with_history(
                    model=llm_model,
                    history_messages=history_messages,
                    prompt=turn.prompt,
                    generation_config=generation_config,
                )
                persisted_response.response_text = response_details["response_text"]
                persisted_response.status = BattleResponse.ResponseStatus.COMPLETED
                persisted_response.error_message = None
                persisted_response.finish_reason = response_details["finish_reason"] or None
                persisted_response.prompt_tokens = response_details["prompt_tokens"]
                persisted_response.completion_tokens = response_details["completion_tokens"]
                persisted_response.total_tokens = response_details["total_tokens"]
                persisted_response.raw_metadata = response_details["raw_metadata"]
                persisted_response.save()
            except LLMInferenceException as exc:
                logger.exception(
                    f"Battle turn generation failed for battle {battle.id}, turn {turn.turn_number}, "
                    f"slot {slot}, and model {llm_model.name}"
                )
                persisted_response.status = BattleResponse.ResponseStatus.FAILED
                persisted_response.error_message = str(exc.detail)
                persisted_response.finish_reason = None
                persisted_response.save()
                generation_errors.append(str(exc.detail))
            except Exception:
                logger.exception(
                    f"Unexpected battle turn generation failure for battle {battle.id}, "
                    f"turn {turn.turn_number}, slot {slot}, and model {llm_model.name}"
                )
                persisted_response.status = BattleResponse.ResponseStatus.FAILED
                persisted_response.error_message = "Model generation failed."
                persisted_response.finish_reason = None
                persisted_response.save()
                generation_errors.append("Model generation failed.")

        if generation_errors:
            turn.status = ArenaTurn.TurnStatus.FAILED
            turn.error_message = " | ".join(generation_errors)
            turn.save(update_fields=["status", "error_message", "updated_at"])

            battle.status = ArenaBattle.BattleStatus.FAILED
            battle.error_message = turn.error_message
            battle.completed_at = timezone.now()
            battle.save(update_fields=["status", "error_message", "completed_at", "updated_at"])
            raise ArenaBattleGenerationFailedException()

        turn.status = ArenaTurn.TurnStatus.COMPLETED
        turn.error_message = None
        turn.save(update_fields=["status", "error_message", "updated_at"])

        battle.status = ArenaBattle.BattleStatus.AWAITING_VOTE
        battle.error_message = None
        battle.completed_at = None
        battle.save(update_fields=["status", "error_message", "completed_at", "updated_at"])

    def _build_slot_history_messages(self, battle: ArenaBattle, slot: str) -> list[ArenaHistoryMessage]:
        """
        Build the slot-specific conversation history for a battle continuation.

        Args:
            battle: Parent battle whose prior completed turns should be replayed.
            slot: Slot whose assistant responses should be included.

        Returns:
            list[ArenaHistoryMessage]: Ordered conversation history for the selected slot.
        """
        completed_turns = (
            ArenaTurn.objects
            .filter(
                battle=battle,
                status=ArenaTurn.TurnStatus.COMPLETED,
            )
            .prefetch_related(
                Prefetch(
                    "responses",
                    queryset=BattleResponse.objects.filter(
                        slot=slot,
                        status=BattleResponse.ResponseStatus.COMPLETED,
                    ).order_by("slot"),
                )
            )
            .order_by("turn_number")
        )

        history_messages: list[ArenaHistoryMessage] = []
        for turn in completed_turns:
            history_messages.append(ArenaHistoryMessage(role="user", content=turn.prompt))
            response = next(iter(turn.responses.all()), None)
            if response and response.response_text:
                history_messages.append(
                    ArenaHistoryMessage(role="assistant", content=response.response_text)
                )
        return history_messages

    def _get_battle_for_update(self, battle_id: UUID) -> ArenaBattle:
        """
        Retrieve a battle row under transaction lock for mutating operations.

        Args:
            battle_id: UUID primary key for the battle.

        Returns:
            ArenaBattle: Locked battle row.

        Raises:
            ArenaBattleNotFoundException: If the battle UUID does not exist.
        """
        battle = (
            ArenaBattle.objects
            .select_for_update()
            .select_related("model_a__provider", "model_b__provider")
            .filter(id=battle_id)
            .first()
        )
        if battle is None:
            raise ArenaBattleNotFoundException()
        return battle

    def _validate_battle_can_continue(self, battle: ArenaBattle) -> None:
        """
        Validate that a battle may receive another turn.

        Args:
            battle: Battle to validate.

        Raises:
            ArenaBattleNotContinuableException: If the battle is terminal or not ready for continuation.
        """
        if battle.status in (
            ArenaBattle.BattleStatus.COMPLETED,
            ArenaBattle.BattleStatus.FAILED,
            ArenaBattle.BattleStatus.IN_PROGRESS,
        ):
            raise ArenaBattleNotContinuableException()

    def _create_turn(self, battle: ArenaBattle, prompt: str) -> ArenaTurn:
        """
        Create a new turn and its two pending slot responses.

        Args:
            battle: Parent battle for the new turn.
            prompt: Normalized user prompt for the turn.

        Returns:
            ArenaTurn: Newly created turn row.
        """
        next_turn_number = (
            ArenaTurn.objects.filter(battle=battle).aggregate(max_turn_number=Max("turn_number"))["max_turn_number"]
            or 0
        ) + 1
        turn = ArenaTurn.objects.create(
            battle=battle,
            turn_number=next_turn_number,
            prompt=prompt,
            status=ArenaTurn.TurnStatus.IN_PROGRESS,
            error_message=None,
        )
        for slot in BattleResponse.ResponseSlot.values:
            BattleResponse.objects.create(
                turn=turn,
                slot=slot,
                status=BattleResponse.ResponseStatus.PENDING,
                error_message=None,
            )
        return turn

    def _select_random_models(self) -> tuple[LLMModel, LLMModel]:
        """
        Select two random active models and assign them to fixed battle slots.

        Returns:
            tuple[LLMModel, LLMModel]: Models assigned to slots A and B.

        Raises:
            InsufficientActiveLLMModelsException: If fewer than two active models are available.
        """
        active_models = list(self.llm_model_service.get_active_models())
        if len(active_models) < 2:
            raise InsufficientActiveLLMModelsException()

        selected_models = random.sample(active_models, 2)
        return selected_models[0], selected_models[1]

    @staticmethod
    def _normalize_prompt(prompt: str) -> str:
        """
        Normalize and validate an incoming battle prompt.

        Args:
            prompt: Raw request prompt.

        Returns:
            str: Trimmed prompt.

        Raises:
            LLMInferenceException: If the prompt is empty.
        """
        normalized_prompt = prompt.strip()
        if not normalized_prompt:
            raise LLMInferenceException(detail="A prompt is required to create a battle.")
        return normalized_prompt

    @staticmethod
    def _get_winner_model(battle: ArenaBattle, choice: str) -> LLMModel | None:
        """
        Resolve the winning model for a vote choice.

        Args:
            battle: Battle that owns the vote.
            choice: Stored vote choice.

        Returns:
            LLMModel | None: Winning model or None for ties.
        """
        if choice == BattleVote.VoteChoice.TIE:
            return None
        return battle.get_model_for_slot(choice)

    @staticmethod
    def _build_revealed_model_entry(slot: str, model: LLMModel, winning_slot: str) -> dict[str, Any]:
        """
        Build the revealed model metadata for a vote response.

        Args:
            slot: Fixed anonymized battle slot.
            model: Model assigned to that slot.
            winning_slot: Vote choice that determines winner display.

        Returns:
            dict[str, Any]: Revealed model metadata payload.
        """
        return {
            "slot": slot,
            "model_name": model.name,
            "provider_name": model.provider.name,
            "provider_display_name": model.provider.display_name,
            "is_winner": winning_slot != BattleVote.VoteChoice.TIE and slot == winning_slot,
        }

    @staticmethod
    def _get_slot_generation_config(
        battle: ArenaBattle,
        slot: str,
    ) -> dict[str, int | float] | None:
        """
        Resolve the persisted runtime generation config for one battle slot.

        Args:
            battle: Battle whose experiment config may define runtime parameters.
            slot: Slot whose generation config should be returned.

        Returns:
            dict[str, int | float] | None: Slot generation config or None for standard battles.
        """
        experiment_config = ArenaService._get_experiment_config(battle)
        if experiment_config is None:
            return None

        slot_suffix = "a" if slot == BattleResponse.ResponseSlot.A else "b"
        generation_config: dict[str, int | float] = {}
        for parameter_name in (
            "temperature",
            "top_p",
            "top_k",
            "frequency_penalty",
            "presence_penalty",
        ):
            if not getattr(experiment_config, f"{parameter_name}_enabled"):
                continue
            value = getattr(experiment_config, f"{parameter_name}_value_{slot_suffix}")
            if value is None:
                continue
            generation_config[parameter_name] = (
                int(value) if parameter_name == "top_k" else float(value)
            )

        return generation_config or None

    @staticmethod
    def _build_experiment_reveal_payload(
        experiment_config: ExperimentConfig | None,
    ) -> dict[str, Any] | None:
        """
        Build the experimental reveal payload for vote responses.

        Args:
            experiment_config: Persisted experiment config for the battle, if present.

        Returns:
            dict[str, Any] | None: Serialized experimental reveal payload or None.
        """
        if experiment_config is None:
            return None

        return {
            "model_mode": experiment_config.model_mode,
            "share_values_across_models": experiment_config.share_values_across_models,
            "parameters": {
                parameter_name: {
                    "enabled": getattr(experiment_config, f"{parameter_name}_enabled"),
                    "distribution": getattr(experiment_config, f"{parameter_name}_distribution"),
                    "slot_a_value": (
                        getattr(experiment_config, f"{parameter_name}_value_a")
                        if parameter_name == "top_k"
                        else ArenaService._serialize_decimal_value(
                            getattr(experiment_config, f"{parameter_name}_value_a")
                        )
                    ),
                    "slot_b_value": (
                        getattr(experiment_config, f"{parameter_name}_value_b")
                        if parameter_name == "top_k"
                        else ArenaService._serialize_decimal_value(
                            getattr(experiment_config, f"{parameter_name}_value_b")
                        )
                    ),
                }
                for parameter_name in (
                    "temperature",
                    "top_p",
                    "top_k",
                    "frequency_penalty",
                    "presence_penalty",
                )
            },
        }

    @staticmethod
    def _serialize_decimal_value(value: Any) -> float | None:
        """
        Convert a stored decimal-like value into a float for response serialization.

        Args:
            value: Decimal-like sampled value.

        Returns:
            float | None: Serialized float or None when the sampled value is empty.
        """
        if value is None:
            return None
        return float(value)

    @staticmethod
    def _get_experiment_config(battle: ArenaBattle) -> ExperimentConfig | None:
        """
        Safely return the experiment config linked to a battle when it exists.

        Args:
            battle: Battle whose linked experiment config should be retrieved.

        Returns:
            ExperimentConfig | None: Linked experiment config or None for standard battles.
        """
        try:
            return battle.experiment_config
        except ExperimentConfig.DoesNotExist:
            return None
