from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class CardDeckMigrationTests(TransactionTestCase):
    migrate_from = (
        "game",
        "0003_movelog_game_created_at_game_profile_game_result_and_more",
    )
    migrate_to = (
        "game",
        "0004_remove_game_croupier_hand_remove_game_discard_pile_and_more",
    )

    def test_json_cards_are_migrated_to_ordered_orm_models(self):
        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_from])
        old_apps = executor.loader.project_state([self.migrate_from]).apps
        OldGame = old_apps.get_model("game", "Game")

        old_game = OldGame.objects.create(
            draw_pile={
                "visible": True,
                "visible_first": False,
                "cards": [
                    {"value": 2, "suit": "clubs", "true_value": 2},
                    {"value": 13, "suit": "spades", "true_value": 10},
                ],
            },
            discard_pile=[],
            player_hand={
                "visible": True,
                "cards": [{"value": 1, "suit": "hearts", "true_value": 1}],
            },
            croupier_hand={
                "visible": False,
                "visible_first": True,
                "cards": [{"value": 8, "suit": "diamonds", "true_value": 8}],
            },
        )

        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_to])
        new_apps = executor.loader.project_state([self.migrate_to]).apps
        Deck = new_apps.get_model("game", "Deck")

        decks = Deck.objects.filter(game_id=old_game.pk)
        self.assertEqual(decks.count(), 4)

        draw_deck = decks.get(zone="draw")
        self.assertTrue(draw_deck.visible)
        self.assertEqual(
            list(draw_deck.cards.order_by("position").values_list("value", "suit")),
            [(2, "clubs"), (13, "spades")],
        )

        dealer_deck = decks.get(zone="dealer_hand")
        self.assertFalse(dealer_deck.visible)
        self.assertTrue(dealer_deck.visible_first)
