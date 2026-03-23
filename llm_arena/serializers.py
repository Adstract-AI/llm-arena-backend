from rest_framework import serializers

from llm_arena.models import BattleResponse, BattleVote


class BattleCreateRequestSerializer(serializers.Serializer):
    prompt = serializers.CharField()


class BattleResponseSerializer(serializers.Serializer):
    slot = serializers.ChoiceField(choices=BattleResponse.ResponseSlot.choices)
    response_text = serializers.CharField()


class BattleCreateResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    prompt = serializers.CharField()
    responses = BattleResponseSerializer(many=True)


class BattleVoteRequestSerializer(serializers.Serializer):
    choice = serializers.ChoiceField(choices=BattleVote.VoteChoice.choices)
    feedback = serializers.CharField(required=False, allow_blank=True)


class BattleVoteRevealResponseSerializer(serializers.Serializer):
    slot = serializers.ChoiceField(choices=BattleResponse.ResponseSlot.choices)
    response_text = serializers.CharField()
    model_name = serializers.CharField()
    provider_name = serializers.CharField()
    provider_display_name = serializers.CharField()
    is_winner = serializers.BooleanField()


class BattleVoteResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    choice = serializers.ChoiceField(choices=BattleVote.VoteChoice.choices)
    feedback = serializers.CharField(allow_blank=True)
    winner_provider_name = serializers.CharField(allow_null=True)
    winner_model_name = serializers.CharField(allow_null=True)
    responses = BattleVoteRevealResponseSerializer(many=True)


class LeaderboardEntrySerializer(serializers.Serializer):
    model_name = serializers.CharField()
    provider_name = serializers.CharField()
    provider_display_name = serializers.CharField()
    matches = serializers.IntegerField()
    wins = serializers.IntegerField()
    losses = serializers.IntegerField()
    ties = serializers.IntegerField()
    win_rate = serializers.FloatField()
    non_tie_win_rate = serializers.FloatField(allow_null=True)
    elo_score = serializers.FloatField()
    avg_prompt_tokens = serializers.FloatField(allow_null=True)
    avg_completion_tokens = serializers.FloatField(allow_null=True)
    avg_total_tokens = serializers.FloatField(allow_null=True)
    avg_latency_ms = serializers.FloatField(allow_null=True)
    avg_response_length_chars = serializers.FloatField(allow_null=True)


class LLMModelDetailSerializer(serializers.Serializer):
    name = serializers.CharField()
    external_model_id = serializers.CharField()
    description = serializers.CharField(allow_blank=True)
    provider_name = serializers.CharField()
    provider_display_name = serializers.CharField()
    provider_description = serializers.CharField(allow_blank=True)
    is_fine_tuned = serializers.BooleanField()
    is_macedonian_optimized = serializers.BooleanField()
    matches = serializers.IntegerField()
    wins = serializers.IntegerField()
    losses = serializers.IntegerField()
    ties = serializers.IntegerField()
    win_rate = serializers.FloatField()
    non_tie_win_rate = serializers.FloatField(allow_null=True)
    elo_score = serializers.FloatField()
    avg_prompt_tokens = serializers.FloatField(allow_null=True)
    avg_completion_tokens = serializers.FloatField(allow_null=True)
    avg_total_tokens = serializers.FloatField(allow_null=True)
    avg_latency_ms = serializers.FloatField(allow_null=True)
    avg_response_length_chars = serializers.FloatField(allow_null=True)
