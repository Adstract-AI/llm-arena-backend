from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from queue import Queue
from typing import Any
from uuid import UUID

from django.db import close_old_connections
from django.utils import timezone

from common.abstract import AbstractService
from llm_arena.exceptions import ArenaBattleGenerationFailedException, LLMInferenceException
from llm_arena.models import ArenaBattle, ArenaTurn, BattleResponse
from llm_arena.services.arena_service import ArenaHistoryMessage, ArenaService
from llm_arena.services.inference_service import ArenaInferenceService

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class StreamingSlotPayload:
    slot: str
    response_id: int
    model_name: str
    llm_model: Any
    history_messages: list[ArenaHistoryMessage]
    generation_config: dict[str, int | float] | None


@dataclass(frozen=True)
class StreamingSession:
    battle: ArenaBattle
    turn: ArenaTurn
    events: Any


class ArenaStreamingService(AbstractService):
    """Stream arena turn responses over server-sent events and persist final rows."""

    arena_service = ArenaService()
    inference_service = ArenaInferenceService()

    QUEUE_TIMEOUT_SECONDS = 0.1
    WORKER_COUNT = 2

    def prepare_create_battle_stream(self, prompt: str) -> StreamingSession:
        battle, turn = self.arena_service.prepare_battle(prompt=prompt)
        return StreamingSession(
            battle=battle,
            turn=turn,
            events=self._stream_turn_events(
                battle=battle,
                turn=turn,
                initial_events=[
                    (
                        "battle_created",
                        {
                            "id": str(battle.id),
                            "status": battle.status,
                            "turn_number": turn.turn_number,
                        },
                    ),
                ],
            ),
        )

    def prepare_continue_battle_stream(self, battle_id: UUID, prompt: str) -> StreamingSession:
        battle, turn = self.arena_service.prepare_continue_battle(
            battle_id=battle_id,
            prompt=prompt,
        )
        return StreamingSession(
            battle=battle,
            turn=turn,
            events=self._stream_turn_events(battle=battle, turn=turn),
        )

    def prepare_battle_with_models_stream(
        self,
        prompt: str,
        model_a: Any,
        model_b: Any,
        experiment_setup_callback: Any | None = None,
    ) -> StreamingSession:
        battle, turn = self.arena_service.prepare_battle_with_models(
            prompt=prompt,
            model_a=model_a,
            model_b=model_b,
            experiment_setup_callback=experiment_setup_callback,
        )
        return StreamingSession(
            battle=battle,
            turn=turn,
            events=self._stream_turn_events(
                battle=battle,
                turn=turn,
                initial_events=[
                    (
                        "battle_created",
                        {
                            "id": str(battle.id),
                            "status": battle.status,
                            "turn_number": turn.turn_number,
                        },
                    ),
                ],
            ),
        )

    def _stream_turn_events(
        self,
        battle: ArenaBattle,
        turn: ArenaTurn,
        initial_events: list[tuple[str, dict[str, Any]]] | None = None,
    ):
        for event_name, payload in initial_events or []:
            yield self._format_sse(event_name, payload)

        yield self._format_sse(
            "turn_created",
            {
                "id": str(battle.id),
                "turn_number": turn.turn_number,
                "prompt": turn.prompt,
            },
        )

        event_queue: Queue[tuple[str, str, dict[str, Any]] | tuple[str, str]] = Queue()
        slot_payloads = self._build_slot_payloads(battle=battle, turn=turn)
        completed_slots = 0
        failed_messages: list[str] = []

        with ThreadPoolExecutor(max_workers=self.WORKER_COUNT) as executor:
            for slot_payload in slot_payloads:
                executor.submit(
                    self._stream_slot_response,
                    battle.id,
                    turn.id,
                    turn.prompt,
                    slot_payload,
                    event_queue,
                )

            while completed_slots < len(slot_payloads):
                queue_item = event_queue.get()
                item_type = queue_item[0]

                if item_type == "done":
                    completed_slots += 1
                    continue

                _, event_name, payload = queue_item
                if event_name == "response_failed":
                    failed_messages.append(payload["error_message"])
                yield self._format_sse(event_name, payload)

        if failed_messages:
            self._mark_turn_failed(battle=battle, turn=turn, error_messages=failed_messages)
            failed_battle = self.arena_service.get_battle(battle.id)
            yield self._format_sse(
                "battle_failed",
                {
                    "id": str(failed_battle.id),
                    "error_message": failed_battle.error_message,
                },
            )
            return

        self._mark_turn_completed(battle=battle, turn=turn)
        completed_battle = self.arena_service.get_battle(battle.id)
        yield self._format_sse(
            "turn_completed",
            {
                "id": str(completed_battle.id),
                "turn_number": turn.turn_number,
                "status": completed_battle.status,
                "can_vote": completed_battle.status == ArenaBattle.BattleStatus.AWAITING_VOTE,
            },
        )
        yield self._format_sse("done", self.arena_service.build_battle_snapshot(completed_battle))

    def _build_slot_payloads(self, battle: ArenaBattle, turn: ArenaTurn) -> list[StreamingSlotPayload]:
        responses = {
            response.slot: response
            for response in BattleResponse.objects.filter(turn=turn).order_by("slot")
        }
        return [
            StreamingSlotPayload(
                slot=slot,
                response_id=responses[slot].id,
                model_name=battle.get_model_for_slot(slot).name,
                llm_model=battle.get_model_for_slot(slot),
                history_messages=self.arena_service._build_slot_history_messages(
                    battle=battle,
                    slot=slot,
                ),
                generation_config=self.arena_service._get_slot_generation_config(
                    battle=battle,
                    slot=slot,
                ),
            )
            for slot in BattleResponse.ResponseSlot.values
        ]

    def _stream_slot_response(
        self,
        battle_id: UUID,
        turn_id: int,
        prompt: str,
        slot_payload: StreamingSlotPayload,
        event_queue: Queue,
    ) -> None:
        close_old_connections()
        event_queue.put(("event", "response_started", {"slot": slot_payload.slot}))
        response_text = ""

        try:
            completed_details: dict[str, Any] | None = None
            for stream_event in self.inference_service.stream_response_details_with_history(
                model=slot_payload.llm_model,
                history_messages=slot_payload.history_messages,
                prompt=prompt,
                generation_config=slot_payload.generation_config,
            ):
                if stream_event["type"] == "delta":
                    response_text += stream_event["text"]
                    event_queue.put(
                        (
                            "event",
                            "response_delta",
                            {
                                "slot": slot_payload.slot,
                                "text": stream_event["text"],
                            },
                        )
                    )
                    continue
                completed_details = stream_event

            if completed_details is None:
                raise LLMInferenceException(
                    detail=f"Inference failed for model '{slot_payload.model_name}'."
                )

            final_response_text = completed_details["response_text"] or response_text
            self._persist_completed_response(
                response_id=slot_payload.response_id,
                response_details=completed_details | {"response_text": final_response_text},
            )
            event_queue.put(
                (
                    "event",
                    "response_completed",
                    {
                        "slot": slot_payload.slot,
                        "response_text": final_response_text,
                        "finish_reason": completed_details["finish_reason"] or None,
                        "prompt_tokens": completed_details["prompt_tokens"],
                        "completion_tokens": completed_details["completion_tokens"],
                        "total_tokens": completed_details["total_tokens"],
                        "latency_ms": completed_details.get("latency_ms"),
                    },
                )
            )
        except LLMInferenceException as exc:
            logger.error(
                f"Streaming generation failed for battle {battle_id}, turn {turn_id}, "
                f"slot {slot_payload.slot}, and model {slot_payload.model_name}. Error: {exc.detail}"
            )
            self._persist_failed_response(
                response_id=slot_payload.response_id,
                error_message=str(exc.detail),
            )
            event_queue.put(
                (
                    "event",
                    "response_failed",
                    {
                        "slot": slot_payload.slot,
                        "error_message": str(exc.detail),
                    },
                )
            )
        except Exception:
            logger.error(
                f"Unexpected streaming generation failure for battle {battle_id}, turn {turn_id}, "
                f"slot {slot_payload.slot}, and model {slot_payload.model_name}"
            )
            error_message = "Model generation failed."
            self._persist_failed_response(
                response_id=slot_payload.response_id,
                error_message=error_message,
            )
            event_queue.put(
                (
                    "event",
                    "response_failed",
                    {
                        "slot": slot_payload.slot,
                        "error_message": error_message,
                    },
                )
            )
        finally:
            event_queue.put(("done", slot_payload.slot))
            close_old_connections()

    @staticmethod
    def _persist_completed_response(response_id: int, response_details: dict[str, Any]) -> None:
        response = BattleResponse.objects.get(id=response_id)
        response.response_text = response_details["response_text"]
        response.status = BattleResponse.ResponseStatus.COMPLETED
        response.error_message = None
        response.finish_reason = response_details["finish_reason"] or None
        response.prompt_tokens = response_details["prompt_tokens"]
        response.completion_tokens = response_details["completion_tokens"]
        response.total_tokens = response_details["total_tokens"]
        response.latency_ms = response_details.get("latency_ms")
        response.raw_metadata = response_details["raw_metadata"]
        response.save()

    @staticmethod
    def _persist_failed_response(response_id: int, error_message: str) -> None:
        response = BattleResponse.objects.get(id=response_id)
        response.status = BattleResponse.ResponseStatus.FAILED
        response.error_message = error_message
        response.finish_reason = None
        response.save()

    @staticmethod
    def _mark_turn_failed(
        battle: ArenaBattle,
        turn: ArenaTurn,
        error_messages: list[str],
    ) -> None:
        error_message = " | ".join(error_messages)
        turn.status = ArenaTurn.TurnStatus.FAILED
        turn.error_message = error_message
        turn.save(update_fields=["status", "error_message", "updated_at"])

        battle.status = ArenaBattle.BattleStatus.FAILED
        battle.error_message = error_message
        battle.completed_at = timezone.now()
        battle.save(update_fields=["status", "error_message", "completed_at", "updated_at"])

    @staticmethod
    def _mark_turn_completed(battle: ArenaBattle, turn: ArenaTurn) -> None:
        turn.status = ArenaTurn.TurnStatus.COMPLETED
        turn.error_message = None
        turn.save(update_fields=["status", "error_message", "updated_at"])

        battle.status = ArenaBattle.BattleStatus.AWAITING_VOTE
        battle.error_message = None
        battle.completed_at = None
        battle.save(update_fields=["status", "error_message", "completed_at", "updated_at"])

    @staticmethod
    def _format_sse(event_name: str, payload: dict[str, Any]) -> str:
        return f"event: {event_name}\ndata: {json.dumps(payload, default=str)}\n\n"
