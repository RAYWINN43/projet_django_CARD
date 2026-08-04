

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

class Deck() :

    def __init__(self, visible=True) :
        self.cards = []
        self.visible = visible

    def init_deck(self) :
        self.cards = []
        for suit in ["spades","clubs","hearts","diamonds"] :
            for value in range(13) :
                self.cards.append(Card(value+1, suit))

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
        index = randint(0,len(self.cards)-1)
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
    
    def __init__(self) :
        self.bank = 100

    def add_to_bank(self, amount) :
        self.bank += amount

class Game(models.Model) :

    def __init__(self) :
        self.player = Player() # Placeholder, à adapter
        self.pool = 0
        self.bet_value = 0
        self.draw_pile = Deck()
        self.draw_pile.init_deck()
        self.discard_pile = Deck()
        self.player_hand = Deck(visible=True)
        self.croupier_hand = Deck()
        self.running = True

    def new_game(self, bet) :
        self.pool = 0
        self.running = True
        self.discard_pile.add_many(self.player_hand.empty())
        self.discard_pile.add_many(self.croupier_hand.empty())
        self.setup(bet=bet)

    def reshuffle(self) :
        self.draw_pile.set_cards(self.discard_pile.empty())

    def player_draw(self) :
        self.player_hand.add(self.draw_pile.draw())
        if self.draw_pile.is_empty() :
            self.reshuffle()
    def croupier_draw(self) :
        self.croupier_hand.add(self.draw_pile.draw())
        if self.draw_pile.is_empty() :
            self.reshuffle()

    def setup(self, bet) :
        self.bet_value = bet
        self.pool += bet
        self.player.add_to_bank(-bet)
        for _ in range(2) :
            self.player_draw()
            self.croupier_draw()

    def display_game(self) :
        print(f"""
        {'Partie en cours :' if self.running else 'Partie terminée'}
        Pool : {self.pool} $
        Banque : {self.player.bank} $
        Joueur : {self.player_hand}
        Croupier : {self.croupier_hand}
        Défausse : {self.discard_pile}""")

    def hit(self) :
        self.player_draw()
        if self.player_hand.hand_value() > 21 :
            return True
        else :
            return False

    def stop(self) :
        return True

    def double(self) :
        self.player.add_to_bank(-self.bet_value)
        self.pool += self.bet_value
        self.player_draw()
        return True

    def check_results(self) :
        if self.running :
            self.running = False
            self.croupier_hand.set_visible()
            player_score = self.player_hand.hand_value()
            croupier_score = self.croupier_hand.hand_value()
            log = f"""
            Joueur : {player_score}
            Croupier : {croupier_score}"""
            if player_score < croupier_score or player_score > 21 :
                log += "\nLe croupier a gagné"
            elif player_score > croupier_score :
                log += "\nLe joueur a gagné"
                self.player.add_to_bank(2*self.pool)
            else :
                log += "\nÉgalité"
            self.player.add_to_bank(self.pool)
            return log


if __name__ == "__main__" :
    game = Game(player=Player())
    game.new_game(bet=30)
    game.display_game()
    game.hit()
    game.stop()
    game.display_game()