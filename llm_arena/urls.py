from django.urls import path

from llm_arena.views import ArenaBattleCreateView, ArenaBattleVoteCreateView, LeaderboardListView

urlpatterns = [
    # Arena leaderboard
    path("leaderboard/", LeaderboardListView.as_view(), name="arena-leaderboard-list"),

    # Arena battles
    path("battles/", ArenaBattleCreateView.as_view(), name="arena-battle-create"),
    path("battles/<uuid:id>/vote/", ArenaBattleVoteCreateView.as_view(), name="arena-battle-vote-create"),
]
