from rest_framework import status
from rest_framework.generics import CreateAPIView
from rest_framework.response import Response

from common.abstract import ServiceView
from llm_arena.serializers import (
    BattleCreateRequestSerializer,
    BattleCreateResponseSerializer,
    BattleVoteRequestSerializer,
    BattleVoteResponseSerializer,
)
from llm_arena.services.arena_service import ArenaService


class ArenaBattleCreateView(ServiceView[ArenaService], CreateAPIView):
    """Create a new blind arena battle and return anonymized responses."""

    service_class = ArenaService
    serializer_class = BattleCreateRequestSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        battle = self.service.create_battle(
            prompt=serializer.validated_data["prompt"],
        )

        response_serializer = BattleCreateResponseSerializer(
            {
                "battle_id": battle.battle_id,
                "prompt": battle.prompt,
                "responses": [
                    {
                        "slot": response.slot,
                        "response_text": response.response_text,
                    }
                    for response in battle.responses.order_by("slot")
                ],
            }
        )
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class ArenaBattleVoteCreateView(ServiceView[ArenaService], CreateAPIView):
    """Submit a vote for a completed battle and reveal model identities."""

    service_class = ArenaService
    serializer_class = BattleVoteRequestSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        battle_id = kwargs["battle_id"]
        vote = self.service.submit_vote(
            battle_id=battle_id,
            choice=serializer.validated_data["choice"],
            feedback=serializer.validated_data.get("feedback", ""),
        )
        battle = self.service.get_battle_by_battle_id(battle_id)
        responses = list(battle.responses.order_by("slot"))
        winning_response = next((response for response in responses if response.slot == vote.choice), None)

        response_serializer = BattleVoteResponseSerializer(
            {
                "battle_id": battle.battle_id,
                "choice": vote.choice,
                "feedback": vote.feedback,
                "winner_provider_name": winning_response.llm_model.provider.name if winning_response else None,
                "winner_model_name": winning_response.llm_model.name if winning_response else None,
                "responses": [
                    {
                        "slot": response.slot,
                        "response_text": response.response_text,
                        "model_name": response.llm_model.name,
                        "provider_name": response.llm_model.provider.name,
                        "provider_display_name": response.llm_model.provider.display_name,
                        "is_winner": response.slot == vote.choice,
                    }
                    for response in battle.responses.order_by("slot")
                ],
            }
        )
        return Response(response_serializer.data, status=status.HTTP_200_OK)
