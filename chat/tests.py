import uuid
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from chat.models import ChatMessage, ChatSession
from chat.services.chat_service import ChatService
from llm_arena.models import LLMModel, LLMProvider
from platform_settings.management.commands.seed_platform_settings import DEFAULT_RATE_LIMITS
from platform_settings.models import PlatformSettings, RateLimits

User = get_user_model()


class ChatApiTests(APITestCase):
    def setUp(self) -> None:
        rate_limits = RateLimits.objects.create(name="Test Rate Limits", **DEFAULT_RATE_LIMITS)
        PlatformSettings.objects.create(name="Test Settings", is_active=True, rate_limits=rate_limits)
        self.user = User.objects.create_user(
            username="chat-user",
            email="chat@example.com",
        )
        self.other_user = User.objects.create_user(
            username="other-chat-user",
            email="other-chat@example.com",
        )

        self.finki_provider = LLMProvider.objects.create(
            name="finki",
            display_name="FINKI",
            description="FINKI models",
            api_base_url="https://pna.finki.ukim.mk/v1",
        )
        self.openai_provider = LLMProvider.objects.create(
            name="openai",
            display_name="OpenAI",
            description="OpenAI models",
            api_base_url="https://api.openai.com/v1",
        )

        self.finki_model = LLMModel.objects.create(
            provider=self.finki_provider,
            name="vezilka-4b-it-fp16",
            external_model_id="finki_ukim/vezilka:4b-it-fp16",
            description="Active FINKI model",
            is_active=True,
        )
        self.other_finki_model = LLMModel.objects.create(
            provider=self.finki_provider,
            name="vezilka-4b-it-fp32",
            external_model_id="finki_ukim/vezilka:4b-it-fp32",
            description="Another active FINKI model",
            is_active=True,
        )
        self.inactive_finki_model = LLMModel.objects.create(
            provider=self.finki_provider,
            name="vezilka-inactive",
            external_model_id="finki_ukim/vezilka:inactive",
            description="Inactive FINKI model",
            is_active=False,
        )
        self.openai_model = LLMModel.objects.create(
            provider=self.openai_provider,
            name="gpt-4.1",
            external_model_id="gpt-4.1",
            description="OpenAI model",
            is_active=True,
        )

        self.message_url = reverse("chat-message-create")
        self.models_url = reverse("chat-model-list")
        self.client.force_authenticate(user=self.user)

    @patch.object(ChatService.inference_service, "generate_response_details_with_history")
    def test_first_message_creates_session_and_persists_messages(self, mock_generate_response_details):
        mock_generate_response_details.return_value = {
            "response_text": "Zdravo i od asistentot.",
            "finish_reason": "stop",
            "prompt_tokens": 10,
            "completion_tokens": 12,
            "total_tokens": 22,
            "raw_metadata": {"source": "test"},
        }

        response = self.client.post(
            self.message_url,
            {
                "provider_name": "finki",
                "model_name": self.finki_model.name,
                "message": "Zdravo!",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        session = ChatSession.objects.get(id=response.data["session_id"])
        self.assertEqual(session.user_id, self.user.id)
        self.assertEqual(session.llm_model_id, self.finki_model.id)

        persisted_messages = list(session.messages.order_by("created_at", "id"))
        self.assertEqual(len(persisted_messages), 2)
        self.assertEqual(persisted_messages[0].role, ChatMessage.MessageRole.USER)
        self.assertEqual(persisted_messages[0].content, "Zdravo!")
        self.assertEqual(persisted_messages[1].role, ChatMessage.MessageRole.ASSISTANT)
        self.assertEqual(persisted_messages[1].content, "Zdravo i od asistentot.")

        self.assertEqual(mock_generate_response_details.call_count, 1)
        self.assertEqual(mock_generate_response_details.call_args.kwargs["history_messages"], [])

    @patch.object(ChatService.inference_service, "generate_response_details_with_history")
    def test_follow_up_uses_last_twenty_messages_as_memory(self, mock_generate_response_details):
        mock_generate_response_details.return_value = {
            "response_text": "Follow-up response",
            "finish_reason": "stop",
            "prompt_tokens": 5,
            "completion_tokens": 7,
            "total_tokens": 12,
            "raw_metadata": {},
        }

        session = ChatSession.objects.create(user=self.user, llm_model=self.finki_model)
        for index in range(25):
            role = (
                ChatMessage.MessageRole.USER
                if index % 2 == 0
                else ChatMessage.MessageRole.ASSISTANT
            )
            ChatMessage.objects.create(
                session=session,
                role=role,
                content=f"historic-message-{index}",
            )

        response = self.client.post(
            self.message_url,
            {
                "provider_name": "finki",
                "model_name": self.finki_model.name,
                "message": "new question",
                "session_id": str(session.id),
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        history_messages = mock_generate_response_details.call_args.kwargs["history_messages"]
        self.assertEqual(len(history_messages), 20)
        self.assertEqual(
            [message.content for message in history_messages],
            [f"historic-message-{index}" for index in range(5, 25)],
        )

    def test_model_mismatch_returns_conflict(self):
        session = ChatSession.objects.create(user=self.user, llm_model=self.finki_model)

        response = self.client.post(
            self.message_url,
            {
                "provider_name": "finki",
                "model_name": self.other_finki_model.name,
                "message": "question",
                "session_id": str(session.id),
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_non_finki_provider_returns_bad_request(self):
        response = self.client.post(
            self.message_url,
            {
                "provider_name": "openai",
                "model_name": self.openai_model.name,
                "message": "question",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unknown_session_returns_not_found(self):
        response = self.client.post(
            self.message_url,
            {
                "provider_name": "finki",
                "model_name": self.finki_model.name,
                "message": "question",
                "session_id": str(uuid.uuid4()),
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_message_endpoint_requires_authentication(self):
        self.client.force_authenticate(user=None)

        response = self.client.post(
            self.message_url,
            {
                "provider_name": "finki",
                "model_name": self.finki_model.name,
                "message": "question",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_chat_session_is_owner_only(self):
        session = ChatSession.objects.create(user=self.user, llm_model=self.finki_model)
        self.client.force_authenticate(user=self.other_user)

        response = self.client.post(
            self.message_url,
            {
                "provider_name": "finki",
                "model_name": self.finki_model.name,
                "message": "question",
                "session_id": str(session.id),
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_models_endpoint_returns_only_active_finki_models(self):
        response = self.client.get(self.models_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        model_names = [item["name"] for item in response.data]
        self.assertIn(self.finki_model.name, model_names)
        self.assertIn(self.other_finki_model.name, model_names)
        self.assertNotIn(self.inactive_finki_model.name, model_names)
        self.assertNotIn(self.openai_model.name, model_names)
