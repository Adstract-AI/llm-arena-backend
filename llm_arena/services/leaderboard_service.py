from dataclasses import asdict, dataclass
from math import pow
from typing import Any

from common.abstract import AbstractService
from llm_arena.models import BattleVote, LLMModel
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
    """Aggregate voted battle outcomes into leaderboard statistics for active models."""

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
            BattleVote.objects.select_related("battle")
            .prefetch_related("battle__responses__llm_model__provider")
            .order_by("created_at")
        )

        for vote in votes:
            responses = list(vote.battle.responses.all())
            if len(responses) != 2:
                continue

            left_response = responses[0]
            right_response = responses[1]
            if (
                left_response.llm_model_id not in stats_by_model_id
                or right_response.llm_model_id not in stats_by_model_id
            ):
                continue

            left_stats = stats_by_model_id[left_response.llm_model_id]
            right_stats = stats_by_model_id[right_response.llm_model_id]

            self._update_match_counts(left_stats, left_response)
            self._update_match_counts(right_stats, right_response)
            self._apply_vote_result(
                vote_choice=vote.choice,
                left_response=left_response,
                right_response=right_response,
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

    def _update_match_counts(self, stats: dict[str, Any], response) -> None:
        """
        Update aggregate counters for a single persisted response.

        Args:
            stats: Mutable model statistics accumulator.
            response: Persisted battle response row.
        """
        stats["matches"] += 1

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
        left_response,
        right_response,
        left_stats: dict[str, Any],
        right_stats: dict[str, Any],
    ) -> None:
        """
        Apply a single battle outcome to win/loss/tie counters and Elo ratings.

        Args:
            vote_choice: Stored vote choice for the battle.
            left_response: First response in the battle.
            right_response: Second response in the battle.
            left_stats: Mutable stats accumulator for the first model.
            right_stats: Mutable stats accumulator for the second model.
        """
        if vote_choice == BattleVote.VoteChoice.TIE:
            left_stats["ties"] += 1
            right_stats["ties"] += 1
            left_score = 0.5
            right_score = 0.5
        elif vote_choice == left_response.slot:
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
        model = stats["model"]

        return LeaderboardEntry(
            model_name=model.name,
            provider_name=model.provider.name,
            provider_display_name=model.provider.display_name,
            matches=matches,
            wins=wins,
            losses=losses,
            ties=ties,
            win_rate=round((wins / matches), 4) if matches else 0.0,
            non_tie_win_rate=round((wins / decisive_matches), 4) if decisive_matches else None,
            elo_score=round(stats["elo_score"], 2),
            avg_prompt_tokens=self._compute_average(stats["prompt_tokens_sum"], stats["prompt_tokens_count"]),
            avg_completion_tokens=self._compute_average(
                stats["completion_tokens_sum"],
                stats["completion_tokens_count"],
            ),
            avg_total_tokens=self._compute_average(stats["total_tokens_sum"], stats["total_tokens_count"]),
            avg_latency_ms=self._compute_average(stats["latency_ms_sum"], stats["latency_ms_count"]),
            avg_response_length_chars=self._compute_average(
                stats["response_length_sum"],
                stats["response_length_count"],
            ),
        )

    @staticmethod
    def _compute_average(total: int, count: int) -> float | None:
        """
        Compute a rounded average or None when no observations exist.

        Args:
            total: Sum of observed values.
            count: Number of observations.

        Returns:
            float | None: Rounded average when available, otherwise None.
        """
        if count == 0:
            return None
        return round(total / count, 2)
