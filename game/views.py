from django.shortcuts import render, redirect
from .models import Game


def game_page(request, game_id=None):
    game = Game.objects.filter(id=game_id).first() if game_id else None
    return render(request, "game.html", {"game": game})


def launch_game(request):
    game = Game.objects.create()
    game.new_game(bet=30)
    return render(request, "game.html", {"game": game})


def play_game(request, game_id):
    game = Game.objects.get(id=game_id)
    game.new_game(bet=30)
    return render(request, "game.html", {"game": game})


def play_turn(request, game_id, move):
    game = Game.objects.get(id=game_id)
    match move:
        case "hit":
            done = game.hit()
        case "double":
            done = game.double()
        case "stop":
            done = game.stop()
        case _:
            done = False

    if done:
        log = game.check_results()
        print(log)

    return render(request, "game.html", {"game": game})

