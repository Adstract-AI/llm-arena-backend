from django.urls import path

from llm_arena.views import ArenaBattleCreateView, ArenaBattleVoteCreateView

urlpatterns = [
    # Arena battles
    path("battles/", ArenaBattleCreateView.as_view(), name="arena-battle-create"),
    path("battles/<uuid:battle_id>/vote/", ArenaBattleVoteCreateView.as_view(), name="arena-battle-vote-create"),
]
