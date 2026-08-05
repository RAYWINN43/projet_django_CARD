from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import Profile


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    extra = 0
    fields = ("jetons",)
    verbose_name_plural = "Profil joueur"


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "jetons")
    search_fields = ("user__username", "user__email")


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
