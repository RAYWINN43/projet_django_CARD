from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from game.models import Game, GameResult, GameState, MoveLog


class AdminPlayerDashboardTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.admin_user = user_model.objects.create_superuser(
            username="dashboard-admin",
            email="dashboard-admin@example.com",
            password="Strong-admin-pass-123!",
        )
        self.player = user_model.objects.create_user(
            username="alice",
            email="alice@example.com",
            password="Strong-player-pass-123!",
        )
        self.player.profile.jetons = 850
        self.player.profile.save(update_fields=["jetons"])
        self.client.force_login(self.admin_user)

        self.won_game = Game(
            profile=self.player.profile,
            state=GameState.FINISHED,
            result=GameResult.PLAYER,
            player_bank=880,
            pool=20,
            bet_value=20,
            running=False,
            player_hand={
                "visible": True,
                "cards": [
                    {"value": 1, "suit": "spades", "true_value": 1},
                    {"value": 10, "suit": "hearts", "true_value": 10},
                ],
            },
            croupier_hand={
                "visible": True,
                "cards": [
                    {"value": 10, "suit": "clubs", "true_value": 10},
                    {"value": 8, "suit": "diamonds", "true_value": 8},
                ],
            },
        )
        self.lost_game = Game(
            profile=self.player.profile,
            state=GameState.FINISHED,
            result=GameResult.DEALER,
            player_bank=850,
            pool=10,
            bet_value=10,
            running=False,
        )
        Game.objects.bulk_create([self.won_game, self.lost_game])
        MoveLog.objects.create(
            game=self.won_game,
            move=MoveLog.Move.HIT,
            actor=MoveLog.Actor.PLAYER,
            card={"value": 10, "suit": "hearts", "true_value": 10},
        )

    def test_admin_home_lists_recent_players_with_search(self):
        response = self.client.get(reverse("admin:index"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Derniers joueurs")
        self.assertContains(response, "Rechercher un joueur")
        self.assertContains(response, "alice@example.com")
        self.assertContains(response, "+10")

    def test_history_endpoint_returns_bank_gain_games_cards_and_moves(self):
        response = self.client.get(
            reverse("admin:accounts_profile_history", args=[self.player.profile.id])
        )
        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["player"]["username"], "alice")
        self.assertEqual(payload["player"]["bank"], 850)
        self.assertEqual(payload["player"]["total_gain"], 10)
        self.assertEqual(len(payload["games"]), 2)
        won_game = next(game for game in payload["games"] if game["result"] == "player")
        self.assertEqual(won_game["player_cards"][0]["value"], 1)
        self.assertEqual(won_game["moves"][0]["move"], "Pioche")

    def test_non_staff_user_cannot_access_history_endpoint(self):
        self.client.force_login(self.player)

        response = self.client.get(
            reverse("admin:accounts_profile_history", args=[self.player.profile.id])
        )

        self.assertEqual(response.status_code, 302)


class GameAudioTemplateTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="audio-player",
            password="Strong-player-pass-456!",
        )
        self.client.force_login(self.user)

    def test_game_uses_trimmed_bubble_m4a_effect(self):
        response = self.client.get(reverse("game_page"))

        self.assertContains(response, "assets/bubble.m4a")
        self.assertNotContains(response, "BUBBLE POP SOUND EFFECT - FREE.mp3")
