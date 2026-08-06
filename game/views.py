from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.models import Profile

from .forms import BetForm
from .models import Game, GameRuleError


def game_context(game=None, bet_form=None):
    return {"game": game, "bet_form": bet_form}


@login_required
def game_page(request, game_id=None):
    if game_id is not None:
        game = get_object_or_404(Game, id=game_id, profile=request.user.profile)
        return render(request, "game.html", game_context(game=game))

    bet_form = BetForm(bank=request.user.profile.jetons, initial={"bet": 1})
    return render(request, "game.html", game_context(bet_form=bet_form))


@login_required
@require_POST
def launch_game(request):
    with transaction.atomic():
        profile = Profile.objects.select_for_update().get(user=request.user)
        bet_form = BetForm(request.POST, bank=profile.jetons)
        if not bet_form.is_valid():
            return render(
                request,
                "game.html",
                game_context(bet_form=bet_form),
                status=400,
            )

        game = Game.objects.create(profile=profile, player_bank=profile.jetons)
        game.new_game(bet=bet_form.cleaned_data["bet"])

    return redirect("launch_game_id", game_id=game.id)


@login_required
def play_game(request, game_id):
    game = get_object_or_404(Game, id=game_id, profile=request.user.profile)
    return render(request, "game.html", game_context(game=game))


@login_required
@require_POST
def play_turn(request, game_id, move):
    with transaction.atomic():
        game = get_object_or_404(
            Game.objects.select_for_update().select_related("profile"),
            id=game_id,
            profile=request.user.profile,
        )

        try:
            if move == "hit":
                done = game.hit()
            elif move == "double":
                done = game.double()
            elif move == "stop":
                done = game.stop()
            else:
                messages.error(request, "Ce coup n'existe pas.")
                return redirect("launch_game_id", game_id=game.id)

            if done:
                game.check_results()
                return redirect("end_game", game_id=game.id)
        except GameRuleError as error:
            messages.error(request, str(error))

    return redirect("launch_game_id", game_id=game.id)


@login_required
def end_game(request, game_id):
    game = get_object_or_404(Game, id=game_id, profile=request.user.profile)
    return render(request, "game.html", game_context(game=game))
