from rest_framework import serializers


class FinkiModelSerializer(serializers.Serializer):
    name = serializers.CharField()
    external_model_id = serializers.CharField()
    description = serializers.CharField()


class ChatMessageRequestSerializer(serializers.Serializer):
    provider_name = serializers.CharField()
    model_name = serializers.CharField()
    message = serializers.CharField()
    session_id = serializers.UUIDField(required=False)


class ChatMessageResponseSerializer(serializers.Serializer):
    session_id = serializers.UUIDField()
    response_text = serializers.CharField()
    model_name = serializers.CharField()
    provider_name = serializers.CharField()
