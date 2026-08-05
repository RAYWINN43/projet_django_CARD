from django.contrib.auth import get_user_model
from django.test import TestCase

from accounts.models import Profile
from .models import Game

# Test de Copilot pour vérifier que les données survivent d'une action à l'autre dans une partie
class GameModelTests(TestCase):
    def test_game_running_state_survives_reload(self):
        game = Game.objects.create()
        game.new_game(bet=30)

        reloaded_game = Game.objects.get(id=game.id)
        self.assertEqual(len(reloaded_game._player_hand.cards), 2)

        reloaded_game.hit()

        self.assertEqual(len(reloaded_game._player_hand.cards), 3)

# Test de Copilot pour vérifier que la partie utilise bien les jetons du joueur
    def test_new_game_syncs_player_bank_with_profile_jetons(self):
        user_model = get_user_model()
        user = user_model.objects.create_user(
            username="alice",
            password="secret123",
        )
        profile = Profile.objects.get(user=user)
        profile.jetons = 500
        profile.save()

        game = Game.objects.create()
        game.new_game(bet=30, profile=profile)

        profile.refresh_from_db()

        self.assertEqual(game.player.bank, 470)
        self.assertEqual(profile.jetons, 470)
