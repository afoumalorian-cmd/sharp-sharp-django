from django.contrib import admin

from .models import Livraison, Livreur


@admin.register(Livreur)
class LivreurAdmin(admin.ModelAdmin):
    list_display = ("nom",)
    search_fields = ("nom",)


@admin.register(Livraison)
class LivraisonAdmin(admin.ModelAdmin):
    list_display = (
        "reference",
        "service",
        "depart",
        "arrivee",
        "statut",
        "livreur",
        "prix_fcfa",
        "creee_le",
    )
    list_filter = ("statut", "service", "creee_le")
    search_fields = ("reference", "depart", "arrivee")
    ordering = ("-creee_le",)
    list_select_related = ("livreur",)
    autocomplete_fields = ("livreur",)

    # L’équipe modifie l’affectation et le statut depuis cet écran.
    readonly_fields = (
        "reference",
        "service",
        "depart",
        "arrivee",
        "telephone",
        "prix_fcfa",
        "creee_le",
    )

    def has_add_permission(self, request):
        # Les clients créent les commandes depuis le formulaire prévu à cet effet.
        return False