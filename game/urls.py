from django.urls import path
from . import views

urlpatterns = [
    path("", views.game_page, name="game_page"),
    path("launch", views.launch_game, name="launch_game"),
    path("<int:game_id>/launch", views.play_game, name="launch_game_id"),
    path("<int:game_id>/play/<str:move>", views.play_turn, name="play_turn"),
]