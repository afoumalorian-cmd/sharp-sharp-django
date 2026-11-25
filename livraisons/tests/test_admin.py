from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from livraisons.models import Livraison, Livreur


class AdministrationLivraisonsTests(TestCase):
    """Tests fonctionnels de l'administration Sharp Sharp."""

    @classmethod
    def setUpTestData(cls):
        cls.administrateur = get_user_model().objects.create_superuser(
            username="admin_test",
            email="admin@example.com",
            password="AdminTest2026!",
        )

        cls.utilisateur_livreur = get_user_model().objects.create_user(
            username="livreur_test",
        )

        cls.livreur = Livreur.objects.create(
            nom="Livreur Test",
            compte=cls.utilisateur_livreur,
        )

    def setUp(self):
        self.client.force_login(self.administrateur)

        self.url_livraisons = reverse(
            "admin:livraisons_livraison_changelist",
        )

        self.url_livreurs = reverse(
            "admin:livraisons_livreur_changelist",
        )

    def creer_livraison(self, **modifications):
        """Crée une livraison fictive pour les tests."""

        donnees = {
            "service": Livraison.Service.COLIS,
            "depart": "Moungali",
            "arrivee": "Ouenze",
            "telephone": "+242060000000",
            "prix_fcfa": 1500,
            **modifications,
        }

        return Livraison.objects.create(**donnees)

    def creer_incident(self, **modifications):
        """Crée une livraison avec un incident déjà enregistré."""

        donnees = {
            "statut": Livraison.Statut.INCIDENT,
            "livreur": self.livreur,
            "motif_incident": Livraison.MotifIncident.CODE_INCORRECT,
            "tentatives_code_remise": 5,
            "incident_signale_le": timezone.now(),
            **modifications,
        }

        return self.creer_livraison(**donnees)

    def executer_action(self, action, *livraisons):
        """Exécute une action depuis la liste administrative."""

        return self.client.post(
            self.url_livraisons,
            {
                "action": action,
                "_selected_action": [
                    str(livraison.pk)
                    for livraison in livraisons
                ],
            },
            follow=True,
        )

    # ---------------------------------------------------------
    # Administration des livreurs
    # ---------------------------------------------------------

    def test_liste_livreurs_accessible(self):
        response = self.client.get(self.url_livreurs)

        self.assertEqual(response.status_code, 200)

    def test_livreur_visible_dans_administration(self):
        response = self.client.get(self.url_livreurs)

        self.assertContains(response, self.livreur.nom)

    def test_creation_livreur_depuis_administration(self):
        response = self.client.post(
            reverse("admin:livraisons_livreur_add"),
            {
                "nom": "Nouveau livreur",
                "compte": "",
            },
        )

        self.assertEqual(response.status_code, 302)

        self.assertTrue(
            Livreur.objects.filter(
                nom="Nouveau livreur",
            ).exists()
        )

    # ---------------------------------------------------------
    # Administration des livraisons
    # ---------------------------------------------------------

    def test_liste_livraisons_accessible(self):
        response = self.client.get(self.url_livraisons)

        self.assertEqual(response.status_code, 200)

    def test_livraison_visible_dans_administration(self):
        livraison = self.creer_livraison()

        response = self.client.get(self.url_livraisons)

        self.assertContains(response, str(livraison.reference))
        self.assertContains(response, "Moungali")
        self.assertContains(response, "Ouenze")

    def test_fiche_livraison_accessible(self):
        livraison = self.creer_livraison()

        response = self.client.get(
            reverse(
                "admin:livraisons_livraison_change",
                args=[livraison.pk],
            ),
        )

        self.assertEqual(response.status_code, 200)

    def test_affectation_livreur_depuis_administration(self):
        livraison = self.creer_livraison()

        response = self.client.post(
            reverse(
                "admin:livraisons_livraison_change",
                args=[livraison.pk],
            ),
            {
                "statut": Livraison.Statut.AFFECTEE,
                "livreur": self.livreur.pk,
                "_save": "Save",
            },
        )

        self.assertEqual(response.status_code, 302)

        livraison.refresh_from_db()

        self.assertEqual(livraison.livreur, self.livreur)
        self.assertEqual(
            livraison.statut,
            Livraison.Statut.AFFECTEE,
        )

    def test_affectation_sans_livreur_refusee(self):
        livraison = self.creer_livraison()

        response = self.client.post(
            reverse(
                "admin:livraisons_livraison_change",
                args=[livraison.pk],
            ),
            {
                "statut": Livraison.Statut.AFFECTEE,
                "livreur": "",
                "_save": "Save",
            },
        )

        self.assertEqual(response.status_code, 200)

        self.assertIn(
            "livreur",
            response.context["adminform"].form.errors,
        )

        livraison.refresh_from_db()

        self.assertEqual(
            livraison.statut,
            Livraison.Statut.RECUE,
        )

    def test_motif_incident_visible(self):
        livraison = self.creer_incident()

        response = self.client.get(
            reverse(
                "admin:livraisons_livraison_change",
                args=[livraison.pk],
            ),
        )

        self.assertContains(
            response,
            "Code de livraison incorrect",
        )

    # ---------------------------------------------------------
    # Recherche et filtrage
    # ---------------------------------------------------------

    def test_recherche_livraison_par_reference(self):
        livraison = self.creer_livraison()

        autre = self.creer_livraison(
            depart="Bacongo",
            arrivee="Poto-Poto",
        )

        response = self.client.get(
            self.url_livraisons,
            {"q": str(livraison.reference)},
        )

        self.assertContains(response, str(livraison.reference))
        self.assertNotContains(response, str(autre.reference))

    def test_filtrage_livraisons_par_statut(self):
        incident = self.creer_incident()
        commande = self.creer_livraison()

        response = self.client.get(
            self.url_livraisons,
            {"statut__exact": Livraison.Statut.INCIDENT},
        )

        self.assertContains(response, str(incident.reference))
        self.assertNotContains(response, str(commande.reference))

    # ---------------------------------------------------------
    # Relance après un incident
    # ---------------------------------------------------------

    def test_relance_livraison_apres_incident(self):
        livraison = self.creer_incident()

        self.executer_action(
            "relancer_livraison",
            livraison,
        )

        livraison.refresh_from_db()

        self.assertEqual(
            livraison.statut,
            Livraison.Statut.EN_LIVRAISON,
        )

    def test_relance_reinitialise_compteur_code(self):
        livraison = self.creer_incident()

        self.executer_action(
            "relancer_livraison",
            livraison,
        )

        livraison.refresh_from_db()

        self.assertEqual(
            livraison.tentatives_code_remise,
            0,
        )

    def test_relance_conserve_livreur(self):
        livraison = self.creer_incident()

        self.executer_action(
            "relancer_livraison",
            livraison,
        )

        livraison.refresh_from_db()

        self.assertEqual(livraison.livreur, self.livreur)

    def test_relance_conserve_prix_et_reference(self):
        livraison = self.creer_incident()
        reference = livraison.reference

        self.executer_action(
            "relancer_livraison",
            livraison,
        )

        livraison.refresh_from_db()

        self.assertEqual(livraison.prix_fcfa, 1500)
        self.assertEqual(livraison.reference, reference)

    def test_relance_ignore_livraison_sans_incident(self):
        livraison = self.creer_livraison()

        self.executer_action(
            "relancer_livraison",
            livraison,
        )

        livraison.refresh_from_db()

        self.assertEqual(
            livraison.statut,
            Livraison.Statut.RECUE,
        )

    def test_relance_plusieurs_livraisons(self):
        premiere = self.creer_incident()
        seconde = self.creer_incident()

        self.executer_action(
            "relancer_livraison",
            premiere,
            seconde,
        )

        premiere.refresh_from_db()
        seconde.refresh_from_db()

        self.assertEqual(
            premiere.statut,
            Livraison.Statut.EN_LIVRAISON,
        )

        self.assertEqual(
            seconde.statut,
            Livraison.Statut.EN_LIVRAISON,
        )

    # ---------------------------------------------------------
    # Retour des colis
    # ---------------------------------------------------------

    def test_demande_retour_apres_incident(self):
        livraison = self.creer_incident()

        self.executer_action(
            "demander_retour",
            livraison,
        )

        livraison.refresh_from_db()

        self.assertEqual(
            livraison.statut,
            Livraison.Statut.RETOUR,
        )

    def test_demande_retour_conserve_motif(self):
        livraison = self.creer_incident(
            motif_incident=Livraison.MotifIncident.ABSENT,
        )

        self.executer_action(
            "demander_retour",
            livraison,
        )

        livraison.refresh_from_db()

        self.assertEqual(
            livraison.motif_incident,
            Livraison.MotifIncident.ABSENT,
        )

    def test_demande_retour_ignore_livraison_sans_incident(self):
        livraison = self.creer_livraison()

        self.executer_action(
            "demander_retour",
            livraison,
        )

        livraison.refresh_from_db()

        self.assertEqual(
            livraison.statut,
            Livraison.Statut.RECUE,
        )

    def test_confirmation_retour_par_livreur(self):
        livraison = self.creer_incident()

        self.executer_action(
            "demander_retour",
            livraison,
        )

        self.client.force_login(self.utilisateur_livreur)

        response = self.client.post(
            reverse(
                "avancer_course",
                args=[livraison.reference],
            ),
            {
                "statut_attendu": Livraison.Statut.RETOUR,
            },
        )

        self.assertRedirects(response, reverse("mes_courses"))

        livraison.refresh_from_db()

        self.assertEqual(
            livraison.statut,
            Livraison.Statut.RETOURNEE,
        )

    def test_demande_retour_multiple(self):
        premiere = self.creer_incident()
        seconde = self.creer_incident()

        self.executer_action(
            "demander_retour",
            premiere,
            seconde,
        )

        premiere.refresh_from_db()
        seconde.refresh_from_db()

        self.assertEqual(
            premiere.statut,
            Livraison.Statut.RETOUR,
        )

        self.assertEqual(
            seconde.statut,
            Livraison.Statut.RETOUR,
        )