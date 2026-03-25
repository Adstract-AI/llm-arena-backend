from django.urls import path

from llm_arena.views import (
    ArenaBattleCreateView,
    ArenaBattleDetailView,
    ArenaBattleTurnCreateView,
    ArenaBattleVoteCreateView,
    LeaderboardListView,
    LLMModelDetailView,
)

urlpatterns = [
    # Arena leaderboard
    path("leaderboard/", LeaderboardListView.as_view(), name="arena-leaderboard-list"),

    # Arena models
    path("models/<str:model_name>/", LLMModelDetailView.as_view(), name="arena-model-detail"),

    # Arena battles
    path("battles/", ArenaBattleCreateView.as_view(), name="arena-battle-create"),
    path("battles/<uuid:id>/", ArenaBattleDetailView.as_view(), name="arena-battle-detail"),
    path("battles/<uuid:id>/turns/", ArenaBattleTurnCreateView.as_view(), name="arena-battle-turn-create"),
    path("battles/<uuid:id>/vote/", ArenaBattleVoteCreateView.as_view(), name="arena-battle-vote-create"),
]
