from django import forms


class BetForm(forms.Form):
    bet = forms.IntegerField(min_value=1, label="Choix de la mise")

    def __init__(self, *args, bank=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.bank = bank

    def clean_bet(self):
        bet = self.cleaned_data["bet"]
        if self.bank is not None and bet > self.bank:
            raise forms.ValidationError("Votre solde est insuffisant pour cette mise.")
        return bet
