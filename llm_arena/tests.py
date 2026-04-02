from unittest.mock import patch

from django.contrib import admin
from django.test import RequestFactory
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from experimental_llm_arena.models import ExperimentConfig
from llm_arena.admin import ArenaBattleAdmin, ArenaBattleJudgeActionForm
from llm_arena.exceptions import ArenaBattleMissingHumanVoteException
from llm_arena.models import (
    AgentPrompt,
    ArenaBattle,
    ArenaTurn,
    BattleResponse,
    BattleResponseImprovement,
    BattleVote,
    LLMJudgeVote,
    LLMModel,
    LLMProvider,
)
from llm_arena.services.agent_service import AgentService, JudgeDecision
from llm_arena.services.arena_service import ArenaService
from llm_arena.services.leaderboard_service import LeaderboardService


class ArenaApiTests(APITestCase):
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

        self.model_a = LLMModel.objects.create(
            provider=self.openai_provider,
            name="gpt-5.4",
            external_model_id="gpt-5.4",
            is_active=True,
        )
        self.model_b = LLMModel.objects.create(
            provider=self.anthropic_provider,
            name="claude-sonnet-4.6",
            external_model_id="claude-sonnet-4-6",
            is_active=True,
        )

        self.create_url = reverse("arena-battle-create")

    @patch.object(ArenaService.inference_service, "generate_response_details_with_history")
    @patch.object(ArenaService, "_select_random_models")
    def test_create_battle_returns_full_transcript_snapshot(self, mock_select_random_models, mock_generate):
        mock_select_random_models.return_value = (self.model_a, self.model_b)
        mock_generate.side_effect = [
            self._response_details("A1"),
            self._response_details("B1"),
        ]

        response = self.client.post(
            self.create_url,
            {"prompt": "Explain friendship."},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], ArenaBattle.BattleStatus.AWAITING_VOTE)
        self.assertTrue(response.data["can_vote"])
        self.assertEqual(len(response.data["turns"]), 1)
        self.assertEqual(response.data["turns"][0]["turn_number"], 1)
        self.assertEqual(response.data["turns"][0]["prompt"], "Explain friendship.")
        self.assertEqual(
            response.data["turns"][0]["responses"],
            [
                {"slot": "A", "response_text": "A1"},
                {"slot": "B", "response_text": "B1"},
            ],
        )

    @patch.object(ArenaService.inference_service, "generate_response_details_with_history")
    @patch.object(ArenaService, "_select_random_models")
    def test_continue_battle_uses_slot_specific_history(self, mock_select_random_models, mock_generate):
        mock_select_random_models.return_value = (self.model_a, self.model_b)
        mock_generate.side_effect = [
            self._response_details("A1"),
            self._response_details("B1"),
            self._response_details("A2"),
            self._response_details("B2"),
        ]

        create_response = self.client.post(
            self.create_url,
            {"prompt": "Turn one prompt"},
            format="json",
        )
        battle_id = create_response.data["id"]

        continue_response = self.client.post(
            reverse("arena-battle-turn-create", kwargs={"id": battle_id}),
            {"prompt": "Turn two prompt"},
            format="json",
        )

        self.assertEqual(continue_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(continue_response.data["turns"]), 2)
        self.assertEqual(continue_response.data["turns"][1]["prompt"], "Turn two prompt")

        model_a_history = mock_generate.call_args_list[2].kwargs["history_messages"]
        model_b_history = mock_generate.call_args_list[3].kwargs["history_messages"]

        self.assertEqual(
            [(message.role, message.content) for message in model_a_history],
            [("user", "Turn one prompt"), ("assistant", "A1")],
        )
        self.assertEqual(
            [(message.role, message.content) for message in model_b_history],
            [("user", "Turn one prompt"), ("assistant", "B1")],
        )

        detail_response = self.client.get(
            reverse("arena-battle-detail", kwargs={"id": battle_id}),
        )
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(detail_response.data["turns"]), 2)
        self.assertTrue(detail_response.data["can_vote"])

    @patch.object(ArenaService.inference_service, "generate_response_details_with_history")
    @patch.object(ArenaService, "_select_random_models")
    def test_vote_reveals_full_transcript_and_winner(self, mock_select_random_models, mock_generate):
        mock_select_random_models.return_value = (self.model_a, self.model_b)
        mock_generate.side_effect = [
            self._response_details("A1"),
            self._response_details("B1"),
        ]

        create_response = self.client.post(
            self.create_url,
            {"prompt": "Prompt for voting"},
            format="json",
        )
        battle_id = create_response.data["id"]

        vote_response = self.client.post(
            reverse("arena-battle-vote-create", kwargs={"id": battle_id}),
            {"choice": "A", "feedback": "A was better"},
            format="json",
        )

        self.assertEqual(vote_response.status_code, status.HTTP_200_OK)
        self.assertEqual(vote_response.data["status"], ArenaBattle.BattleStatus.COMPLETED)
        self.assertEqual(vote_response.data["winner_provider_name"], self.openai_provider.name)
        self.assertEqual(vote_response.data["winner_model_name"], self.model_a.name)
        self.assertEqual(len(vote_response.data["models"]), 2)
        self.assertTrue(vote_response.data["models"][0]["is_winner"])
        self.assertFalse(vote_response.data["models"][1]["is_winner"])
        self.assertNotIn("experiment", vote_response.data)
        self.assertEqual(len(vote_response.data["turns"]), 1)
        self.assertEqual(
            vote_response.data["turns"][0]["responses"],
            [
                {"slot": "A", "response_text": "A1"},
                {"slot": "B", "response_text": "B1"},
            ],
        )

    def test_update_experimental_response_returns_full_battle_snapshot(self):
        battle = ArenaBattle.objects.create(
            model_a=self.model_a,
            model_b=self.model_b,
            status=ArenaBattle.BattleStatus.AWAITING_VOTE,
        )
        ExperimentConfig.objects.create(
            battle=battle,
            model_mode=ExperimentConfig.ModelMode.DIFFERENT_MODELS,
            share_values_across_models=False,
        )
        turn = ArenaTurn.objects.create(
            battle=battle,
            turn_number=1,
            prompt="Prompt 1",
            status=ArenaTurn.TurnStatus.COMPLETED,
        )
        BattleResponse.objects.create(
            turn=turn,
            slot=BattleResponse.ResponseSlot.A,
            status=BattleResponse.ResponseStatus.COMPLETED,
            response_text="Old A",
            error_message="old error",
        )
        BattleResponse.objects.create(
            turn=turn,
            slot=BattleResponse.ResponseSlot.B,
            status=BattleResponse.ResponseStatus.COMPLETED,
            response_text="B1",
        )

        response = self.client.patch(
            reverse(
                "arena-battle-response-update",
                kwargs={"id": battle.id, "turn_number": 1, "slot": "A"},
            ),
            {"response_text": "  Edited A  "},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], str(battle.id))
        self.assertEqual(response.data["turns"][0]["responses"][0]["response_text"], "Old A")
        self.assertEqual(response.data["turns"][0]["responses"][0]["improvement_text"], "Edited A")
        persisted_response = BattleResponse.objects.get(turn=turn, slot=BattleResponse.ResponseSlot.A)
        self.assertEqual(persisted_response.response_text, "Old A")
        improvement = BattleResponseImprovement.objects.get(response=persisted_response)
        self.assertEqual(improvement.improved_response_text, "Edited A")

    def test_update_experimental_response_updates_existing_improvement(self):
        battle = ArenaBattle.objects.create(
            model_a=self.model_a,
            model_b=self.model_b,
            status=ArenaBattle.BattleStatus.AWAITING_VOTE,
        )
        ExperimentConfig.objects.create(
            battle=battle,
            model_mode=ExperimentConfig.ModelMode.DIFFERENT_MODELS,
            share_values_across_models=False,
        )
        turn = ArenaTurn.objects.create(
            battle=battle,
            turn_number=1,
            prompt="Prompt 1",
            status=ArenaTurn.TurnStatus.COMPLETED,
        )
        response = BattleResponse.objects.create(
            turn=turn,
            slot=BattleResponse.ResponseSlot.A,
            status=BattleResponse.ResponseStatus.COMPLETED,
            response_text="Original A",
        )
        BattleResponseImprovement.objects.create(
            response=response,
            improved_response_text="First improvement",
        )
        BattleResponse.objects.create(
            turn=turn,
            slot=BattleResponse.ResponseSlot.B,
            status=BattleResponse.ResponseStatus.COMPLETED,
            response_text="B1",
        )

        patch_response = self.client.patch(
            reverse(
                "arena-battle-response-update",
                kwargs={"id": battle.id, "turn_number": 1, "slot": "A"},
            ),
            {"response_text": "Updated improvement"},
            format="json",
        )

        self.assertEqual(patch_response.status_code, status.HTTP_200_OK)
        self.assertEqual(BattleResponseImprovement.objects.filter(response=response).count(), 1)
        self.assertEqual(
            BattleResponseImprovement.objects.get(response=response).improved_response_text,
            "Updated improvement",
        )

    def test_vote_response_includes_saved_improvement_text(self):
        battle = ArenaBattle.objects.create(
            model_a=self.model_a,
            model_b=self.model_b,
            status=ArenaBattle.BattleStatus.AWAITING_VOTE,
        )
        ExperimentConfig.objects.create(
            battle=battle,
            model_mode=ExperimentConfig.ModelMode.DIFFERENT_MODELS,
            share_values_across_models=False,
        )
        turn = ArenaTurn.objects.create(
            battle=battle,
            turn_number=1,
            prompt="Prompt 1",
            status=ArenaTurn.TurnStatus.COMPLETED,
        )
        BattleResponse.objects.create(
            turn=turn,
            slot=BattleResponse.ResponseSlot.A,
            status=BattleResponse.ResponseStatus.COMPLETED,
            response_text="Original A",
        )
        BattleResponse.objects.create(
            turn=turn,
            slot=BattleResponse.ResponseSlot.B,
            status=BattleResponse.ResponseStatus.COMPLETED,
            response_text="Original B",
        )

        patch_response = self.client.patch(
            reverse(
                "arena-battle-response-update",
                kwargs={"id": battle.id, "turn_number": 1, "slot": "A"},
            ),
            {"response_text": "Improved A"},
            format="json",
        )
        self.assertEqual(patch_response.status_code, status.HTTP_200_OK)

        vote_response = self.client.post(
            reverse("arena-battle-vote-create", kwargs={"id": battle.id}),
            {"choice": "A", "feedback": "A wins"},
            format="json",
        )

        self.assertEqual(vote_response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            vote_response.data["turns"][0]["responses"],
            [
                {
                    "slot": "A",
                    "response_text": "Original A",
                    "improvement_text": "Improved A",
                },
                {
                    "slot": "B",
                    "response_text": "Original B",
                    "improvement_text": None,
                },
            ],
        )

    def test_update_experimental_response_rejects_standard_battle(self):
        battle = ArenaBattle.objects.create(
            model_a=self.model_a,
            model_b=self.model_b,
            status=ArenaBattle.BattleStatus.AWAITING_VOTE,
        )
        turn = ArenaTurn.objects.create(
            battle=battle,
            turn_number=1,
            prompt="Prompt 1",
            status=ArenaTurn.TurnStatus.COMPLETED,
        )
        BattleResponse.objects.create(
            turn=turn,
            slot=BattleResponse.ResponseSlot.A,
            status=BattleResponse.ResponseStatus.COMPLETED,
            response_text="A1",
        )

        response = self.client.patch(
            reverse(
                "arena-battle-response-update",
                kwargs={"id": battle.id, "turn_number": 1, "slot": "A"},
            ),
            {"response_text": "Edited A"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_experimental_response_rejects_non_latest_turn(self):
        battle = ArenaBattle.objects.create(
            model_a=self.model_a,
            model_b=self.model_b,
            status=ArenaBattle.BattleStatus.AWAITING_VOTE,
        )
        ExperimentConfig.objects.create(
            battle=battle,
            model_mode=ExperimentConfig.ModelMode.DIFFERENT_MODELS,
            share_values_across_models=False,
        )
        turn_one = ArenaTurn.objects.create(
            battle=battle,
            turn_number=1,
            prompt="Prompt 1",
            status=ArenaTurn.TurnStatus.COMPLETED,
        )
        turn_two = ArenaTurn.objects.create(
            battle=battle,
            turn_number=2,
            prompt="Prompt 2",
            status=ArenaTurn.TurnStatus.COMPLETED,
        )
        for turn, prefix in ((turn_one, "One"), (turn_two, "Two")):
            BattleResponse.objects.create(
                turn=turn,
                slot=BattleResponse.ResponseSlot.A,
                status=BattleResponse.ResponseStatus.COMPLETED,
                response_text=f"{prefix} A",
            )
            BattleResponse.objects.create(
                turn=turn,
                slot=BattleResponse.ResponseSlot.B,
                status=BattleResponse.ResponseStatus.COMPLETED,
                response_text=f"{prefix} B",
            )

        response = self.client.patch(
            reverse(
                "arena-battle-response-update",
                kwargs={"id": battle.id, "turn_number": 1, "slot": "A"},
            ),
            {"response_text": "Edited A"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_update_experimental_response_rejects_after_human_vote(self):
        battle = ArenaBattle.objects.create(
            model_a=self.model_a,
            model_b=self.model_b,
            status=ArenaBattle.BattleStatus.COMPLETED,
        )
        ExperimentConfig.objects.create(
            battle=battle,
            model_mode=ExperimentConfig.ModelMode.DIFFERENT_MODELS,
            share_values_across_models=False,
        )
        turn = ArenaTurn.objects.create(
            battle=battle,
            turn_number=1,
            prompt="Prompt 1",
            status=ArenaTurn.TurnStatus.COMPLETED,
        )
        BattleResponse.objects.create(
            turn=turn,
            slot=BattleResponse.ResponseSlot.A,
            status=BattleResponse.ResponseStatus.COMPLETED,
            response_text="A1",
        )
        BattleResponse.objects.create(
            turn=turn,
            slot=BattleResponse.ResponseSlot.B,
            status=BattleResponse.ResponseStatus.COMPLETED,
            response_text="B1",
        )
        BattleVote.objects.create(
            battle=battle,
            choice=BattleVote.VoteChoice.A,
            feedback="locked",
        )

        response = self.client.patch(
            reverse(
                "arena-battle-response-update",
                kwargs={"id": battle.id, "turn_number": 1, "slot": "A"},
            ),
            {"response_text": "Edited A"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_update_experimental_response_rejects_after_llm_judge_vote(self):
        battle = ArenaBattle.objects.create(
            model_a=self.model_a,
            model_b=self.model_b,
            status=ArenaBattle.BattleStatus.AWAITING_VOTE,
        )
        ExperimentConfig.objects.create(
            battle=battle,
            model_mode=ExperimentConfig.ModelMode.DIFFERENT_MODELS,
            share_values_across_models=False,
        )
        turn = ArenaTurn.objects.create(
            battle=battle,
            turn_number=1,
            prompt="Prompt 1",
            status=ArenaTurn.TurnStatus.COMPLETED,
        )
        BattleResponse.objects.create(
            turn=turn,
            slot=BattleResponse.ResponseSlot.A,
            status=BattleResponse.ResponseStatus.COMPLETED,
            response_text="A1",
        )
        BattleResponse.objects.create(
            turn=turn,
            slot=BattleResponse.ResponseSlot.B,
            status=BattleResponse.ResponseStatus.COMPLETED,
            response_text="B1",
        )
        LLMJudgeVote.objects.create(
            battle=battle,
            judge_model=self.model_a,
            choice=BattleVote.VoteChoice.B,
            reasoning="judge locked",
        )

        response = self.client.patch(
            reverse(
                "arena-battle-response-update",
                kwargs={"id": battle.id, "turn_number": 1, "slot": "A"},
            ),
            {"response_text": "Edited A"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_update_experimental_response_rejects_invalid_slot_and_missing_turn(self):
        battle = ArenaBattle.objects.create(
            model_a=self.model_a,
            model_b=self.model_b,
            status=ArenaBattle.BattleStatus.AWAITING_VOTE,
        )
        ExperimentConfig.objects.create(
            battle=battle,
            model_mode=ExperimentConfig.ModelMode.DIFFERENT_MODELS,
            share_values_across_models=False,
        )
        turn = ArenaTurn.objects.create(
            battle=battle,
            turn_number=1,
            prompt="Prompt 1",
            status=ArenaTurn.TurnStatus.COMPLETED,
        )
        BattleResponse.objects.create(
            turn=turn,
            slot=BattleResponse.ResponseSlot.A,
            status=BattleResponse.ResponseStatus.COMPLETED,
            response_text="A1",
        )
        BattleResponse.objects.create(
            turn=turn,
            slot=BattleResponse.ResponseSlot.B,
            status=BattleResponse.ResponseStatus.COMPLETED,
            response_text="B1",
        )

        missing_turn_response = self.client.patch(
            reverse(
                "arena-battle-response-update",
                kwargs={"id": battle.id, "turn_number": 9, "slot": "A"},
            ),
            {"response_text": "Edited A"},
            format="json",
        )
        invalid_slot_response = self.client.patch(
            reverse(
                "arena-battle-response-update",
                kwargs={"id": battle.id, "turn_number": 1, "slot": "C"},
            ),
            {"response_text": "Edited A"},
            format="json",
        )

        self.assertEqual(missing_turn_response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(invalid_slot_response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_experimental_response_rejects_blank_text(self):
        battle = ArenaBattle.objects.create(
            model_a=self.model_a,
            model_b=self.model_b,
            status=ArenaBattle.BattleStatus.AWAITING_VOTE,
        )
        ExperimentConfig.objects.create(
            battle=battle,
            model_mode=ExperimentConfig.ModelMode.DIFFERENT_MODELS,
            share_values_across_models=False,
        )
        turn = ArenaTurn.objects.create(
            battle=battle,
            turn_number=1,
            prompt="Prompt 1",
            status=ArenaTurn.TurnStatus.COMPLETED,
        )
        BattleResponse.objects.create(
            turn=turn,
            slot=BattleResponse.ResponseSlot.A,
            status=BattleResponse.ResponseStatus.COMPLETED,
            response_text="A1",
        )
        BattleResponse.objects.create(
            turn=turn,
            slot=BattleResponse.ResponseSlot.B,
            status=BattleResponse.ResponseStatus.COMPLETED,
            response_text="B1",
        )

        response = self.client.patch(
            reverse(
                "arena-battle-response-update",
                kwargs={"id": battle.id, "turn_number": 1, "slot": "A"},
            ),
            {"response_text": "   "},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch.object(ArenaService.inference_service, "generate_response_details_with_history")
    def test_continue_battle_uses_original_response_in_history_after_improvement(self, mock_generate):
        battle = ArenaBattle.objects.create(
            model_a=self.model_a,
            model_b=self.model_b,
            status=ArenaBattle.BattleStatus.AWAITING_VOTE,
        )
        ExperimentConfig.objects.create(
            battle=battle,
            model_mode=ExperimentConfig.ModelMode.DIFFERENT_MODELS,
            share_values_across_models=False,
        )
        turn = ArenaTurn.objects.create(
            battle=battle,
            turn_number=1,
            prompt="Turn one prompt",
            status=ArenaTurn.TurnStatus.COMPLETED,
        )
        BattleResponse.objects.create(
            turn=turn,
            slot=BattleResponse.ResponseSlot.A,
            status=BattleResponse.ResponseStatus.COMPLETED,
            response_text="Original A1",
        )
        BattleResponse.objects.create(
            turn=turn,
            slot=BattleResponse.ResponseSlot.B,
            status=BattleResponse.ResponseStatus.COMPLETED,
            response_text="Original B1",
        )
        update_response = self.client.patch(
            reverse(
                "arena-battle-response-update",
                kwargs={"id": battle.id, "turn_number": 1, "slot": "A"},
            ),
            {"response_text": "Edited A1"},
            format="json",
        )

        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        mock_generate.side_effect = [
            self._response_details("A2"),
            self._response_details("B2"),
        ]

        continue_response = self.client.post(
            reverse("arena-battle-turn-create", kwargs={"id": battle.id}),
            {"prompt": "Turn two prompt"},
            format="json",
        )

        self.assertEqual(continue_response.status_code, status.HTTP_201_CREATED)
        model_a_history = mock_generate.call_args_list[0].kwargs["history_messages"]
        model_b_history = mock_generate.call_args_list[1].kwargs["history_messages"]
        self.assertEqual(
            [(message.role, message.content) for message in model_a_history],
            [("user", "Turn one prompt"), ("assistant", "Original A1")],
        )
        self.assertEqual(
            [(message.role, message.content) for message in model_b_history],
            [("user", "Turn one prompt"), ("assistant", "Original B1")],
        )

    def test_leaderboard_counts_one_match_per_multi_turn_battle(self):
        battle = ArenaBattle.objects.create(
            model_a=self.model_a,
            model_b=self.model_b,
            status=ArenaBattle.BattleStatus.COMPLETED,
        )
        turn_one = ArenaTurn.objects.create(
            battle=battle,
            turn_number=1,
            prompt="Prompt 1",
            status=ArenaTurn.TurnStatus.COMPLETED,
        )
        turn_two = ArenaTurn.objects.create(
            battle=battle,
            turn_number=2,
            prompt="Prompt 2",
            status=ArenaTurn.TurnStatus.COMPLETED,
        )
        BattleResponse.objects.create(
            turn=turn_one,
            slot=BattleResponse.ResponseSlot.A,
            status=BattleResponse.ResponseStatus.COMPLETED,
            response_text="A1",
            prompt_tokens=4,
            completion_tokens=6,
            total_tokens=10,
            latency_ms=100,
        )
        BattleResponse.objects.create(
            turn=turn_one,
            slot=BattleResponse.ResponseSlot.B,
            status=BattleResponse.ResponseStatus.COMPLETED,
            response_text="B1",
            prompt_tokens=3,
            completion_tokens=5,
            total_tokens=8,
            latency_ms=120,
        )
        BattleResponse.objects.create(
            turn=turn_two,
            slot=BattleResponse.ResponseSlot.A,
            status=BattleResponse.ResponseStatus.COMPLETED,
            response_text="A2",
            prompt_tokens=5,
            completion_tokens=9,
            total_tokens=14,
            latency_ms=110,
        )
        BattleResponse.objects.create(
            turn=turn_two,
            slot=BattleResponse.ResponseSlot.B,
            status=BattleResponse.ResponseStatus.COMPLETED,
            response_text="B2",
            prompt_tokens=4,
            completion_tokens=8,
            total_tokens=12,
            latency_ms=130,
        )
        BattleVote.objects.create(
            battle=battle,
            choice=BattleVote.VoteChoice.A,
            feedback="A wins",
        )

        leaderboard = LeaderboardService().get_leaderboard()
        leaderboard_by_model_name = {
            entry["model_name"]: entry
            for entry in leaderboard
        }

        self.assertEqual(leaderboard_by_model_name[self.model_a.name]["matches"], 1)
        self.assertEqual(leaderboard_by_model_name[self.model_b.name]["matches"], 1)
        self.assertEqual(leaderboard_by_model_name[self.model_a.name]["wins"], 1)
        self.assertEqual(leaderboard_by_model_name[self.model_b.name]["losses"], 1)
        self.assertEqual(leaderboard_by_model_name[self.model_a.name]["avg_total_tokens"], 12.0)
        self.assertEqual(leaderboard_by_model_name[self.model_b.name]["avg_total_tokens"], 10.0)

    def test_leaderboard_excludes_experimental_battles(self):
        standard_battle = ArenaBattle.objects.create(
            model_a=self.model_a,
            model_b=self.model_b,
            status=ArenaBattle.BattleStatus.COMPLETED,
        )
        standard_turn = ArenaTurn.objects.create(
            battle=standard_battle,
            turn_number=1,
            prompt="Standard prompt",
            status=ArenaTurn.TurnStatus.COMPLETED,
        )
        BattleResponse.objects.create(
            turn=standard_turn,
            slot=BattleResponse.ResponseSlot.A,
            status=BattleResponse.ResponseStatus.COMPLETED,
            response_text="Standard A",
            total_tokens=12,
        )
        BattleResponse.objects.create(
            turn=standard_turn,
            slot=BattleResponse.ResponseSlot.B,
            status=BattleResponse.ResponseStatus.COMPLETED,
            response_text="Standard B",
            total_tokens=10,
        )
        BattleVote.objects.create(
            battle=standard_battle,
            choice=BattleVote.VoteChoice.A,
            feedback="Standard win",
        )

        experimental_battle = ArenaBattle.objects.create(
            model_a=self.model_a,
            model_b=self.model_b,
            status=ArenaBattle.BattleStatus.COMPLETED,
        )
        ExperimentConfig.objects.create(
            battle=experimental_battle,
            model_mode=ExperimentConfig.ModelMode.DIFFERENT_MODELS,
            share_values_across_models=False,
        )
        experimental_turn = ArenaTurn.objects.create(
            battle=experimental_battle,
            turn_number=1,
            prompt="Experimental prompt",
            status=ArenaTurn.TurnStatus.COMPLETED,
        )
        BattleResponse.objects.create(
            turn=experimental_turn,
            slot=BattleResponse.ResponseSlot.A,
            status=BattleResponse.ResponseStatus.COMPLETED,
            response_text="Experimental A",
            total_tokens=100,
        )
        BattleResponse.objects.create(
            turn=experimental_turn,
            slot=BattleResponse.ResponseSlot.B,
            status=BattleResponse.ResponseStatus.COMPLETED,
            response_text="Experimental B",
            total_tokens=90,
        )
        BattleVote.objects.create(
            battle=experimental_battle,
            choice=BattleVote.VoteChoice.B,
            feedback="Experimental win",
        )

        leaderboard = LeaderboardService().get_leaderboard()
        leaderboard_by_model_name = {
            entry["model_name"]: entry
            for entry in leaderboard
        }

        self.assertEqual(leaderboard_by_model_name[self.model_a.name]["matches"], 1)
        self.assertEqual(leaderboard_by_model_name[self.model_b.name]["matches"], 1)
        self.assertEqual(leaderboard_by_model_name[self.model_a.name]["wins"], 1)
        self.assertEqual(leaderboard_by_model_name[self.model_b.name]["losses"], 1)
        self.assertEqual(leaderboard_by_model_name[self.model_a.name]["avg_total_tokens"], 12.0)
        self.assertEqual(leaderboard_by_model_name[self.model_b.name]["avg_total_tokens"], 10.0)

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


class AgentServiceTests(APITestCase):
    def setUp(self) -> None:
        self.factory = RequestFactory()
        self.service = AgentService()
        self.provider = LLMProvider.objects.create(
            name="openai",
            display_name="OpenAI",
            description="OpenAI models",
            api_base_url="https://api.openai.com/v1",
        )
        self.model_a = LLMModel.objects.create(
            provider=self.provider,
            name="gpt-5.4",
            external_model_id="gpt-5.4",
            is_active=True,
        )
        self.model_b = LLMModel.objects.create(
            provider=self.provider,
            name="gpt-5.4-mini",
            external_model_id="gpt-5.4-mini",
            is_active=True,
        )
        self.judge_model = LLMModel.objects.create(
            provider=self.provider,
            name="gpt-4.1",
            external_model_id="gpt-4.1",
            is_active=True,
        )
        AgentPrompt.objects.create(
            agent_type=AgentPrompt.AgentType.JUDGE,
            name="Default judge prompt",
            system_prompt="You are a strict arena judge.",
            is_active=True,
        )

    @patch.object(AgentService, "_generate_judge_decision")
    def test_judge_battle_persists_judge_vote_and_sends_full_transcript(self, mock_generate_decision):
        battle = ArenaBattle.objects.create(
            model_a=self.model_a,
            model_b=self.model_b,
            status=ArenaBattle.BattleStatus.COMPLETED,
        )
        turn_one = ArenaTurn.objects.create(
            battle=battle,
            turn_number=1,
            prompt="Explain friendship.",
            status=ArenaTurn.TurnStatus.COMPLETED,
        )
        turn_two = ArenaTurn.objects.create(
            battle=battle,
            turn_number=2,
            prompt="Now explain loyalty.",
            status=ArenaTurn.TurnStatus.COMPLETED,
        )
        BattleResponse.objects.create(
            turn=turn_one,
            slot=BattleResponse.ResponseSlot.A,
            status=BattleResponse.ResponseStatus.COMPLETED,
            response_text="A1",
        )
        BattleResponse.objects.create(
            turn=turn_one,
            slot=BattleResponse.ResponseSlot.B,
            status=BattleResponse.ResponseStatus.COMPLETED,
            response_text="B1",
        )
        BattleResponse.objects.create(
            turn=turn_two,
            slot=BattleResponse.ResponseSlot.A,
            status=BattleResponse.ResponseStatus.COMPLETED,
            response_text="A2",
        )
        BattleResponse.objects.create(
            turn=turn_two,
            slot=BattleResponse.ResponseSlot.B,
            status=BattleResponse.ResponseStatus.COMPLETED,
            response_text="B2",
        )
        BattleVote.objects.create(
            battle=battle,
            choice=BattleVote.VoteChoice.A,
            feedback="Human picked A.",
        )
        mock_generate_decision.return_value = JudgeDecision(
            choice="B",
            reasoning="B stayed more consistent across both turns.",
        )

        judge_vote = self.service.judge_battle(battle.id, self.judge_model)

        self.assertEqual(judge_vote.choice, BattleVote.VoteChoice.B)
        self.assertEqual(judge_vote.reasoning, "B stayed more consistent across both turns.")
        self.assertEqual(judge_vote.judge_model, self.judge_model)
        self.assertTrue(LLMJudgeVote.objects.filter(battle=battle).exists())
        self.assertEqual(
            mock_generate_decision.call_args.kwargs["system_prompt"],
            "You are a strict arena judge.",
        )
        self.assertEqual(mock_generate_decision.call_args.kwargs["model"], self.judge_model)
        prompt = mock_generate_decision.call_args.kwargs["prompt"]
        self.assertIn("Turn 1", prompt)
        self.assertIn("User Prompt: Explain friendship.", prompt)
        self.assertIn("Response A: A1", prompt)
        self.assertIn("Response B: B2", prompt)

    def test_judge_action_form_only_lists_active_models(self):
        inactive_model = LLMModel.objects.create(
            provider=self.provider,
            name="inactive-model",
            external_model_id="inactive-model",
            is_active=False,
        )

        form = ArenaBattleJudgeActionForm()

        self.assertIn(self.model_a, form.fields["judge_model"].queryset)
        self.assertIn(self.judge_model, form.fields["judge_model"].queryset)
        self.assertNotIn(inactive_model, form.fields["judge_model"].queryset)

    def test_admin_action_judges_eligible_battles_and_skips_ineligible_ones(self):
        eligible_battle = ArenaBattle.objects.create(
            model_a=self.model_a,
            model_b=self.model_b,
            status=ArenaBattle.BattleStatus.COMPLETED,
        )
        BattleVote.objects.create(
            battle=eligible_battle,
            choice=BattleVote.VoteChoice.A,
            feedback="Eligible.",
        )
        ineligible_battle = ArenaBattle.objects.create(
            model_a=self.model_a,
            model_b=self.model_b,
            status=ArenaBattle.BattleStatus.AWAITING_VOTE,
        )
        arena_battle_admin = ArenaBattleAdmin(ArenaBattle, admin.site)
        request = self.factory.post(
            "/admin/llm_arena/arenabattle/",
            {
                "action": "judge_selected_battles",
                "judge_model": str(self.judge_model.pk),
            },
        )

        def judge_side_effect(*, battle_id, judge_model):
            if battle_id == ineligible_battle.id:
                raise ArenaBattleMissingHumanVoteException(
                    detail=f"Battle '{battle_id}' must have a human vote before LLM judging."
                )

        with patch.object(arena_battle_admin.agent_service, "judge_battle") as mock_judge, patch.object(
            arena_battle_admin, "message_user"
        ) as mock_message_user:
            mock_judge.side_effect = judge_side_effect
            arena_battle_admin.judge_selected_battles(
                request,
                ArenaBattle.objects.filter(pk__in=[eligible_battle.pk, ineligible_battle.pk]),
            )

        self.assertEqual(mock_judge.call_count, 2)
        mock_judge.assert_any_call(
            battle_id=eligible_battle.id,
            judge_model=self.judge_model,
        )
        self.assertTrue(mock_message_user.called)
