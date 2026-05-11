from django.urls import path

from experimental_llm_arena.views import (
    ExperimentalArenaBattleCreateView,
    ExperimentalArenaBattleStreamCreateView,
)

urlpatterns = [
    path("battles/", ExperimentalArenaBattleCreateView.as_view(), name="experimental-arena-battle-create"),
    path(
        "battles/stream/",
        ExperimentalArenaBattleStreamCreateView.as_view(),
        name="experimental-arena-battle-stream-create",
    ),
]
