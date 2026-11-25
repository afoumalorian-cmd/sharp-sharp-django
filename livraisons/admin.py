from django.contrib import admin, messages

from .models import Livraison, Livreur


@admin.register(Livreur)
class LivreurAdmin(admin.ModelAdmin):
    list_display = ("nom",)
    search_fields = ("nom",)


@admin.register(Livraison)
class LivraisonAdmin(admin.ModelAdmin):

    # Colonnes affichées dans la liste des livraisons.
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

    # Filtres disponibles dans l'administration.
    list_filter = (
        "statut",
        "motif_incident",
        "service",
        "creee_le",
    )

    search_fields = (
        "reference",
        "depart",
        "arrivee",
    )

    ordering = ("-creee_le",)
    list_select_related = ("livreur",)
    autocomplete_fields = ("livreur",)

    # Actions de traitement des incidents.
    actions = (
        "relancer_livraison",
        "demander_retour",
    )

    # Champs consultables en lecture seule.
    readonly_fields = (
        "reference",
        "service",
        "depart",
        "arrivee",
        "telephone",
        "prix_fcfa",
        "creee_le",
        "motif_incident",
        "incident_signale_le",
    )

    def has_add_permission(self, request):
        """Les commandes sont créées depuis l'espace client."""
        return False

    @admin.action(
        description="Relancer la livraison après un incident",
        permissions=["change"],
    )
    def relancer_livraison(self, request, queryset):
        """Relance les courses ayant fait l'objet d'un signalement."""
        nombre = queryset.filter(
            statut=Livraison.Statut.INCIDENT
        ).update(
            statut=Livraison.Statut.EN_LIVRAISON,
            tentatives_code_remise=0,
        )

        self.message_user(
            request,
            f"Courses relancées : {nombre}.",
            messages.INFO,
        )

    @admin.action(
        description="Demander le retour du colis",
        permissions=["change"],
    )
    def demander_retour(self, request, queryset):
        """Demande au livreur de retourner les colis concernés."""
        nombre = queryset.filter(
            statut=Livraison.Statut.INCIDENT
        ).update(
            statut=Livraison.Statut.RETOUR,
        )

        self.message_user(
            request,
            f"Retours demandés : {nombre}.",
            messages.INFO,
        )