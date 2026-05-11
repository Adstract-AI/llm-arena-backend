from rest_framework import status
from rest_framework.generics import CreateAPIView, ListAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from chat.serializers import (
    ChatMessageRequestSerializer,
    ChatMessageResponseSerializer,
    FinkiModelSerializer,
)
from chat.services.chat_service import ChatService
from chat.services.chat_streaming_service import ChatStreamingService
from common.abstract import ServiceView
from llm_arena.views import build_sse_response
from platform_settings.services import RateLimitService


class FinkiModelListView(ServiceView[ChatService], ListAPIView):
    """Return active FINKI models that are available for non-battle chat."""

    permission_classes = [AllowAny]
    service_class = ChatService
    serializer_class = FinkiModelSerializer

    def list(self, request, *args, **kwargs):
        models = self.service.get_chat_supported_models()
        serializer = self.get_serializer(models, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ChatMessageCreateView(ServiceView[ChatService], CreateAPIView):
    """Create one chat turn by invoking a selected FINKI model with session memory."""

    permission_classes = [IsAuthenticated]
    service_class = ChatService
    serializer_class = ChatMessageRequestSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        RateLimitService(user=request.user).enforce_chat_limit()

        response_payload = self.service.send_message(
            provider_name=serializer.validated_data["provider_name"],
            model_name=serializer.validated_data["model_name"],
            message=serializer.validated_data["message"],
            session_id=serializer.validated_data.get("session_id"),
        )

        response_serializer = ChatMessageResponseSerializer(response_payload)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class ChatMessageStreamCreateView(ServiceView[ChatStreamingService], CreateAPIView):
    """Create one chat turn and stream the selected FINKI model response."""

    permission_classes = [IsAuthenticated]
    service_class = ChatStreamingService
    serializer_class = ChatMessageRequestSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        RateLimitService(user=request.user).enforce_chat_limit()

        events = self.service.stream_message(
            provider_name=serializer.validated_data["provider_name"],
            model_name=serializer.validated_data["model_name"],
            message=serializer.validated_data["message"],
            session_id=serializer.validated_data.get("session_id"),
        )
        return build_sse_response(events)
