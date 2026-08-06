from typing import ClassVar

from django.db import models
from django.db.models import Max
from django.utils import timezone

from . import game_engine

GameRuleError = game_engine.GameRuleError
Player = game_engine.Player
evaluate_round = game_engine.evaluate_round


class GameState(models.TextChoices):
    WAITING = "waiting", "En attente"
    PLAYER_TURN = "player_turn", "Tour du joueur"
    DEALER_TURN = "dealer_turn", "Tour du croupier"
    FINISHED = "finished", "Terminée"


class GameResult(models.TextChoices):
    PLAYER = "player", "Victoire du joueur"
    DEALER = "dealer", "Victoire du croupier"
    DRAW = "draw", "Égalité"


class Game(models.Model):
    profile = models.ForeignKey(
        "accounts.Profile",
        on_delete=models.CASCADE,
        related_name="games",
        null=True,
        blank=True,
    )
    state = models.CharField(
        max_length=20,
        choices=GameState.choices,
        default=GameState.WAITING,
        db_index=True,
    )
    result = models.CharField(
        max_length=10,
        choices=GameResult.choices,
        blank=True,
        default="",
    )
    player_bank = models.IntegerField(default=100)
    pool = models.PositiveIntegerField(default=0)
    bet_value = models.PositiveIntegerField(default=0)
    running = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["profile", "-created_at"])
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # QuerySets used by Django's deletion collector may defer most fields.
        # Reading a deferred descriptor here would recursively refresh the model.
        self.player = Player(bank=self.__dict__.get("player_bank", 100))
        self._running = self.__dict__.get("running", False)

    def save(self, *args, **kwargs):
        self.running = self._running
        self.player_bank = self.player.bank

        update_fields = kwargs.get("update_fields")
        if update_fields is not None:
            kwargs["update_fields"] = set(update_fields) | {
                "running",
                "player_bank",
                "updated_at",
            }

        super().save(*args, **kwargs)

        if self.profile_id and self.profile.jetons != self.player.bank:
            self.profile.jetons = self.player.bank
            self.profile.save(update_fields=["jetons"])

    def deck_for(self, zone):
        if not self.pk:
            raise GameRuleError(
                "La partie doit être enregistrée avant de créer un paquet."
            )
        prefetched_decks = getattr(self, "_prefetched_objects_cache", {}).get("decks")
        if prefetched_decks is not None:
            for deck in prefetched_decks:
                if deck.zone == zone:
                    return deck
            raise Deck.DoesNotExist
        return self.decks.get(zone=zone)

    @property
    def draw_deck(self):
        return self.deck_for(Deck.Zone.DRAW)

    @property
    def discard_deck(self):
        return self.deck_for(Deck.Zone.DISCARD)

    @property
    def player_deck(self):
        return self.deck_for(Deck.Zone.PLAYER_HAND)

    @property
    def croupier_deck(self):
        return self.deck_for(Deck.Zone.DEALER_HAND)

    def deck_payload(self, zone, *, visible, visible_first=False):
        try:
            return self.deck_for(zone).to_dict()
        except (Deck.DoesNotExist, GameRuleError):
            return {
                "visible": visible,
                "visible_first": visible_first,
                "cards": [],
            }

    # Compatibility properties used by templates and the administration API.
    @property
    def draw_pile(self):
        return self.deck_payload(Deck.Zone.DRAW, visible=True)

    @property
    def discard_pile(self):
        return self.deck_payload(Deck.Zone.DISCARD, visible=False)

    @property
    def player_hand(self):
        return self.deck_payload(Deck.Zone.PLAYER_HAND, visible=True)

    @property
    def croupier_hand(self):
        return self.deck_payload(
            Deck.Zone.DEALER_HAND,
            visible=False,
            visible_first=True,
        )

    def initialize_decks(self):
        self.decks.all().delete()
        draw_deck = Deck.objects.create(
            game=self,
            zone=Deck.Zone.DRAW,
            visible=True,
        )
        Deck.objects.create(
            game=self,
            zone=Deck.Zone.DISCARD,
            visible=False,
        )
        Deck.objects.create(
            game=self,
            zone=Deck.Zone.PLAYER_HAND,
            visible=True,
        )
        Deck.objects.create(
            game=self,
            zone=Deck.Zone.DEALER_HAND,
            visible=False,
            visible_first=True,
        )
        draw_deck.init_deck()

    def record_move(self, move, actor, card=None, details=None):
        if not self.pk:
            return None
        return MoveLog.objects.create(
            game=self,
            move=move,
            actor=actor,
            card=card.to_dict() if card else None,
            details=details or {},
        )

    def new_game(self, bet, profile=None):
        if profile is not None:
            self.profile = profile

        try:
            bet = int(bet)
        except (TypeError, ValueError) as error:
            raise GameRuleError("La mise doit être un nombre entier.") from error

        starting_bank = self.profile.jetons if self.profile_id else self.player_bank
        self.player = Player(bank=starting_bank)
        self.player.debit(bet)
        self.pool = bet
        self.bet_value = bet
        self.result = ""
        self.state = GameState.PLAYER_TURN
        self._running = True
        self.save()

        self.initialize_decks()
        for _ in range(2):
            self.player_draw()
            self.croupier_draw()

        self.record_move(
            MoveLog.Move.DEAL,
            MoveLog.Actor.SYSTEM,
            details={
                "bet": self.bet_value,
                "player_cards": self.player_hand["cards"],
                "dealer_cards": self.croupier_hand["cards"],
            },
        )

    def reshuffle(self):
        cards = self.discard_deck.empty()
        if not cards:
            raise GameRuleError(
                "Aucune carte n'est disponible pour reformer la pioche."
            )
        self.draw_deck.set_cards(cards)
        self.draw_deck.shuffle()

    def draw_for(self, hand):
        if self.draw_deck.is_empty():
            self.reshuffle()
        card_drawn = self.draw_deck.draw()
        return hand.add(card_drawn)

    def player_draw(self):
        return self.draw_for(self.player_deck)

    def croupier_draw(self):
        return self.draw_for(self.croupier_deck)

    def display_game(self):
        return {
            "running": self.running,
            "pool": self.pool,
            "bank": self.player.bank,
            "player": str(self.player_deck),
            "dealer": str(self.croupier_deck),
        }

    def require_player_turn(self):
        if not self._running or self.state != GameState.PLAYER_TURN:
            raise GameRuleError(
                "Cette action n'est pas autorisée à ce stade de la partie."
            )

    def hit(self):
        self.require_player_turn()
        card_drawn = self.player_draw()
        is_bust = self.player_deck.hand_value() > 21
        if is_bust:
            self.state = GameState.DEALER_TURN
        self.save()
        self.record_move(MoveLog.Move.HIT, MoveLog.Actor.PLAYER, card=card_drawn)
        return is_bust

    def stop(self):
        self.require_player_turn()
        self.state = GameState.DEALER_TURN
        self.save()
        self.record_move(MoveLog.Move.STAND, MoveLog.Actor.PLAYER)
        return True

    def double(self):
        self.require_player_turn()
        self.player.debit(self.bet_value)
        self.pool += self.bet_value
        card_drawn = self.player_draw()
        self.state = GameState.DEALER_TURN
        self.save()
        self.record_move(
            MoveLog.Move.DOUBLE,
            MoveLog.Actor.PLAYER,
            card=card_drawn,
            details={"current_bet": self.pool},
        )
        return True

    def check_results(self):
        if not self._running:
            raise GameRuleError("Cette partie est déjà terminée.")

        self.state = GameState.DEALER_TURN
        self.croupier_deck.set_visible()
        dealer_cards = []
        while self.croupier_deck.hand_value() < 17:
            card_drawn = self.croupier_draw()
            dealer_cards.append(card_drawn.to_dict())

        outcome = evaluate_round(
            self.player_deck.hand_value(), self.croupier_deck.hand_value()
        )
        self.result = outcome.winner
        if outcome.winner == GameResult.PLAYER:
            self.player.add_to_bank(2 * self.pool)
        elif outcome.winner == GameResult.DRAW:
            self.player.add_to_bank(self.pool)

        self.state = GameState.FINISHED
        self._running = False
        self.save()
        self.record_move(
            MoveLog.Move.RESULT,
            MoveLog.Actor.SYSTEM,
            details={
                "winner": outcome.winner,
                "player_score": outcome.player_score,
                "dealer_score": outcome.dealer_score,
                "dealer_cards_drawn": dealer_cards,
                "final_bank": self.player.bank,
            },
        )
        return outcome


class Deck(models.Model):
    class Zone(models.TextChoices):
        DRAW = "draw", "Pioche"
        DISCARD = "discard", "Défausse"
        PLAYER_HAND = "player_hand", "Main du joueur"
        DEALER_HAND = "dealer_hand", "Main du croupier"

    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name="decks")
    zone = models.CharField(max_length=20, choices=Zone.choices)
    visible = models.BooleanField(default=True)
    visible_first = models.BooleanField(default=False)

    class Meta:
        ordering: ClassVar[list[str]] = ["game_id", "zone"]
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                fields=["game", "zone"],
                name="unique_deck_zone_per_game",
            )
        ]

    def __str__(self):
        cards = (
            str(card) if self.visible or (self.visible_first and index == 0) else "XX"
            for index, card in enumerate(self.cards.all())
        )
        return ", ".join(cards)

    def to_dict(self):
        return {
            "visible": self.visible,
            "visible_first": self.visible_first,
            "cards": [card.to_dict() for card in self.cards.all()],
        }

    def init_deck(self):
        rule_deck = game_engine.Deck(
            visible=self.visible,
            visible_first=self.visible_first,
        )
        rule_deck.init_deck()
        self.replace_cards(rule_deck.cards)

    def replace_cards(self, cards):
        self.cards.all().delete()
        persisted_cards = []
        for position, card in enumerate(cards):
            payload = card if isinstance(card, dict) else card.to_dict()
            persisted_cards.append(
                Card(
                    deck=self,
                    value=payload["value"],
                    suit=payload["suit"],
                    position=position,
                )
            )
        Card.objects.bulk_create(persisted_cards)

    def shuffle(self):
        cards = list(self.cards.all())
        rule_deck = game_engine.Deck(
            cards=[game_engine.Card(card.value, card.suit) for card in cards]
        )
        rule_deck.shuffle()
        positions = {
            (card.suit, card.value): position
            for position, card in enumerate(rule_deck.cards)
        }
        for card in cards:
            card.position = positions[(card.suit, card.value)]
        Card.objects.bulk_update(cards, ["position"])

    def set_cards(self, cards):
        cards = list(cards)
        kept_ids = [card.pk for card in cards if card.pk]
        self.cards.exclude(pk__in=kept_ids).delete()
        for position, card in enumerate(cards):
            card.deck = self
            card.position = position
        Card.objects.bulk_update(cards, ["deck", "position"])

    def set_visible(self, visibility=True):
        self.visible = visibility
        self.save(update_fields=["visible"])

    def is_empty(self):
        return not self.cards.exists()

    def empty(self):
        return list(self.cards.all())

    def draw(self):
        card = self.cards.order_by("-position", "-id").first()
        if card is None:
            raise GameRuleError("La pioche est vide.")
        return card

    def add(self, card):
        last_position = self.cards.aggregate(Max("position"))["position__max"]
        next_position = 0 if last_position is None else last_position + 1
        if isinstance(card, Card):
            card.deck = self
            card.position = next_position
            card.save(update_fields=["deck", "position"])
            return card
        payload = card if isinstance(card, dict) else card.to_dict()
        return Card.objects.create(
            deck=self,
            value=payload["value"],
            suit=payload["suit"],
            position=next_position,
        )

    def add_many(self, cards):
        return [self.add(card) for card in cards]

    def hand_value(self):
        rule_hand = game_engine.Deck(
            cards=[game_engine.Card(card.value, card.suit) for card in self.cards.all()]
        )
        return rule_hand.hand_value()


class Card(models.Model):
    class Suit(models.TextChoices):
        SPADES = "spades", "Piques"
        CLUBS = "clubs", "Trèfles"
        HEARTS = "hearts", "Cœurs"
        DIAMONDS = "diamonds", "Carreaux"

    deck = models.ForeignKey(Deck, on_delete=models.CASCADE, related_name="cards")
    value = models.PositiveSmallIntegerField()
    suit = models.CharField(max_length=8, choices=Suit.choices)
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering: ClassVar[list[str]] = ["position", "id"]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["deck", "position"])
        ]
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.CheckConstraint(
                condition=models.Q(value__gte=1, value__lte=13),
                name="card_value_between_1_and_13",
            )
        ]

    @property
    def true_value(self):
        return min(self.value, 10)

    def __str__(self):
        return f"{self.value}{self.suit[0].capitalize()}"

    def to_dict(self):
        return {
            "value": self.value,
            "suit": self.suit,
            "true_value": self.true_value,
        }


class MoveLog(models.Model):
    class Move(models.TextChoices):
        DEAL = "deal", "Distribution"
        HIT = "hit", "Pioche"
        STAND = "stand", "Stop"
        DOUBLE = "double", "Double"
        RESULT = "result", "Résultat"

    class Actor(models.TextChoices):
        PLAYER = "player", "Joueur"
        DEALER = "dealer", "Croupier"
        SYSTEM = "system", "Système"

    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name="moves")
    move = models.CharField(max_length=12, choices=Move.choices)
    actor = models.CharField(max_length=10, choices=Actor.choices)
    card = models.JSONField(null=True, blank=True)
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering: ClassVar[list[str]] = ["created_at", "id"]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["game", "created_at"])
        ]

    def __str__(self):
        return f"Partie {self.game_id} · {self.get_move_display()}"


__all__ = [
    "Card",
    "Deck",
    "Game",
    "GameResult",
    "GameRuleError",
    "GameState",
    "MoveLog",
    "Player",
]
