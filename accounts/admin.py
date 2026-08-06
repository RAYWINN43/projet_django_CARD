from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.db.models import Case, Count, F, IntegerField, Sum, Value, When
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import path
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_GET

from game.models import GameResult, GameState

from .models import Profile


def net_gain_expression(prefix="games__"):
    return Case(
        When(
            **{
                f"{prefix}state": GameState.FINISHED,
                f"{prefix}result": GameResult.PLAYER,
                "then": F(f"{prefix}pool"),
            }
        ),
        When(
            **{
                f"{prefix}state": GameState.FINISHED,
                f"{prefix}result": GameResult.DEALER,
                "then": -F(f"{prefix}pool"),
            }
        ),
        default=Value(0),
        output_field=IntegerField(),
    )


def cards_from_payload(payload):
    if isinstance(payload, dict):
        cards = payload.get("cards", [])
    else:
        cards = payload or []
    return [
        {"value": card.get("value"), "suit": card.get("suit", "")}
        for card in cards
        if isinstance(card, dict)
    ]


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    extra = 0
    fields = ("jetons",)
    verbose_name_plural = "Profil joueur"


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "jetons", "games_count_display", "total_gain_display")
    search_fields = ("user__username", "user__email")

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("user")
            .annotate(
                admin_games_count=Count("games", distinct=True),
                admin_total_gain=Coalesce(
                    Sum(net_gain_expression()),
                    Value(0),
                ),
            )
        )

    def get_urls(self):
        custom_urls = [
            path(
                "<int:profile_id>/history/",
                self.admin_site.admin_view(self.player_history),
                name="accounts_profile_history",
            )
        ]
        return custom_urls + super().get_urls()

    @admin.display(description="PARTIES", ordering="admin_games_count")
    def games_count_display(self, obj):
        return obj.admin_games_count

    @admin.display(description="GAINS NETS", ordering="admin_total_gain")
    def total_gain_display(self, obj):
        value = obj.admin_total_gain
        return f"{value:+d} jetons" if value else "0 jeton"

    @method_decorator(require_GET)
    def player_history(self, request, profile_id):
        profile = get_object_or_404(
            Profile.objects.select_related("user"),
            id=profile_id,
        )
        games = list(
            profile.games.prefetch_related("moves", "decks__cards").order_by(
                "-created_at"
            )[:30]
        )
        total_gain = 0
        game_history = []

        for game in games:
            if game.state == GameState.FINISHED and game.result == GameResult.PLAYER:
                net_gain = game.pool
            elif game.state == GameState.FINISHED and game.result == GameResult.DEALER:
                net_gain = -game.pool
            else:
                net_gain = 0
            total_gain += net_gain

            game_history.append(
                {
                    "id": game.id,
                    "created_at": timezone.localtime(game.created_at).isoformat(),
                    "state": game.state,
                    "state_label": game.get_state_display(),
                    "result": game.result,
                    "result_label": (
                        game.get_result_display() if game.result else "En cours"
                    ),
                    "starting_bet": game.bet_value,
                    "current_bet": game.pool,
                    "net_gain": net_gain,
                    "player_cards": cards_from_payload(game.player_hand),
                    "dealer_cards": cards_from_payload(game.croupier_hand),
                    "moves": [
                        {
                            "move": move.get_move_display(),
                            "actor": move.get_actor_display(),
                            "card": move.card,
                            "created_at": timezone.localtime(
                                move.created_at
                            ).isoformat(),
                        }
                        for move in game.moves.all()
                    ],
                }
            )

        return JsonResponse(
            {
                "player": {
                    "username": profile.user.username,
                    "email": profile.user.email,
                    "bank": profile.jetons,
                    "total_gain": total_gain,
                },
                "games": game_history,
            },
            json_dumps_params={"ensure_ascii": False},
        )


User = get_user_model()
admin.site.unregister(User)


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    inlines = (ProfileInline,)
    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "is_staff",
        "jetons",
    )

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related("profile")

    @admin.display(description="JETON")
    def jetons(self, obj):
        try:
            return obj.profile.jetons
        except Profile.DoesNotExist:
            return 0
