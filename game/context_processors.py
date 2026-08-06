from django.db.models import Case, Count, F, IntegerField, Sum, Value, When
from django.db.models.functions import Coalesce

from accounts.models import Profile

from .models import GameResult, GameState


def admin_dashboard(request):
    """Provide recent-player summaries only to the Django admin home page."""

    match = getattr(request, "resolver_match", None)
    if (
        not request.user.is_authenticated
        or not request.user.is_staff
        or match is None
        or match.namespace != "admin"
        or match.url_name != "index"
    ):
        return {}

    net_gain = Case(
        When(
            games__state=GameState.FINISHED,
            games__result=GameResult.PLAYER,
            then=F("games__pool"),
        ),
        When(
            games__state=GameState.FINISHED,
            games__result=GameResult.DEALER,
            then=-F("games__pool"),
        ),
        default=Value(0),
        output_field=IntegerField(),
    )
    players = (
        Profile.objects.select_related("user")
        .annotate(
            games_count=Count("games", distinct=True),
            total_gain=Coalesce(Sum(net_gain), Value(0)),
        )
        .order_by("-user__date_joined")[:12]
    )
    return {"admin_player_dashboard": players}
