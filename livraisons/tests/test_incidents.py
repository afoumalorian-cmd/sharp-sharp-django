from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from livraisons.code_remise import code_pour_livraison
from livraisons.models import Livraison, Livreur


class IncidentLivraisonTests(TestCase):
    """Tests fonctionnels de la gestion des incidents."""

    @classmethod
    def setUpTestData(cls):
        cls.utilisateur = get_user_model().objects.create_user(
            username="livreur_test",
        )

        cls.livreur = Livreur.objects.create(
            nom="Livreur Test",
            compte=cls.utilisateur,
        )

    def setUp(self):
        self.client.force_login(self.utilisateur)

        self.livraison = Livraison.objects.create(
            service=Livraison.Service.COLIS,
            depart="Moungali",
            arrivee="Ouenze",
            telephone="+242060000000",
            prix_fcfa=1500,
            statut=Livraison.Statut.EN_LIVRAISON,
            livreur=self.livreur,
        )

        self.url = reverse(
            "signaler_incident",
            args=[self.livraison.reference],
        )

        self.client_suivi = Client()

        session = self.client_suivi.session
        session["derniere_livraison"] = {
            "reference": str(self.livraison.reference),
        }
        session.save()

    def signaler_incident(self, motif):
        """Envoie un signalement et recharge la course depuis la base."""

        response = self.client.post(
            self.url,
            {"motif": motif},
            follow=True,
        )

        self.livraison.refresh_from_db()

        return response

    def changer_statut(self, statut):
        """Prépare une course dans un état donné."""

        self.livraison.statut = statut
        self.livraison.save(update_fields=["statut"])

    # Signalements manuels

    def test_signalement_destinataire_absent(self):
        self.signaler_incident(
            Livraison.MotifIncident.ABSENT,
        )

        self.assertEqual(
            self.livraison.statut,
            Livraison.Statut.INCIDENT,
        )

        self.assertEqual(
            self.livraison.motif_incident,
            Livraison.MotifIncident.ABSENT,
        )

    def test_signalement_adresse_introuvable(self):
        self.signaler_incident(
            Livraison.MotifIncident.ADRESSE,
        )

        self.assertEqual(
            self.livraison.statut,
            Livraison.Statut.INCIDENT,
        )

        self.assertEqual(
            self.livraison.motif_incident,
            Livraison.MotifIncident.ADRESSE,
        )

    def test_signalement_code_incorrect(self):
        self.signaler_incident(
            Livraison.MotifIncident.CODE_INCORRECT,
        )

        self.assertEqual(
            self.livraison.statut,
            Livraison.Statut.INCIDENT,
        )

        self.assertEqual(
            self.livraison.motif_incident,
            Livraison.MotifIncident.CODE_INCORRECT,
        )

    def test_date_signalement_enregistree(self):
        avant = timezone.now()

        self.signaler_incident(
            Livraison.MotifIncident.ABSENT,
        )

        apres = timezone.now()

        self.assertIsNotNone(
            self.livraison.incident_signale_le,
        )

        self.assertGreaterEqual(
            self.livraison.incident_signale_le,
            avant,
        )

        self.assertLessEqual(
            self.livraison.incident_signale_le,
            apres,
        )

    def test_message_confirmation_signalement(self):
        response = self.signaler_incident(
            Livraison.MotifIncident.ABSENT,
        )

        self.assertContains(
            response,
            "Incident signalé.",
        )

    # Validation des motifs

    def test_motif_invalide_refuse(self):
        response = self.signaler_incident(
            "motif_inexistant",
        )

        self.assertEqual(
            self.livraison.statut,
            Livraison.Statut.EN_LIVRAISON,
        )

        self.assertEqual(
            self.livraison.motif_incident,
            "",
        )

        self.assertContains(
            response,
            "Sélectionne un motif",
        )

    def test_motif_vide_refuse(self):
        self.signaler_incident("")

        self.assertEqual(
            self.livraison.statut,
            Livraison.Statut.EN_LIVRAISON,
        )

        self.assertIsNone(
            self.livraison.incident_signale_le,
        )

    # Règles métier

    def test_signalement_avant_recuperation_refuse(self):
        self.changer_statut(
            Livraison.Statut.AFFECTEE,
        )

        self.signaler_incident(
            Livraison.MotifIncident.ABSENT,
        )

        self.assertEqual(
            self.livraison.statut,
            Livraison.Statut.AFFECTEE,
        )

    def test_signalement_avant_demarrage_refuse(self):
        self.changer_statut(
            Livraison.Statut.RECUPEREE,
        )

        self.signaler_incident(
            Livraison.MotifIncident.ABSENT,
        )

        self.assertEqual(
            self.livraison.statut,
            Livraison.Statut.RECUPEREE,
        )

    def test_signalement_apres_livraison_refuse(self):
        self.changer_statut(
            Livraison.Statut.LIVREE,
        )

        self.signaler_incident(
            Livraison.MotifIncident.ABSENT,
        )

        self.assertEqual(
            self.livraison.statut,
            Livraison.Statut.LIVREE,
        )

    def test_second_signalement_ne_modifie_pas_incident(self):
        self.signaler_incident(
            Livraison.MotifIncident.ABSENT,
        )

        premiere_date = self.livraison.incident_signale_le

        self.signaler_incident(
            Livraison.MotifIncident.ADRESSE,
        )

        self.assertEqual(
            self.livraison.motif_incident,
            Livraison.MotifIncident.ABSENT,
        )

        self.assertEqual(
            self.livraison.incident_signale_le,
            premiere_date,
        )

    def test_signalement_conserve_livreur(self):
        self.signaler_incident(
            Livraison.MotifIncident.ABSENT,
        )

        self.assertEqual(
            self.livraison.livreur,
            self.livreur,
        )

    def test_signalement_conserve_prix(self):
        self.signaler_incident(
            Livraison.MotifIncident.ADRESSE,
        )

        self.assertEqual(
            self.livraison.prix_fcfa,
            1500,
        )

    def test_signalement_conserve_reference(self):
        reference_initiale = self.livraison.reference

        self.signaler_incident(
            Livraison.MotifIncident.ADRESSE,
        )

        self.assertEqual(
            self.livraison.reference,
            reference_initiale,
        )

    # Affichage côté livreur

    def test_formulaire_incident_visible_en_livraison(self):
        response = self.client.get(
            reverse("mes_courses"),
        )

        self.assertContains(
            response,
            "Signaler un incident",
        )

        self.assertContains(
            response,
            "Destinataire absent",
        )

        self.assertContains(
            response,
            "Adresse introuvable",
        )

        self.assertContains(
            response,
            "Code de livraison incorrect",
        )

    def test_motif_visible_apres_signalement(self):
        response = self.signaler_incident(
            Livraison.MotifIncident.ADRESSE,
        )

        self.assertContains(
            response,
            "Incident signalé",
        )

        self.assertContains(
            response,
            "Adresse introuvable",
        )

    def test_confirmation_remise_absente_pendant_incident(self):
        response = self.signaler_incident(
            Livraison.MotifIncident.ABSENT,
        )

        self.assertNotContains(
            response,
            "Confirmer la remise",
        )

    # Suivi côté client

    def test_suivi_client_affiche_incident(self):
        self.signaler_incident(
            Livraison.MotifIncident.ABSENT,
        )

        response = self.client_suivi.get(
            reverse("confirmation_livraison"),
        )

        self.assertContains(
            response,
            "Incident signalé",
        )

    def test_code_remise_masque_pendant_incident(self):
        self.signaler_incident(
            Livraison.MotifIncident.CODE_INCORRECT,
        )

        response = self.client_suivi.get(
            reverse("confirmation_livraison"),
        )

        self.assertEqual(
            response.context["code_remise"],
            "",
        )

    def test_signalement_course_bloquee(self):
        # Compatibilité avec les anciennes commandes bloquées
        # avant l'introduction des incidents automatiques.

        self.livraison.tentatives_code_remise = 5

        self.livraison.save(
            update_fields=["tentatives_code_remise"],
        )

        self.signaler_incident(
            Livraison.MotifIncident.CODE_INCORRECT,
        )

        self.assertEqual(
            self.livraison.statut,
            Livraison.Statut.INCIDENT,
        )

        self.assertEqual(
            self.livraison.tentatives_code_remise,
            5,
        )