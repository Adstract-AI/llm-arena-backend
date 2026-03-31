from decimal import Decimal
from unittest.mock import patch

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from experimental_llm_arena.models import ExperimentConfig
from experimental_llm_arena.services.experimental_arena_service import ExperimentalArenaService
from llm_arena.models import ArenaBattle, LLMModel, LLMProvider
from llm_arena.services.arena_service import ArenaService


class ExperimentalArenaApiTests(APITestCase):
    def setUp(self) -> None:
        self.openai_provider = LLMProvider.objects.create(
            name="openai",
            display_name="OpenAI",
            description="OpenAI models",
            api_base_url="https://api.openai.com/v1",
        )
        self.anthropic_provider = LLMProvider.objects.create(
            name="anthropic",
            display_name="Anthropic",
            description="Anthropic models",
            api_base_url="https://api.anthropic.com/v1",
        )
        self.finki_provider = LLMProvider.objects.create(
            name="finki",
            display_name="FINKI",
            description="FINKI models",
            api_base_url="https://pna.finki.ukim.mk/v1",
        )

        self.openai_model = LLMModel.objects.create(
            provider=self.openai_provider,
            name="gpt-5.4",
            external_model_id="gpt-5.4",
            is_active=True,
        )
        self.anthropic_model = LLMModel.objects.create(
            provider=self.anthropic_provider,
            name="claude-sonnet-4.6",
            external_model_id="claude-sonnet-4-6",
            is_active=True,
        )
        self.finki_model = LLMModel.objects.create(
            provider=self.finki_provider,
            name="vezilka-4b-it-fp16",
            external_model_id="finki_ukim/vezilka:4b-it-fp16",
            is_active=True,
        )

        self.create_url = reverse("experimental-arena-battle-create")

    @patch.object(ArenaService.inference_service, "generate_response_details_with_history")
    @patch.object(ExperimentalArenaService, "_sample_parameter_value")
    @patch.object(ExperimentalArenaService, "_select_models")
    def test_create_experimental_battle_persists_config_without_reveal(
        self,
        mock_select_models,
        mock_sample_parameter_value,
        mock_generate,
    ) -> None:
        mock_select_models.return_value = (self.openai_model, self.openai_model)
        mock_sample_parameter_value.side_effect = [
            Decimal("0.5000"),
            Decimal("0.9000"),
        ]
        mock_generate.side_effect = [
            self._response_details("A1"),
            self._response_details("B1"),
        ]

        response = self.client.post(
            self.create_url,
            {
                "prompt": "Explain friendship.",
                "model_mode": "same_model",
                "share_values_across_models": None,
                "parameters": {
                    "temperature": {"enabled": True, "distribution": "normal"},
                    "top_p": {"enabled": False, "distribution": None},
                    "top_k": {"enabled": False, "distribution": None},
                    "frequency_penalty": {"enabled": False, "distribution": None},
                    "presence_penalty": {"enabled": False, "distribution": None},
                },
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertNotIn("experiment", response.data)

        battle = ArenaBattle.objects.get(id=response.data["id"])
        experiment_config = battle.experiment_config
        self.assertEqual(battle.model_a_id, self.openai_model.id)
        self.assertEqual(battle.model_b_id, self.openai_model.id)
        self.assertEqual(experiment_config.model_mode, ExperimentConfig.ModelMode.SAME_MODEL)
        self.assertEqual(experiment_config.temperature_value_a, Decimal("0.5000"))
        self.assertEqual(experiment_config.temperature_value_b, Decimal("0.9000"))
        self.assertFalse(experiment_config.top_p_enabled)

    @patch.object(ArenaService.inference_service, "generate_response_details_with_history")
    @patch.object(ExperimentalArenaService, "_sample_parameter_value")
    @patch.object(ExperimentalArenaService, "_select_models")
    def test_continue_experimental_battle_reuses_sampled_generation_config(
        self,
        mock_select_models,
        mock_sample_parameter_value,
        mock_generate,
    ) -> None:
        mock_select_models.return_value = (self.openai_model, self.anthropic_model)
        mock_sample_parameter_value.side_effect = [
            Decimal("0.4000"),
            Decimal("0.8000"),
        ]
        mock_generate.side_effect = [
            self._response_details("A1"),
            self._response_details("B1"),
            self._response_details("A2"),
            self._response_details("B2"),
        ]

        create_response = self.client.post(
            self.create_url,
            {
                "prompt": "Turn one",
                "model_mode": "different_models",
                "share_values_across_models": False,
                "parameters": {
                    "temperature": {"enabled": True, "distribution": "uniform"},
                    "top_p": {"enabled": False, "distribution": None},
                    "top_k": {"enabled": False, "distribution": None},
                    "frequency_penalty": {"enabled": False, "distribution": None},
                    "presence_penalty": {"enabled": False, "distribution": None},
                },
            },
            format="json",
        )

        battle_id = create_response.data["id"]
        continue_response = self.client.post(
            reverse("arena-battle-turn-create", kwargs={"id": battle_id}),
            {"prompt": "Turn two"},
            format="json",
        )

        self.assertEqual(continue_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            mock_generate.call_args_list[2].kwargs["generation_config"],
            {"temperature": 0.4},
        )
        self.assertEqual(
            mock_generate.call_args_list[3].kwargs["generation_config"],
            {"temperature": 0.8},
        )

    @patch.object(ArenaService.inference_service, "generate_response_details_with_history")
    @patch.object(ExperimentalArenaService, "_sample_parameter_value")
    @patch.object(ExperimentalArenaService, "_select_models")
    def test_vote_reveals_experiment_config_for_experimental_battle(
        self,
        mock_select_models,
        mock_sample_parameter_value,
        mock_generate,
    ) -> None:
        mock_select_models.return_value = (self.openai_model, self.anthropic_model)
        mock_sample_parameter_value.return_value = Decimal("0.7000")
        mock_generate.side_effect = [
            self._response_details("A1"),
            self._response_details("B1"),
        ]

        create_response = self.client.post(
            self.create_url,
            {
                "prompt": "Prompt for voting",
                "model_mode": "different_models",
                "share_values_across_models": True,
                "parameters": {
                    "temperature": {"enabled": True, "distribution": "beta"},
                    "top_p": {"enabled": False, "distribution": None},
                    "top_k": {"enabled": False, "distribution": None},
                    "frequency_penalty": {"enabled": False, "distribution": None},
                    "presence_penalty": {"enabled": False, "distribution": None},
                },
            },
            format="json",
        )

        vote_response = self.client.post(
            reverse("arena-battle-vote-create", kwargs={"id": create_response.data["id"]}),
            {"choice": "A", "feedback": "A was better"},
            format="json",
        )

        self.assertEqual(vote_response.status_code, status.HTTP_200_OK)
        self.assertIn("experiment", vote_response.data)
        self.assertEqual(vote_response.data["experiment"]["model_mode"], "different_models")
        self.assertTrue(vote_response.data["experiment"]["share_values_across_models"])
        self.assertEqual(
            vote_response.data["experiment"]["parameters"]["temperature"],
            {
                "enabled": True,
                "distribution": "beta",
                "slot_a_value": 0.7,
                "slot_b_value": 0.7,
            },
        )

    @staticmethod
    def _response_details(response_text: str) -> dict:
        return {
            "response_text": response_text,
            "finish_reason": "stop",
            "prompt_tokens": 5,
            "completion_tokens": 7,
            "total_tokens": 12,
            "raw_metadata": {"source": "test"},
        }
