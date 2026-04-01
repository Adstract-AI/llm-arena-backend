import json
from typing import Any
from uuid import UUID

from django.db import transaction

from common.abstract import AbstractService
from llm_arena.exceptions import (
    ActiveAgentPromptNotFoundException,
    ArenaBattleAlreadyHasJudgeVoteException,
    ArenaBattleMissingHumanVoteException,
    ArenaBattleNotFoundException,
    InactiveLLMModelException,
    LLMJudgeDecisionParseException,
)
from llm_arena.models import AgentPrompt, ArenaBattle, BattleResponse, BattleVote, LLMJudgeVote, LLMModel
from llm_arena.services.arena_service import ArenaService
from llm_arena.services.inference_service import ArenaInferenceService

class AgentService(AbstractService):
    """Run internal agent workflows such as LLM-based judging for arena battles."""

    arena_service = ArenaService()
    inference_service = ArenaInferenceService()

    def judge_battle(self, battle_id: UUID, judge_model: LLMModel) -> LLMJudgeVote:
        """
        Run the judge agent against one battle transcript and persist the resulting judge vote.

        Args:
            battle_id: UUID primary key of the battle to judge.
            judge_model: Active LLM model that will evaluate the anonymous transcript.

        Returns:
            LLMJudgeVote: Persisted LLM judge vote for the selected battle.

        Raises:
            ArenaBattleNotFoundException: If the battle does not exist.
            InactiveLLMModelException: If the selected judge model is inactive.
            ArenaBattleMissingHumanVoteException: If the battle has not been human-voted yet.
            ArenaBattleAlreadyHasJudgeVoteException: If an LLM judge vote already exists.
            ActiveAgentPromptNotFoundException: If no active judge prompt is configured.
            LLMJudgeDecisionParseException: If the judge output cannot be parsed or validated.
        """
        if not judge_model.is_active:
            raise InactiveLLMModelException(
                detail=f"LLM model '{judge_model.name}' is inactive and cannot be used as a judge."
            )

        battle = self.arena_service.get_battle(battle_id)
        self._validate_judge_eligibility(battle)
        system_prompt = self.get_active_system_prompt(AgentPrompt.AgentType.JUDGE)
        response_details = self.inference_service.generate_response_details(
            model=judge_model,
            prompt=self._build_judge_prompt(battle),
            system_prompt=system_prompt,
        )
        parsed_decision = self._parse_judge_response(response_details["response_text"])
        return self._persist_judge_vote(
            battle_id=battle.id,
            judge_model=judge_model,
            choice=parsed_decision["choice"],
            reasoning=parsed_decision["reasoning"],
        )

    def get_active_system_prompt(self, agent_type: str) -> str:
        """
        Return the active system prompt text for an internal agent type.

        Args:
            agent_type: Agent type identifier to resolve.

        Returns:
            str: Active system prompt text.

        Raises:
            ActiveAgentPromptNotFoundException: If no active prompt exists for the agent type.
        """
        prompt = (
            AgentPrompt.objects
            .filter(agent_type=agent_type, is_active=True)
            .order_by("-updated_at", "-created_at")
            .first()
        )
        if prompt is None:
            raise ActiveAgentPromptNotFoundException(
                detail=f"No active prompt is configured for agent type '{agent_type}'."
            )
        return prompt.system_prompt

    def _validate_judge_eligibility(self, battle: ArenaBattle) -> None:
        """
        Validate that one battle may receive an LLM judge vote.

        Args:
            battle: Persisted battle to validate.

        Raises:
            ArenaBattleMissingHumanVoteException: If the battle has no human vote.
            ArenaBattleAlreadyHasJudgeVoteException: If an LLM judge vote already exists.
        """
        if not BattleVote.objects.filter(battle=battle).exists():
            raise ArenaBattleMissingHumanVoteException(
                detail=f"Battle '{battle.id}' must have a human vote before LLM judging."
            )
        if LLMJudgeVote.objects.filter(battle=battle).exists():
            raise ArenaBattleAlreadyHasJudgeVoteException(
                detail=f"Battle '{battle.id}' already has an LLM judge vote."
            )

    def _build_judge_prompt(self, battle: ArenaBattle) -> str:
        """
        Build the user prompt passed to the judge model for one anonymous battle.

        Args:
            battle: Persisted battle whose transcript should be judged.

        Returns:
            str: Transcript-formatted user prompt with strict JSON response instructions.
        """
        transcript_lines = [
            "Evaluate the following anonymous multi-turn arena battle.",
            "Return strict JSON with exactly two keys: choice and reasoning.",
            'The choice value must be one of: "A", "B", "tie".',
            "The reasoning must be a short explanation of the decision.",
            "",
            "Battle Transcript:",
        ]

        for turn in battle.turns.all():
            transcript_lines.extend(
                [
                    "",
                    f"Turn {turn.turn_number}",
                    f"User Prompt: {turn.prompt}",
                    f"Response A: {self._get_turn_response_text(turn, BattleResponse.ResponseSlot.A)}",
                    f"Response B: {self._get_turn_response_text(turn, BattleResponse.ResponseSlot.B)}",
                ]
            )

        return "\n".join(transcript_lines)

    def _parse_judge_response(self, response_text: str) -> dict[str, str]:
        """
        Parse the judge model output into a normalized battle decision payload.

        Args:
            response_text: Raw model text returned by the judge model.

        Returns:
            dict[str, str]: Parsed choice and reasoning values.

        Raises:
            LLMJudgeDecisionParseException: If the output is missing or invalid.
        """
        normalized_text = response_text.strip()
        if not normalized_text:
            raise LLMJudgeDecisionParseException(detail="The LLM judge returned an empty response.")

        json_payload_text = self._extract_json_payload(normalized_text)
        try:
            payload = json.loads(json_payload_text)
        except json.JSONDecodeError as exc:
            raise LLMJudgeDecisionParseException(
                detail="The LLM judge did not return valid JSON."
            ) from exc

        choice = str(payload.get("choice", "")).strip()
        reasoning = str(payload.get("reasoning", "")).strip()
        if choice not in BattleVote.VoteChoice.values:
            raise LLMJudgeDecisionParseException(
                detail="The LLM judge returned an invalid choice."
            )
        if not reasoning:
            raise LLMJudgeDecisionParseException(
                detail="The LLM judge response is missing reasoning."
            )

        return {
            "choice": choice,
            "reasoning": reasoning,
        }

    @staticmethod
    def _extract_json_payload(response_text: str) -> str:
        """
        Extract the JSON object payload from a raw judge-model response.

        Args:
            response_text: Raw judge-model text output.

        Returns:
            str: JSON substring ready for parsing.

        Raises:
            LLMJudgeDecisionParseException: If no JSON object can be found.
        """
        stripped_text = response_text.strip()
        if stripped_text.startswith("```"):
            stripped_text = stripped_text.split("\n", 1)[-1]
            if stripped_text.endswith("```"):
                stripped_text = stripped_text[:-3].strip()

        start_index = stripped_text.find("{")
        end_index = stripped_text.rfind("}")
        if start_index == -1 or end_index == -1 or end_index < start_index:
            raise LLMJudgeDecisionParseException(
                detail="The LLM judge response did not contain a JSON object."
            )
        return stripped_text[start_index:end_index + 1]

    @transaction.atomic
    def _persist_judge_vote(
        self,
        battle_id: UUID,
        judge_model: LLMModel,
        choice: str,
        reasoning: str,
    ) -> LLMJudgeVote:
        """
        Persist one judge vote after revalidating battle eligibility under lock.

        Args:
            battle_id: UUID primary key of the judged battle.
            judge_model: Active model used as the judge.
            choice: Parsed winner choice.
            reasoning: Parsed judge reasoning text.

        Returns:
            LLMJudgeVote: Persisted judge vote row.

        Raises:
            ArenaBattleNotFoundException: If the battle does not exist.
            ArenaBattleMissingHumanVoteException: If the battle no longer has a human vote.
            ArenaBattleAlreadyHasJudgeVoteException: If an LLM judge vote already exists.
        """
        battle = (
            ArenaBattle.objects
            .select_for_update()
            .filter(id=battle_id)
            .first()
        )
        if battle is None:
            raise ArenaBattleNotFoundException()

        self._validate_judge_eligibility(battle)
        return LLMJudgeVote.objects.create(
            battle=battle,
            judge_model=judge_model,
            choice=choice,
            reasoning=reasoning,
        )

    @staticmethod
    def _get_turn_response_text(turn: Any, slot: str) -> str:
        """
        Return the stored response text for one battle turn and slot.

        Args:
            turn: Arena turn carrying prefetched responses.
            slot: Slot identifier whose response text should be returned.

        Returns:
            str: Response text or an empty string when missing.
        """
        for response in turn.responses.all():
            if response.slot == slot:
                return response.response_text
        return ""
