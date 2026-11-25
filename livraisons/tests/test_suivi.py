from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from livraisons.code_remise import code_pour_livraison
from livraisons.models import Livraison, Livreur


class SuiviLivraisonTests(TestCase):
    """Tests fonctionnels du suivi des commandes côté client."""

    @classmethod
    def setUpTestData(cls):
        cls.livreur = Livreur.objects.create(
            nom="Livreur Test",
        )

    def setUp(self):
        self.url = reverse("confirmation_livraison")

        self.client.post(
            reverse("nouvelle_livraison"),
            {
                "service": Livraison.Service.COLIS,
                "depart": "Moungali",
                "arrivee": "Ouenze",
                "telephone": "+242060000000",
            },
        )

        self.livraison = Livraison.objects.get()

    def changer_statut(self, statut, **modifications):
        """Simule une mise à jour du statut en base de données."""

        donnees = {
            "statut": statut,
            "livreur": (
                None
                if statut == Livraison.Statut.RECUE
                else self.livreur
            ),
            **modifications,
        }

        Livraison.objects.filter(
            pk=self.livraison.pk,
        ).update(**donnees)

        self.livraison.refresh_from_db()

    def test_page_suivi_accessible(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "suivi_livraison.html",
        )

    def test_suivi_sans_commande(self):
        nouveau_client = Client()

        response = nouveau_client.get(self.url)

        self.assertRedirects(
            response,
            reverse("nouvelle_livraison"),
        )

    def test_suivi_reference_conservee(self):
        response = self.client.get(self.url)

        self.assertEqual(
            response.context["livraison"].reference,
            self.livraison.reference,
        )

    def test_affichage_reference(self):
        response = self.client.get(self.url)

        self.assertContains(
            response,
            str(self.livraison.reference),
        )

    def test_affichage_trajet(self):
        response = self.client.get(self.url)

        self.assertContains(response, "Moungali")
        self.assertContains(response, "Ouenze")

    def test_affichage_service(self):
        response = self.client.get(self.url)

        self.assertContains(response, "Colis")

    def test_affichage_prix(self):
        response = self.client.get(self.url)

        self.assertEqual(
            response.context["prix_fcfa"],
            "1\u202f500",
        )

    def test_statut_commande_recue(self):
        response = self.client.get(self.url)

        self.assertContains(response, "Commande reçue")

    def test_statut_livreur_affecte(self):
        self.changer_statut(
            Livraison.Statut.AFFECTEE,
        )

        response = self.client.get(self.url)

        self.assertContains(response, "Livreur affecté")

    def test_statut_colis_recupere(self):
        self.changer_statut(
            Livraison.Statut.RECUPEREE,
        )

        response = self.client.get(self.url)

        self.assertContains(response, "Colis récupéré")

    def test_statut_en_livraison(self):
        self.changer_statut(
            Livraison.Statut.EN_LIVRAISON,
        )

        response = self.client.get(self.url)

        self.assertContains(response, "En livraison")

    def test_statut_livre(self):
        self.changer_statut(
            Livraison.Statut.LIVREE,
        )

        response = self.client.get(self.url)

        self.assertContains(response, "Livrée")

    def test_statut_incident_signale(self):
        self.changer_statut(
            Livraison.Statut.INCIDENT,
            motif_incident=Livraison.MotifIncident.ABSENT,
            incident_signale_le=timezone.now(),
        )

        response = self.client.get(self.url)

        self.assertContains(response, "Incident signalé")

    def test_statut_retour_a_effectuer(self):
        self.changer_statut(
            Livraison.Statut.RETOUR,
            motif_incident=Livraison.MotifIncident.ADRESSE,
            incident_signale_le=timezone.now(),
        )

        response = self.client.get(self.url)

        self.assertContains(response, "Retour à effectuer")

    def test_statut_retourne(self):
        self.changer_statut(
            Livraison.Statut.RETOURNEE,
            motif_incident=Livraison.MotifIncident.ADRESSE,
            incident_signale_le=timezone.now(),
        )

        response = self.client.get(self.url)

        self.assertContains(response, "Retournée")

    def test_code_remise_visible_en_livraison(self):
        self.changer_statut(
            Livraison.Statut.EN_LIVRAISON,
        )

        response = self.client.get(self.url)

        code_attendu = code_pour_livraison(
            self.livraison.reference,
        )

        self.assertEqual(
            response.context["code_remise"],
            code_attendu,
        )

        self.assertContains(response, code_attendu)

    def test_code_remise_masque_avant_livraison(self):
        statuts = (
            Livraison.Statut.RECUE,
            Livraison.Statut.AFFECTEE,
            Livraison.Statut.RECUPEREE,
        )

        for statut in statuts:
            with self.subTest(statut=statut):
                self.changer_statut(statut)

                response = self.client.get(self.url)

                self.assertEqual(
                    response.context["code_remise"],
                    "",
                )

    def test_code_remise_masque_apres_livraison(self):
        self.changer_statut(
            Livraison.Statut.LIVREE,
        )

        response = self.client.get(self.url)

        self.assertEqual(
            response.context["code_remise"],
            "",
        )

    def test_code_remise_masque_pendant_incident(self):
        self.changer_statut(
            Livraison.Statut.INCIDENT,
            motif_incident=Livraison.MotifIncident.CODE_INCORRECT,
            incident_signale_le=timezone.now(),
        )

        response = self.client.get(self.url)

        self.assertEqual(
            response.context["code_remise"],
            "",
        )

    def test_code_remise_masque_pendant_et_apres_retour(self):
        statuts = (
            Livraison.Statut.RETOUR,
            Livraison.Statut.RETOURNEE,
        )

        for statut in statuts:
            with self.subTest(statut=statut):
                self.changer_statut(
                    statut,
                    motif_incident=Livraison.MotifIncident.ABSENT,
                    incident_signale_le=timezone.now(),
                )

                response = self.client.get(self.url)

                self.assertEqual(
                    response.context["code_remise"],
                    "",
                )

    def test_actualisation_statut(self):
        response = self.client.get(self.url)

        self.assertContains(response, "Commande reçue")

        self.changer_statut(
            Livraison.Statut.AFFECTEE,
        )

        response = self.client.get(self.url)

        self.assertContains(response, "Livreur affecté")

    def test_activer_suivi_sans_creer_de_commande(self):
        self.client.get(self.url)
        self.client.get(self.url)
        self.client.get(self.url)

        self.assertEqual(Livraison.objects.count(), 1)

    def test_suivi_commande_supprimee(self):
        self.livraison.delete()

        response = self.client.get(self.url)

        self.assertRedirects(
            response,
            reverse("nouvelle_livraison"),
        )

        self.assertNotIn(
            "derniere_livraison",
            self.client.session,
        )

    def test_suivi_non_mis_en_cache(self):
        response = self.client.get(self.url)

        self.assertIn(
            "no-store",
            response.headers.get("Cache-Control", ""),
        )