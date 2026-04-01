from rest_framework import status
from rest_framework.generics import CreateAPIView, ListAPIView, RetrieveAPIView
from rest_framework.response import Response

from common.abstract import ServiceView
from llm_arena.serializers import (
    ArenaBattleSnapshotSerializer,
    BattleCreateRequestSerializer,
    BattleResponseUpdateRequestSerializer,
    BattleTurnCreateRequestSerializer,
    BattleVoteRequestSerializer,
    BattleVoteResponseSerializer,
    LeaderboardEntrySerializer,
    LLMModelDetailSerializer,
)
from llm_arena.services.arena_service import ArenaService
from llm_arena.services.leaderboard_service import LeaderboardService
from llm_arena.services.llm_model_service import LLMModelService


class ArenaBattleCreateView(ServiceView[ArenaService], CreateAPIView):
    """Create a new blind arena battle and return the full anonymous transcript snapshot."""

    service_class = ArenaService
    serializer_class = BattleCreateRequestSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        battle = self.service.create_battle(
            prompt=serializer.validated_data["prompt"],
        )
        response_serializer = ArenaBattleSnapshotSerializer(
            self.service.build_battle_snapshot(battle)
        )
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class ArenaBattleTurnCreateView(ServiceView[ArenaService], CreateAPIView):
    """Append a new prompt turn to an existing arena battle and return the full transcript."""

    service_class = ArenaService
    serializer_class = BattleTurnCreateRequestSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        battle = self.service.continue_battle(
            battle_id=kwargs["id"],
            prompt=serializer.validated_data["prompt"],
        )
        response_serializer = ArenaBattleSnapshotSerializer(
            self.service.build_battle_snapshot(battle)
        )
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class ArenaBattleResponseUpdateView(ServiceView[ArenaService]):
    """Create or update one saved response improvement for an experimental battle."""

    service_class = ArenaService
    serializer_class = BattleResponseUpdateRequestSerializer

    def patch(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        battle = self.service.update_experimental_response(
            battle_id=kwargs["id"],
            turn_number=kwargs["turn_number"],
            slot=kwargs["slot"],
            response_text=serializer.validated_data["response_text"],
        )
        response_serializer = ArenaBattleSnapshotSerializer(
            self.service.build_battle_snapshot(battle)
        )
        return Response(response_serializer.data, status=status.HTTP_200_OK)


class ArenaBattleDetailView(ServiceView[ArenaService], RetrieveAPIView):
    """Return the full anonymous transcript for one arena battle."""

    service_class = ArenaService
    serializer_class = ArenaBattleSnapshotSerializer

    def retrieve(self, request, *args, **kwargs):
        battle = self.service.get_battle(kwargs["id"])
        serializer = self.get_serializer(self.service.build_battle_snapshot(battle))
        return Response(serializer.data, status=status.HTTP_200_OK)


class ArenaBattleVoteCreateView(ServiceView[ArenaService], CreateAPIView):
    """Submit a vote for a completed battle transcript and reveal model identities."""

    service_class = ArenaService
    serializer_class = BattleVoteRequestSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        battle_id = kwargs["id"]
        self.service.submit_vote(
            battle_id=battle_id,
            choice=serializer.validated_data["choice"],
            feedback=serializer.validated_data.get("feedback", ""),
        )
        battle = self.service.get_battle(battle_id)
        response_serializer = BattleVoteResponseSerializer(
            self.service.build_vote_snapshot(battle)
        )
        return Response(response_serializer.data, status=status.HTTP_200_OK)


class LeaderboardListView(ServiceView[LeaderboardService], ListAPIView):
    """Return leaderboard statistics for all active arena models."""

    service_class = LeaderboardService
    serializer_class = LeaderboardEntrySerializer

    def list(self, request, *args, **kwargs):
        leaderboard = self.service.get_leaderboard()
        serializer = self.get_serializer(leaderboard, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class LLMModelDetailView(ServiceView[LLMModelService], RetrieveAPIView):
    """Return a detailed model payload including stats and leaderboard-derived values."""

    service_class = LLMModelService
    serializer_class = LLMModelDetailSerializer

    def retrieve(self, request, *args, **kwargs):
        model_detail = self.service.get_model_detail(kwargs["model_name"])
        serializer = self.get_serializer(model_detail)
        return Response(serializer.data, status=status.HTTP_200_OK)
