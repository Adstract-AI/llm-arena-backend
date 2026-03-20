from rest_framework import serializers

from llm_arena.models import BattleResponse, BattleVote


class BattleCreateRequestSerializer(serializers.Serializer):
    prompt = serializers.CharField()


class BattleResponseSerializer(serializers.Serializer):
    slot = serializers.ChoiceField(choices=BattleResponse.ResponseSlot.choices)
    response_text = serializers.CharField()


class BattleCreateResponseSerializer(serializers.Serializer):
    battle_id = serializers.UUIDField()
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


class BattleVoteResponseSerializer(serializers.Serializer):
    battle_id = serializers.UUIDField()
    choice = serializers.ChoiceField(choices=BattleVote.VoteChoice.choices)
    feedback = serializers.CharField(allow_blank=True)
    responses = BattleVoteRevealResponseSerializer(many=True)
