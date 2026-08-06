from typing import ClassVar

from django.db import models
from django.utils import timezone

from .game_engine import Card, Deck, GameRuleError, Player, evaluate_round


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
    draw_pile = models.JSONField(default=list, blank=True)
    discard_pile = models.JSONField(default=list, blank=True)
    player_hand = models.JSONField(default=list, blank=True)
    croupier_hand = models.JSONField(default=list, blank=True)
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
        self._draw_pile = Deck.from_dict(self.__dict__.get("draw_pile", []))
        self._discard_pile = Deck.from_dict(self.__dict__.get("discard_pile", []))
        self._player_hand = Deck.from_dict(self.__dict__.get("player_hand", []))
        self._croupier_hand = Deck.from_dict(self.__dict__.get("croupier_hand", []))
        self._running = self.__dict__.get("running", False)

    def save(self, *args, **kwargs):
        self.running = self._running
        self.player_bank = self.player.bank
        self.draw_pile = self._draw_pile.to_dict()
        self.discard_pile = self._discard_pile.to_dict()
        self.player_hand = self._player_hand.to_dict()
        self.croupier_hand = self._croupier_hand.to_dict()

        update_fields = kwargs.get("update_fields")
        if update_fields is not None:
            kwargs["update_fields"] = set(update_fields) | {
                "running",
                "player_bank",
                "draw_pile",
                "discard_pile",
                "player_hand",
                "croupier_hand",
                "updated_at",
            }

        super().save(*args, **kwargs)

        if self.profile_id and self.profile.jetons != self.player.bank:
            self.profile.jetons = self.player.bank
            self.profile.save(update_fields=["jetons"])

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
        starting_bank = self.profile.jetons if self.profile_id else self.player_bank
        self.player = Player(bank=starting_bank)
        self._draw_pile = Deck(visible=True)
        self._draw_pile.init_deck()
        self._discard_pile = Deck(visible=False)
        self._player_hand = Deck(visible=True)
        self._croupier_hand = Deck(visible=False, visible_first=True)
        self.pool = 0
        self.bet_value = 0
        self.result = ""
        self.state = GameState.PLAYER_TURN
        self._running = True
        self.setup(bet=bet)
        self.save()
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
        cards = self._discard_pile.empty()
        if not cards:
            raise GameRuleError(
                "Aucune carte n'est disponible pour reformer la pioche."
            )
        self._draw_pile.set_cards(cards)
        self._draw_pile.shuffle()

    def draw_for(self, hand):
        if self._draw_pile.is_empty():
            self.reshuffle()
        card_drawn = self._draw_pile.draw()
        hand.add(card_drawn)
        return card_drawn

    def player_draw(self):
        return self.draw_for(self._player_hand)

    def croupier_draw(self):
        return self.draw_for(self._croupier_hand)

    def setup(self, bet):
        try:
            bet = int(bet)
        except (TypeError, ValueError) as error:
            raise GameRuleError("La mise doit être un nombre entier.") from error

        self.player.debit(bet)
        self.bet_value = bet
        self.pool = bet
        for _ in range(2):
            self.player_draw()
            self.croupier_draw()

    def display_game(self):
        return {
            "running": self.running,
            "pool": self.pool,
            "bank": self.player.bank,
            "player": str(self._player_hand),
            "dealer": str(self._croupier_hand),
        }

    def require_player_turn(self):
        if not self._running or self.state != GameState.PLAYER_TURN:
            raise GameRuleError(
                "Cette action n'est pas autorisée à ce stade de la partie."
            )

    def hit(self):
        self.require_player_turn()
        card_drawn = self.player_draw()
        is_bust = self._player_hand.hand_value() > 21
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
        self._croupier_hand.set_visible()
        dealer_cards = []
        while self._croupier_hand.hand_value() < 17:
            card_drawn = self.croupier_draw()
            dealer_cards.append(card_drawn.to_dict())

        outcome = evaluate_round(
            self._player_hand.hand_value(), self._croupier_hand.hand_value()
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
