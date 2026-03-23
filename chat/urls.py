from django.urls import path

from chat.views import ChatMessageCreateView, FinkiModelListView

urlpatterns = [
    # FINKI chat models
    path("models/", FinkiModelListView.as_view(), name="chat-model-list"),

    # Session-backed chat messages
    path("messages/", ChatMessageCreateView.as_view(), name="chat-message-create"),
]
