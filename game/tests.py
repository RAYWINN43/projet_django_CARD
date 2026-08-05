from django.test import TestCase

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
