from rest_framework import serializers


class OAuthCodeRequestSerializer(serializers.Serializer):
    code = serializers.CharField()


class AuthenticatedUserSerializer(serializers.Serializer):
    email = serializers.EmailField()
    username = serializers.CharField()


class OAuthLoginResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()
    user = AuthenticatedUserSerializer()
