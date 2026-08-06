from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from accounts.models import Profile

from .game_engine import Card, Deck, GameRuleError, Player, evaluate_round
from .models import Game, GameResult, GameState, MoveLog


class GameEngineTests(TestCase):
    def test_fresh_deck_contains_52_unique_cards(self):
        deck = Deck()
        deck.init_deck()

        self.assertEqual(len(deck.cards), 52)
        self.assertEqual(len({(card.value, card.suit) for card in deck.cards}), 52)

    def test_draw_removes_one_card(self):
        deck = Deck(cards=[Card(2, "clubs"), Card(3, "spades")])

        drawn = deck.draw()

        self.assertEqual(str(drawn), "3S")
        self.assertEqual(len(deck.cards), 1)

    def test_ace_is_worth_eleven_when_it_does_not_bust(self):
        hand = Deck(cards=[Card(10, "spades"), Card(1, "hearts")])

        self.assertEqual(hand.hand_value(), 21)

    def test_multiple_aces_are_counted_safely(self):
        hand = Deck(cards=[Card(1, "spades"), Card(1, "hearts"), Card(9, "clubs")])

        self.assertEqual(hand.hand_value(), 21)

    def test_player_cannot_debit_invalid_or_unavailable_amount(self):
        player = Player(bank=20)

        with self.assertRaises(GameRuleError):
            player.debit(0)
        with self.assertRaises(GameRuleError):
            player.debit(21)
        self.assertEqual(player.bank, 20)

    def test_round_evaluator_handles_player_dealer_and_draw(self):
        self.assertEqual(evaluate_round(20, 18).winner, "player")
        self.assertEqual(evaluate_round(22, 18).winner, "dealer")
        self.assertEqual(evaluate_round(18, 18).winner, "draw")


class GameModelTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="alice", password="Strong-pass-123!"
        )
        self.profile = Profile.objects.get(user=self.user)
        self.profile.jetons = 500
        self.profile.save(update_fields=["jetons"])

    def make_game(self, bet=30):
        game = Game.objects.create(
            profile=self.profile, player_bank=self.profile.jetons
        )
        game.new_game(bet=bet)
        return game

    def test_new_game_persists_cards_bank_state_and_deal_log(self):
        game = self.make_game()
        reloaded_game = Game.objects.get(id=game.id)
        self.profile.refresh_from_db()

        self.assertEqual(len(reloaded_game._player_hand.cards), 2)
        self.assertEqual(reloaded_game.state, GameState.PLAYER_TURN)
        self.assertEqual(reloaded_game.player_bank, 470)
        self.assertEqual(self.profile.jetons, 470)
        self.assertTrue(reloaded_game.moves.filter(move=MoveLog.Move.DEAL).exists())

    def test_negative_and_overdraft_bets_are_rejected(self):
        for invalid_bet in (-10, 0, 501):
            game = Game(profile=self.profile, player_bank=self.profile.jetons)
            with self.assertRaises(GameRuleError):
                game.new_game(bet=invalid_bet)

        self.profile.refresh_from_db()
        self.assertEqual(self.profile.jetons, 500)

    def test_hit_survives_reload_and_creates_move_log(self):
        game = self.make_game()

        Game.objects.get(id=game.id).hit()
        reloaded_game = Game.objects.get(id=game.id)

        self.assertEqual(len(reloaded_game._player_hand.cards), 3)
        self.assertTrue(reloaded_game.moves.filter(move=MoveLog.Move.HIT).exists())

    def test_double_updates_pool_bank_state_and_log(self):
        game = self.make_game()

        game.double()
        self.profile.refresh_from_db()

        self.assertEqual(game.pool, 60)
        self.assertEqual(game.player.bank, 440)
        self.assertEqual(self.profile.jetons, 440)
        self.assertEqual(game.state, GameState.DEALER_TURN)
        self.assertTrue(game.moves.filter(move=MoveLog.Move.DOUBLE).exists())

    def test_double_is_rejected_when_bank_is_insufficient(self):
        self.profile.jetons = 40
        self.profile.save(update_fields=["jetons"])
        game = self.make_game(bet=30)

        with self.assertRaises(GameRuleError):
            game.double()

        self.assertEqual(game.pool, 30)
        self.assertEqual(game.player.bank, 10)

    def test_check_results_finishes_game_and_credits_winner(self):
        game = self.make_game()
        game._player_hand = Deck(cards=[Card(10, "hearts"), Card(10, "clubs")])
        game._croupier_hand = Deck(cards=[Card(10, "spades"), Card(8, "diamonds")])
        game.state = GameState.DEALER_TURN

        outcome = game.check_results()
        self.profile.refresh_from_db()

        self.assertEqual(outcome.winner, GameResult.PLAYER)
        self.assertEqual(game.state, GameState.FINISHED)
        self.assertFalse(game.running)
        self.assertEqual(self.profile.jetons, 530)
        self.assertTrue(game.moves.filter(move=MoveLog.Move.RESULT).exists())

    def test_deleting_user_cascades_to_game_and_move_logs(self):
        game = self.make_game()

        self.user.delete()

        self.assertFalse(Game.objects.filter(id=game.id).exists())
        self.assertFalse(MoveLog.objects.filter(game_id=game.id).exists())


class GameViewSecurityTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="alice", password="Strong-pass-123!"
        )
        self.other_user = user_model.objects.create_user(
            username="bob", password="Strong-pass-456!"
        )
        self.client.force_login(self.user)

    def make_game(self):
        profile = self.user.profile
        game = Game.objects.create(profile=profile, player_bank=profile.jetons)
        game.new_game(bet=30)
        return game

    def test_game_routes_require_authentication(self):
        game = self.make_game()
        anonymous = Client()
        urls = [
            reverse("game_page"),
            reverse("launch_game"),
            reverse("launch_game_id", args=[game.id]),
            reverse("play_turn", args=[game.id, "hit"]),
            reverse("end_game", args=[game.id]),
        ]

        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(anonymous.get(url).status_code, 302)

    def test_launch_and_turn_actions_only_accept_post(self):
        game = self.make_game()

        self.assertEqual(self.client.get(reverse("launch_game")).status_code, 405)
        self.assertEqual(
            self.client.get(reverse("play_turn", args=[game.id, "hit"])).status_code,
            405,
        )

    def test_launch_rejects_invalid_bets(self):
        for invalid_bet in (-10, 0, self.user.profile.jetons + 1):
            with self.subTest(bet=invalid_bet):
                response = self.client.post(
                    reverse("launch_game"), {"bet": invalid_bet}
                )
                self.assertEqual(response.status_code, 400)

        self.assertEqual(Game.objects.count(), 0)

    def test_valid_launch_owns_game_and_updates_profile_bank(self):
        response = self.client.post(reverse("launch_game"), {"bet": 25})
        game = Game.objects.get()
        self.user.profile.refresh_from_db()

        self.assertRedirects(response, reverse("launch_game_id", args=[game.id]))
        self.assertEqual(game.profile, self.user.profile)
        self.assertEqual(self.user.profile.jetons, 975)

    def test_other_user_cannot_view_or_modify_game(self):
        game = self.make_game()
        self.client.force_login(self.other_user)

        self.assertEqual(
            self.client.get(reverse("launch_game_id", args=[game.id])).status_code,
            404,
        )
        self.assertEqual(
            self.client.post(reverse("play_turn", args=[game.id, "stop"])).status_code,
            404,
        )
        self.assertEqual(
            self.client.get(reverse("end_game", args=[game.id])).status_code,
            404,
        )

    def test_csrf_is_required_for_game_actions(self):
        game = self.make_game()
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.user)

        self.assertEqual(
            csrf_client.post(reverse("play_turn", args=[game.id, "hit"])).status_code,
            403,
        )

    def test_posted_hit_creates_a_move_and_redirects(self):
        game = self.make_game()

        response = self.client.post(reverse("play_turn", args=[game.id, "hit"]))

        self.assertEqual(response.status_code, 302)
        self.assertTrue(game.moves.filter(move=MoveLog.Move.HIT).exists())
