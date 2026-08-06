from django.shortcuts import render, redirect
from .models import Game


def game_page(request, game_id=None):
    game = Game.objects.filter(id=game_id).first() if game_id else None
    return render(request, "game.html", {"game": game})


def launch_game(request):
    bet_value_raw = request.GET.get("bet")

    try:
        bet_value = int(bet_value_raw)
    except (TypeError, ValueError):
        bet_value = 30

    profile = request.user.profile if request.user.is_authenticated else None
    game = Game.objects.create()
    game.new_game(bet=bet_value, profile=profile)
    return redirect("launch_game_id", game_id=game.id)


def play_game(request, game_id):
    game = Game.objects.get(id=game_id)
    return render(request, "game.html", {"game": game})


def play_turn(request, game_id, move):
    game = Game.objects.get(id=game_id)
    if request.user.is_authenticated:
        game.profile = request.user.profile
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
        return redirect("end_game", game_id=game.id)

    return render(request, "game.html", {"game": game})


def end_game(request, game_id):
    game = Game.objects.get(id=game_id)
    return render(request, "game.html", {"game": game})