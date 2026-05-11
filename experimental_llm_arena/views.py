from rest_framework import status
from rest_framework.generics import CreateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from common.abstract import ServiceView
from experimental_llm_arena.serializers import ExperimentalBattleCreateRequestSerializer
from experimental_llm_arena.services.experimental_arena_service import ExperimentalArenaService
from llm_arena.serializers import ExperimentalArenaBattleSnapshotSerializer
from llm_arena.views import build_sse_response
from platform_settings.services import RateLimitService


class ExperimentalArenaBattleCreateView(ServiceView[ExperimentalArenaService], CreateAPIView):
    """Start a new experimental arena battle and return the anonymous transcript snapshot."""

    permission_classes = [IsAuthenticated]
    service_class = ExperimentalArenaService
    serializer_class = ExperimentalBattleCreateRequestSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        RateLimitService(user=request.user).enforce_experimental_arena_limit()

        battle = self.service.create_battle(
            prompt=serializer.validated_data["prompt"],
            model_mode=serializer.validated_data["model_mode"],
            share_values_across_models=serializer.validated_data.get("share_values_across_models"),
            parameters=serializer.validated_data["parameters"],
        )
        response_serializer = ExperimentalArenaBattleSnapshotSerializer(
            self.service.arena_service.build_battle_snapshot(battle)
        )
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class ExperimentalArenaBattleStreamCreateView(ServiceView[ExperimentalArenaService], CreateAPIView):
    """Start a new experimental arena battle and stream both first-turn responses."""

    permission_classes = [IsAuthenticated]
    service_class = ExperimentalArenaService
    serializer_class = ExperimentalBattleCreateRequestSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        RateLimitService(user=request.user).enforce_experimental_arena_limit()

        streaming_session = self.service.create_battle_stream(
            prompt=serializer.validated_data["prompt"],
            model_mode=serializer.validated_data["model_mode"],
            share_values_across_models=serializer.validated_data.get("share_values_across_models"),
            parameters=serializer.validated_data["parameters"],
        )
        return build_sse_response(streaming_session.events)
