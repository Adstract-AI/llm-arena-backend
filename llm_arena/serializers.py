from rest_framework import serializers

from llm_arena.models import ArenaBattle, BattleResponse, BattleVote


class BattleCreateRequestSerializer(serializers.Serializer):
    prompt = serializers.CharField()


class BattleTurnCreateRequestSerializer(serializers.Serializer):
    prompt = serializers.CharField()


class ArenaTurnResponseSerializer(serializers.Serializer):
    slot = serializers.ChoiceField(choices=BattleResponse.ResponseSlot.choices)
    response_text = serializers.CharField()


class ArenaTurnSerializer(serializers.Serializer):
    turn_number = serializers.IntegerField()
    prompt = serializers.CharField()
    responses = ArenaTurnResponseSerializer(many=True)


class ArenaBattleSnapshotSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    status = serializers.ChoiceField(choices=ArenaBattle.BattleStatus.choices)
    can_vote = serializers.BooleanField()
    turns = ArenaTurnSerializer(many=True)


class BattleVoteRequestSerializer(serializers.Serializer):
    choice = serializers.ChoiceField(choices=BattleVote.VoteChoice.choices)
    feedback = serializers.CharField(required=False, allow_blank=True)


class BattleVoteRevealModelSerializer(serializers.Serializer):
    slot = serializers.ChoiceField(choices=BattleResponse.ResponseSlot.choices)
    model_name = serializers.CharField()
    provider_name = serializers.CharField()
    provider_display_name = serializers.CharField()
    is_winner = serializers.BooleanField()


class BattleVoteTurnResponseSerializer(serializers.Serializer):
    slot = serializers.ChoiceField(choices=BattleResponse.ResponseSlot.choices)
    response_text = serializers.CharField()
    is_winner = serializers.BooleanField()


class BattleVoteTurnSerializer(serializers.Serializer):
    turn_number = serializers.IntegerField()
    prompt = serializers.CharField()
    responses = BattleVoteTurnResponseSerializer(many=True)


class BattleVoteExperimentParameterSerializer(serializers.Serializer):
    enabled = serializers.BooleanField()
    distribution = serializers.CharField(allow_null=True)
    slot_a_value = serializers.FloatField(allow_null=True)
    slot_b_value = serializers.FloatField(allow_null=True)


class BattleVoteExperimentTopKParameterSerializer(serializers.Serializer):
    enabled = serializers.BooleanField()
    distribution = serializers.CharField(allow_null=True)
    slot_a_value = serializers.IntegerField(allow_null=True)
    slot_b_value = serializers.IntegerField(allow_null=True)


class BattleVoteExperimentParametersSerializer(serializers.Serializer):
    temperature = BattleVoteExperimentParameterSerializer()
    top_p = BattleVoteExperimentParameterSerializer()
    top_k = BattleVoteExperimentTopKParameterSerializer()
    frequency_penalty = BattleVoteExperimentParameterSerializer()
    presence_penalty = BattleVoteExperimentParameterSerializer()


class BattleVoteExperimentSerializer(serializers.Serializer):
    model_mode = serializers.CharField()
    share_values_across_models = serializers.BooleanField(allow_null=True)
    parameters = BattleVoteExperimentParametersSerializer()


class BattleVoteResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    status = serializers.ChoiceField(choices=ArenaBattle.BattleStatus.choices)
    choice = serializers.ChoiceField(choices=BattleVote.VoteChoice.choices)
    feedback = serializers.CharField(allow_blank=True)
    winner_provider_name = serializers.CharField(allow_null=True)
    winner_model_name = serializers.CharField(allow_null=True)
    models = BattleVoteRevealModelSerializer(many=True)
    turns = BattleVoteTurnSerializer(many=True)
    experiment = BattleVoteExperimentSerializer(required=False, allow_null=True)


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
