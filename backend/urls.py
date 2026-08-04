from django.urls import path
import views

urlpatterns = [
    path("game/<int:game_id>/play", views.play_game, name="play_game"),
    path("game/<int:game_id>/play/<str:move>", views.play_turn, name="play_turn"),
]