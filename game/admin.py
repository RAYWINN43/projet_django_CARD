from django.contrib import admin

from .models import Game, MoveLog


class MoveLogInline(admin.TabularInline):
    model = MoveLog
    extra = 0
    readonly_fields = ("move", "actor", "card", "details", "created_at")
    can_delete = False


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
    inlines = (MoveLogInline,)


@admin.register(MoveLog)
class MoveLogAdmin(admin.ModelAdmin):
    list_display = ("game", "move", "actor", "created_at")
    list_filter = ("move", "actor")
    search_fields = ("game__profile__user__username",)
    readonly_fields = ("created_at",)
