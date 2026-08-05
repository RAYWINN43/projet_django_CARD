#page de gestion des mots de passe chiffre caractere spe et une lettre 
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _


class PasswordCompositionValidator:
    def validate(self, password, user=None):
        has_letter = any(char.isalpha() for char in password)
        has_digit = any(char.isdigit() for char in password)
        has_special = any(
            not char.isalnum() and not char.isspace() for char in password
        )

        if not has_letter or not has_digit or not has_special:
            raise ValidationError(
                _(
                    "Le mot de passe doit contenir au moins une lettre, "
                    "un chiffre et un caractere special."
                ),
                code="password_missing_required_character_type",
            )

    def get_help_text(self):
        return _(
            "Votre mot de passe doit contenir au moins une lettre, "
            "un chiffre et un caractere special."
        )
