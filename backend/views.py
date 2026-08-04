from django.http import HttpResponse
from django.shortcuts import render, redirect
from models import Game

def play_game() :
    game = Game.objects.create()
    return redirect("game", game_id = game.id)

def play_turn(game_id, move) :
    game = Game.objects.get(id = game_id)
    match move :
        case "hit" :
            done = game.hit()
        case "double" :
            done = game.double()    
        case "stop" :
            done = game.stop()
    if done :
        log = game.check_results()
        print(log)
    return redirect("game", game_id = game.id)