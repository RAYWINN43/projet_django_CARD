

from django.db import models
from random import randint

# Create your models here.

class Card() :

    def __init__(self, value, suit) :
        self.value = value
        self.true_value = value if value <= 10 else 10
        self.suit = suit

    def __str__(self) :
        return f"{self.value}{self.suit[0].capitalize()}"

    def to_dict(self) :
        return {
            "value": self.value,
            "suit": self.suit,
            "true_value": self.true_value,
        }

    @classmethod
    def from_dict(cls, payload) :
        return cls(payload["value"], payload["suit"])


class Deck() :

    def __init__(self, visible=True, cards=None) :
        self.cards = cards or []
        self.visible = visible

    def init_deck(self) :
        self.cards = []
        for suit in ["spades", "clubs", "hearts", "diamonds"] :
            for value in range(13) :
                self.cards.append(Card(value + 1, suit))

    def to_dict(self) :
        return {
            "visible": self.visible,
            "cards": [card.to_dict() for card in self.cards],
        }

    @classmethod
    def from_dict(cls, payload) :
        visible = payload.get("visible", True) if isinstance(payload, dict) else True
        cards = payload.get("cards", []) if isinstance(payload, dict) else payload or []
        deck = cls(visible=visible)
        deck.cards = [Card.from_dict(card) for card in cards]
        return deck

    def set_cards(self, cards) :
        self.cards = cards

    def set_visible(self, visibility=True) :
        self.visible = visibility

    def is_empty(self) :
        return True if len(self.cards) == 0 else False

    def empty(self) :
        cards = self.cards
        self.set_cards([])
        return cards

    def draw(self) :
        index = randint(0, len(self.cards) - 1)
        card = self.cards[index]
        self.cards.pop(index)
        return card

    def add(self, card) :
        self.cards.append(card)

    def add_many(self, cards) :
        self.cards += cards

    def __str__(self) :
        to_display = ""
        for card in self.cards :
            to_display += str(card) if self.visible else "XX"
            to_display += ", "
        return to_display[:-2]

    def hand_value(self) :
        value = 0
        aces = 0
        for card in self.cards :
            value += card.true_value
            if value == 1 :
                aces += 1
        while aces > 0 and value <= 11 :
            value += 10
            aces -= 1
        return value


class Player() :

    def __init__(self, bank=100) :
        self.bank = bank

    def add_to_bank(self, amount) :
        self.bank += amount


class Game(models.Model) :
    player_bank = models.IntegerField(default=100)
    pool = models.IntegerField(default=0)
    bet_value = models.IntegerField(default=0)
    draw_pile = models.JSONField(default=list, blank=True)
    discard_pile = models.JSONField(default=list, blank=True)
    player_hand = models.JSONField(default=list, blank=True)
    croupier_hand = models.JSONField(default=list, blank=True)
    running = models.BooleanField(default=True)

    def __init__(self, *args, **kwargs) :
        super().__init__(*args, **kwargs)
        self.player = Player(bank=self.player_bank)
        self._draw_pile = Deck.from_dict(self.draw_pile)
        self._discard_pile = Deck.from_dict(self.discard_pile)
        self._player_hand = Deck.from_dict(self.player_hand)
        self._croupier_hand = Deck.from_dict(self.croupier_hand)
        self._running = self.running

    def save(self, *args, **kwargs) :
        self.running = self._running
        self.player_bank = self.player.bank
        self.draw_pile = self._draw_pile.to_dict()
        self.discard_pile = self._discard_pile.to_dict()
        self.player_hand = self._player_hand.to_dict()
        self.croupier_hand = self._croupier_hand.to_dict()
        super().save(*args, **kwargs)

    def new_game(self, bet) :
        print("Nouvelle partie")
        self.player = Player(bank=self.player_bank)
        self._draw_pile = Deck(visible=True)
        self._draw_pile.init_deck()
        self._discard_pile = Deck(visible=False)
        self._player_hand = Deck(visible=True)
        self._croupier_hand = Deck(visible=False)
        self.pool = 0
        self.bet_value = 0
        self._running = True
        self.setup(bet=bet)
        self.save()

    def reshuffle(self) :
        self._draw_pile.set_cards(self._discard_pile.empty())

    def player_draw(self) :
        self._player_hand.add(self._draw_pile.draw())
        if self._draw_pile.is_empty() :
            self.reshuffle()

    def croupier_draw(self) :
        self._croupier_hand.add(self._draw_pile.draw())
        if self._draw_pile.is_empty() :
            self.reshuffle()

    def setup(self, bet) :
        self.bet_value = bet
        self.pool += bet
        self.player.add_to_bank(-bet)
        for _ in range(2) :
            self.player_draw()
            self.croupier_draw()
        self.display_game()

    def display_game(self) :
        print(f"""
        {'Partie en cours :' if self.running else 'Partie terminée'}
        Pool : {self.pool} $
        Banque : {self.player.bank} $
        Joueur : {self._player_hand}
        Croupier : {self._croupier_hand}
        Défausse : {self._discard_pile}""")

    def hit(self) :
        if self._running :
            print("Piocher")
            self.player_draw()
            self.save()
            if self._player_hand.hand_value() > 21 :
                return True
            else :
                return False

    def stop(self) :
        if self._running :
            print("Rester")
            self.save()
            return True

    def double(self) :
        if self._running :
            print("Doubler")
            self.player.add_to_bank(-self.bet_value)
            self.pool += self.bet_value
            self.player_draw()
            self.save()
            return True

    def check_results(self) :
        if self._running :
            print("Fin de la partie")
            self.running = False
            self._running = False
            self._croupier_hand.set_visible()
            player_score = self._player_hand.hand_value()
            croupier_score = self._croupier_hand.hand_value()
            self.display_game()
            log = f"""
            Joueur : {player_score}
            Croupier : {croupier_score}"""
            if player_score < croupier_score or player_score > 21 :
                log += "\nLe croupier a gagné"
            elif player_score > croupier_score :
                log += "\nLe joueur a gagné"
                self.player.add_to_bank(2 * self.pool)
            else :
                log += "\nÉgalité"
            self.player.add_to_bank(self.pool)
            self.save()
            return log


if __name__ == "__main__" :
    game = Game(player=Player())
    game.new_game(bet=30)
    game.display_game()
    game.hit()
    game.stop()
    game.display_game()