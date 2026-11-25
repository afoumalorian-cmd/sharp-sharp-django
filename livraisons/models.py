import uuid

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.conf import settings


class Livreur(models.Model):
    nom = models.CharField("Nom complet", max_length=120)
    compte = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        verbose_name="Compte de connexion",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="profil_livreur",
    )

    class Meta:
        ordering = ["nom"]

    def __str__(self):
        return self.nom


class Livraison(models.Model):
    class Service(models.TextChoices):
        COLIS = "colis", "Colis"
        DOCUMENTS = "documents", "Documents"

    class Statut(models.TextChoices):
        RECUE = "recue", "Commande reçue"
        AFFECTEE = "affectee", "Livreur affecté"
        RECUPEREE = "recuperee", "Colis récupéré"
        EN_LIVRAISON = "en_livraison", "En livraison"
        LIVREE = "livree", "Livrée"
        INCIDENT = "incident", "Incident signalé"
        RETOUR = "retour", "Retour à effectuer"
        RETOURNEE = "retournee", "Retournée"

    class MotifIncident(models.TextChoices):
        ABSENT = "destinataire_absent", "Destinataire absent"
        ADRESSE = "adresse_introuvable", "Adresse introuvable"
        CODE_INCORRECT = "code_incorrect", "Code de livraison incorrect"

    reference = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    service = models.CharField(max_length=12, choices=Service.choices)
    depart = models.CharField("Quartier et repère de départ", max_length=180)
    arrivee = models.CharField("Quartier et repère d’arrivée", max_length=180)
    telephone = models.CharField(
        "Téléphone du destinataire",
        max_length=24,
        validators=[
            RegexValidator(
                r"\A(?:\+242[ .-]*)?(?:[0-9][ .-]*){8}[0-9]\Z",
                "Saisissez 9 chiffres, précédés de +242 si nécessaire.",
            )
        ],
    )
    prix_fcfa = models.PositiveIntegerField("Prix en FCFA")
    creee_le = models.DateTimeField("Créée le", auto_now_add=True)
    statut = models.CharField(
        max_length=16,
        choices=Statut.choices,
        default=Statut.RECUE,
    )
    tentatives_code_remise = models.PositiveSmallIntegerField(
    "Tentatives de code de remise",
    default=0,
    editable=False,
    )

    motif_incident = models.CharField(
        max_length=50,
        choices=MotifIncident.choices,
        blank=True,
        editable=False,
    )
    incident_signale_le = models.DateTimeField(
        null=True,
        blank=True,
        editable=False,
    )

    # Une commande peut être enregistrée avant qu’un livreur soit disponible.
    # PROTECT conserve le lien avec le livreur dans les commandes existantes.
    livreur = models.ForeignKey(
        Livreur,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="livraisons",
    )

    class Meta:
        verbose_name = "livraison"
        verbose_name_plural = "livraisons"

    def __str__(self):
        return str(self.reference)

    def clean(self):
        super().clean()

        statuts_avec_incident = {
            self.Statut.INCIDENT,
            self.Statut.RETOUR,
            self.Statut.RETOURNEE,
        }
        if self.statut in statuts_avec_incident and not self.motif_incident:
            raise ValidationError({
                "statut": "Cette course doit d’abord faire l’objet d’un signalement."
            })

        # L’administration appelle cette validation avant l’enregistrement.
        if self.statut == self.Statut.RECUE and self.livreur_id:
            raise ValidationError({
                "statut": "Passez la commande à « Livreur affecté » pour enregistrer l’affectation."
            })

        if self.statut and self.statut != self.Statut.RECUE and not self.livreur_id:
            raise ValidationError({
                "livreur": "Sélectionnez un livreur pour ce statut."
            })