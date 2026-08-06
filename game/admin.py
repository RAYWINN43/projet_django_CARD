from django.contrib import admin

from .models import Card, Deck, Game, MoveLog


class MoveLogInline(admin.TabularInline):
    model = MoveLog
    extra = 0
    readonly_fields = ("move", "actor", "card", "details", "created_at")
    can_delete = False


class DeckInline(admin.TabularInline):
    model = Deck
    extra = 0
    fields = ("zone", "visible", "visible_first", "cards_count")
    readonly_fields = ("cards_count",)
    can_delete = False

    @admin.display(description="Cartes")
    def cards_count(self, obj):
        return obj.cards.count() if obj.pk else 0


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "profile",
        "state",
        "result",
        "bet_value",
        "player_bank",
        "created_at",
    )
    list_filter = ("state", "result", "created_at")
    search_fields = ("profile__user__username",)
    readonly_fields = ("created_at", "updated_at")
    inlines = (DeckInline, MoveLogInline)


@admin.register(Deck)
class DeckAdmin(admin.ModelAdmin):
    list_display = ("game", "zone", "cards_count", "visible", "visible_first")
    list_filter = ("zone", "visible")
    search_fields = ("game__profile__user__username",)

    @admin.display(description="Cartes")
    def cards_count(self, obj):
        return obj.cards.count()


@admin.register(Card)
class CardAdmin(admin.ModelAdmin):
    list_display = ("id", "deck", "value", "suit", "position")
    list_filter = ("suit", "deck__zone")
    search_fields = ("deck__game__profile__user__username",)


@admin.register(MoveLog)
class MoveLogAdmin(admin.ModelAdmin):
    list_display = ("game", "move", "actor", "created_at")
    list_filter = ("move", "actor")
    search_fields = ("game__profile__user__username",)
    readonly_fields = ("created_at",)
