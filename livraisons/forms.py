from django import forms

from .models import Livraison


class LivraisonForm(forms.ModelForm):
    class Meta:
        model = Livraison
        fields = ("service", "depart", "arrivee", "telephone")
        widgets = {
            "depart": forms.TextInput(
                attrs={"placeholder": "Ex. Bacongo, entrée du marché Total"}
            ),
            "arrivee": forms.TextInput(
                attrs={"placeholder": "Ex. Poto-Poto, près de la pharmacie"}
            ),
            "telephone": forms.TextInput(
                attrs={
                    "type": "tel",
                    "placeholder": "+242 06 000 00 00",
                }
            ),
        }