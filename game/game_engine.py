"""Pure Blackjack rules, independent from Django and HTTP concerns."""

from dataclasses import dataclass
from random import shuffle


class GameRuleError(ValueError):
    """Raised when a requested move violates a Blackjack rule."""


class Card:
    def __init__(self, value, suit):
        self.value = value
        self.true_value = min(value, 10)
        self.suit = suit

    def __str__(self):
        return f"{self.value}{self.suit[0].capitalize()}"

    def to_dict(self):
        return {
            "value": self.value,
            "suit": self.suit,
            "true_value": self.true_value,
        }

    @classmethod
    def from_dict(cls, payload):
        return cls(payload["value"], payload["suit"])


class Deck:
    suits = ("spades", "clubs", "hearts", "diamonds")

    def __init__(self, visible=True, visible_first=False, cards=None):
        self.cards = list(cards or [])
        self.visible = visible
        self.visible_first = visible_first

    def init_deck(self):
        self.cards = [
            Card(value, suit) for suit in self.suits for value in range(1, 14)
        ]
        self.shuffle()

    def shuffle(self):
        shuffle(self.cards)

    def to_dict(self):
        return {
            "visible": self.visible,
            "visible_first": self.visible_first,
            "cards": [card.to_dict() for card in self.cards],
        }

    @classmethod
    def from_dict(cls, payload):
        visible = payload.get("visible", True) if isinstance(payload, dict) else True
        visible_first = (
            payload.get("visible_first", False) if isinstance(payload, dict) else False
        )
        cards = payload.get("cards", []) if isinstance(payload, dict) else payload or []
        return cls(
            visible=visible,
            visible_first=visible_first,
            cards=[Card.from_dict(card) for card in cards],
        )

    def set_cards(self, cards):
        self.cards = list(cards)

    def set_visible(self, visibility=True):
        self.visible = visibility

    def is_empty(self):
        return not self.cards

    def empty(self):
        cards = self.cards
        self.cards = []
        return cards

    def draw(self):
        if self.is_empty():
            raise GameRuleError("La pioche est vide.")
        return self.cards.pop()

    def add(self, card):
        self.cards.append(card)

    def add_many(self, cards):
        self.cards.extend(cards)

    def __str__(self):
        cards = (
            str(card) if self.visible or (self.visible_first and index == 0) else "XX"
            for index, card in enumerate(self.cards)
        )
        return ", ".join(cards)

    def hand_value(self):
        value = sum(card.true_value for card in self.cards)
        aces = sum(card.true_value == 1 for card in self.cards)

        while aces > 0 and value <= 11:
            value += 10
            aces -= 1
        return value


class Player:
    def __init__(self, bank=100):
        self.bank = bank

    def add_to_bank(self, amount):
        self.bank += amount

    def debit(self, amount):
        if amount <= 0:
            raise GameRuleError("La mise doit être strictement positive.")
        if amount > self.bank:
            raise GameRuleError("Le solde est insuffisant pour cette mise.")
        self.bank -= amount

    def get_bank(self):
        return self.bank


@dataclass(frozen=True)
class RoundResult:
    winner: str
    player_score: int
    dealer_score: int


def evaluate_round(player_score, dealer_score):
    if player_score > 21 or (player_score < dealer_score <= 21):
        winner = "dealer"
    elif dealer_score > 21 or player_score > dealer_score:
        winner = "player"
    else:
        winner = "draw"
    return RoundResult(winner, player_score, dealer_score)
