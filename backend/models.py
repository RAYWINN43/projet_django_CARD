from django.db import models
from random import randint

# Create your models here.

class Card(models.Model) :
    value = models.IntegerField
    suit = models.CharField(max_length=8)

    def __init__(self, value, suit) :
        self.value = value
        self.true_value = value if value <= 10 else 10
        self.suit = suit

    def display(self) :
        return f"{self.value}{self.suit[0].capitalize()}"

class Deck(models.Model) :
    visible = models.BooleanField

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

    def display(self) :
        to_display = ""
        for card in self.cards :
            to_display += card.display() if self.visible else "XX"
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

class Player(models.Model) :
    bank = models.IntegerField
    
    def __init__(self) :
        self.bank = 100

    def add_to_bank(self, amount) :
        self.bank += amount

class Game(models.Model) :
    pool = models.IntegerField
    bet_value = models.IntegerField
    running = models.BooleanField

    def __init__(self, player) :
        self.player = player
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
        Joueur : {self.player_hand.display()}
        Croupier : {self.croupier_hand.display()}
        Défausse : {self.discard_pile.display()}""")

    def hit(self) :
        self.player_draw()
        if self.player_hand.hand_value() > 21 :
            self.check_results()

    def stop(self) :
        self.check_results()

    def double(self) :
        self.player.add_to_bank(-self.bet_value)
        self.pool += self.bet_value
        self.player_draw()
        self.check_results()

    def check_results(self) :
        if self.running :
            self.running = False
            self.croupier_hand.set_visible()
            player_score = self.player_hand.hand_value()
            croupier_score = self.croupier_hand.hand_value()
            print(f"""
            Joueur : {player_score}
            Croupier : {croupier_score}""")
            if player_score < croupier_score or player_score > 21 :
                print("Le croupier a gagné")
            elif player_score > croupier_score :
                print("Le joueur a gagné")
                self.player.add_to_bank(2*self.pool)
            else :
                print("Égalité")
            self.player.add_to_bank(self.pool)


if __name__ == "__main__" :
    game = Game(player=Player())
    game.new_game(bet=30)
    game.display_game()
    game.hit()
    game.stop()
    game.display_game()