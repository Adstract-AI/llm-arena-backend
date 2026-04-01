from dataclasses import asdict, dataclass
from math import pow
from typing import Any

from django.db.models import Prefetch

from common.abstract import AbstractService
from llm_arena.models import ArenaTurn, BattleResponse, BattleVote, LLMModel
from llm_arena.services.llm_model_service import LLMModelService


@dataclass
class LeaderboardEntry:
    model_name: str
    provider_name: str
    provider_display_name: str
    matches: int
    wins: int
    losses: int
    ties: int
    win_rate: float
    non_tie_win_rate: float | None
    elo_score: float
    avg_prompt_tokens: float | None
    avg_completion_tokens: float | None
    avg_total_tokens: float | None
    avg_latency_ms: float | None
    avg_response_length_chars: float | None


class LeaderboardService(AbstractService):
    """Aggregate voted multi-turn battle outcomes into leaderboard statistics."""

    DEFAULT_ELO_SCORE = 1000.0
    ELO_K_FACTOR = 32.0

    llm_model_service = LLMModelService()

    def get_leaderboard(self) -> list[dict[str, Any]]:
        """
        Build leaderboard statistics for all active models.

        Returns:
            list[dict[str, Any]]: Sorted leaderboard entries with derived model statistics.
        """
        active_models = list(self.llm_model_service.get_active_models())
        stats_by_model_id = {
            model.id: self._initialize_model_stats(model)
            for model in active_models
        }

        votes = (
            BattleVote.objects
            .filter(battle__experiment_config__isnull=True)
            .select_related("battle__model_a__provider", "battle__model_b__provider")
            .prefetch_related(
                Prefetch(
                    "battle__turns",
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
            .order_by("created_at")
        )

        for vote in votes:
            battle = vote.battle
            if (
                battle.model_a_id not in stats_by_model_id
                or battle.model_b_id not in stats_by_model_id
            ):
                continue

            left_stats = stats_by_model_id[battle.model_a_id]
            right_stats = stats_by_model_id[battle.model_b_id]

            self._update_match_counts(left_stats)
            self._update_match_counts(right_stats)

            for turn in battle.turns.all():
                responses_by_slot = {
                    response.slot: response
                    for response in turn.responses.all()
                }
                if BattleResponse.ResponseSlot.A in responses_by_slot:
                    self._update_response_metrics(left_stats, responses_by_slot[BattleResponse.ResponseSlot.A])
                if BattleResponse.ResponseSlot.B in responses_by_slot:
                    self._update_response_metrics(right_stats, responses_by_slot[BattleResponse.ResponseSlot.B])

            self._apply_vote_result(
                vote_choice=vote.choice,
                left_stats=left_stats,
                right_stats=right_stats,
            )

        leaderboard_entries = [
            self._build_entry(stats)
            for stats in stats_by_model_id.values()
        ]
        leaderboard_entries.sort(
            key=lambda entry: (
                entry.elo_score,
                entry.wins,
                entry.matches,
                entry.model_name,
            ),
            reverse=True,
        )
        return [asdict(entry) for entry in leaderboard_entries]

    def get_model_leaderboard_entry(self, model: LLMModel) -> dict[str, Any]:
        """
        Return leaderboard statistics for a single model.

        Args:
            model: Model to fetch leaderboard statistics for.

        Returns:
            dict[str, Any]: Leaderboard entry for the requested model.
        """
        leaderboard = self.get_leaderboard()
        for entry in leaderboard:
            if (
                entry["provider_name"] == model.provider.name
                and entry["model_name"] == model.name
            ):
                return entry

        return asdict(
            LeaderboardEntry(
                model_name=model.name,
                provider_name=model.provider.name,
                provider_display_name=model.provider.display_name,
                matches=0,
                wins=0,
                losses=0,
                ties=0,
                win_rate=0.0,
                non_tie_win_rate=None,
                elo_score=self.DEFAULT_ELO_SCORE,
                avg_prompt_tokens=None,
                avg_completion_tokens=None,
                avg_total_tokens=None,
                avg_latency_ms=None,
                avg_response_length_chars=None,
            )
        )

    def _initialize_model_stats(self, model: LLMModel) -> dict[str, Any]:
        """
        Create the mutable accumulator for a single model.

        Args:
            model: Active model to initialize.

        Returns:
            dict[str, Any]: Mutable statistics accumulator.
        """
        return {
            "model": model,
            "matches": 0,
            "wins": 0,
            "losses": 0,
            "ties": 0,
            "elo_score": self.DEFAULT_ELO_SCORE,
            "prompt_tokens_sum": 0,
            "prompt_tokens_count": 0,
            "completion_tokens_sum": 0,
            "completion_tokens_count": 0,
            "total_tokens_sum": 0,
            "total_tokens_count": 0,
            "latency_ms_sum": 0,
            "latency_ms_count": 0,
            "response_length_sum": 0,
            "response_length_count": 0,
        }

    @staticmethod
    def _update_match_counts(stats: dict[str, Any]) -> None:
        """
        Increment the match counter for one battle result.

        Args:
            stats: Mutable model statistics accumulator.
        """
        stats["matches"] += 1

    @staticmethod
    def _update_response_metrics(stats: dict[str, Any], response: BattleResponse) -> None:
        """
        Update aggregate token, latency, and length counters for one response row.

        Args:
            stats: Mutable model statistics accumulator.
            response: Persisted battle response row.
        """
        if response.prompt_tokens is not None:
            stats["prompt_tokens_sum"] += response.prompt_tokens
            stats["prompt_tokens_count"] += 1
        if response.completion_tokens is not None:
            stats["completion_tokens_sum"] += response.completion_tokens
            stats["completion_tokens_count"] += 1
        if response.total_tokens is not None:
            stats["total_tokens_sum"] += response.total_tokens
            stats["total_tokens_count"] += 1
        if response.latency_ms is not None:
            stats["latency_ms_sum"] += response.latency_ms
            stats["latency_ms_count"] += 1

        response_text = response.response_text or ""
        if response_text:
            stats["response_length_sum"] += len(response_text)
            stats["response_length_count"] += 1

    def _apply_vote_result(
        self,
        vote_choice: str,
        left_stats: dict[str, Any],
        right_stats: dict[str, Any],
    ) -> None:
        """
        Apply a single battle outcome to win/loss/tie counters and Elo ratings.

        Args:
            vote_choice: Stored vote choice for the battle.
            left_stats: Mutable stats accumulator for the A-slot model.
            right_stats: Mutable stats accumulator for the B-slot model.
        """
        if vote_choice == BattleVote.VoteChoice.TIE:
            left_stats["ties"] += 1
            right_stats["ties"] += 1
            left_score = 0.5
            right_score = 0.5
        elif vote_choice == BattleResponse.ResponseSlot.A:
            left_stats["wins"] += 1
            right_stats["losses"] += 1
            left_score = 1.0
            right_score = 0.0
        else:
            left_stats["losses"] += 1
            right_stats["wins"] += 1
            left_score = 0.0
            right_score = 1.0

        left_expected = self._expected_score(left_stats["elo_score"], right_stats["elo_score"])
        right_expected = self._expected_score(right_stats["elo_score"], left_stats["elo_score"])

        left_stats["elo_score"] += self.ELO_K_FACTOR * (left_score - left_expected)
        right_stats["elo_score"] += self.ELO_K_FACTOR * (right_score - right_expected)

    @staticmethod
    def _expected_score(player_rating: float, opponent_rating: float) -> float:
        """
        Compute the expected Elo score for a head-to-head matchup.

        Args:
            player_rating: Current Elo rating for the player model.
            opponent_rating: Current Elo rating for the opponent model.

        Returns:
            float: Expected score between 0 and 1.
        """
        return 1.0 / (1.0 + pow(10.0, (opponent_rating - player_rating) / 400.0))

    def _build_entry(self, stats: dict[str, Any]) -> LeaderboardEntry:
        """
        Convert a mutable stats accumulator into the serialized leaderboard shape.

        Args:
            stats: Mutable model statistics accumulator.

        Returns:
            LeaderboardEntry: Final leaderboard entry.
        """
        matches = stats["matches"]
        wins = stats["wins"]
        losses = stats["losses"]
        ties = stats["ties"]
        decisive_matches = wins + losses

        def average(sum_key: str, count_key: str) -> float | None:
            count = stats[count_key]
            if count == 0:
                return None
            return stats[sum_key] / count

        return LeaderboardEntry(
            model_name=stats["model"].name,
            provider_name=stats["model"].provider.name,
            provider_display_name=stats["model"].provider.display_name,
            matches=matches,
            wins=wins,
            losses=losses,
            ties=ties,
            win_rate=(wins / matches) if matches else 0.0,
            non_tie_win_rate=(wins / decisive_matches) if decisive_matches else None,
            elo_score=stats["elo_score"],
            avg_prompt_tokens=average("prompt_tokens_sum", "prompt_tokens_count"),
            avg_completion_tokens=average("completion_tokens_sum", "completion_tokens_count"),
            avg_total_tokens=average("total_tokens_sum", "total_tokens_count"),
            avg_latency_ms=average("latency_ms_sum", "latency_ms_count"),
            avg_response_length_chars=average("response_length_sum", "response_length_count"),
        )
