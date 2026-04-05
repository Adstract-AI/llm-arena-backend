from django.urls import path

from experimental_llm_arena.views import ExperimentalArenaBattleCreateView

urlpatterns = [
    path("battles/", ExperimentalArenaBattleCreateView.as_view(), name="experimental-arena-battle-create"),
]

