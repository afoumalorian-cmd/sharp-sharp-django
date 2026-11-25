from datetime import timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from livraisons.models import Livraison, Livreur


class LivreurTests(TestCase):
    """Tests fonctionnels de l'espace livreur."""

    @classmethod
    def setUpTestData(cls):
        cls.utilisateur = get_user_model().objects.create_user(
            username="livreur_test",
            password="MotDePasseTest2026!",
        )

        cls.livreur = Livreur.objects.create(
            nom="Livreur Test",
            compte=cls.utilisateur,
        )

        cls.autre_utilisateur = get_user_model().objects.create_user(
            username="autre_livreur",
        )

        cls.autre_livreur = Livreur.objects.create(
            nom="Autre livreur",
            compte=cls.autre_utilisateur,
        )

        cls.utilisateur_sans_livreur = (
            get_user_model().objects.create_user(
                username="client_test",
            )
        )

    def setUp(self):
        self.url = reverse("mes_courses")
        self.client.force_login(self.utilisateur)

    def creer_course(self, **modifications):
        """Crée une course fictive affectée au livreur de test."""
        donnees = {
            "service": Livraison.Service.COLIS,
            "depart": "Bacongo",
            "arrivee": "Poto-Poto",
            "telephone": "+242060000000",
            "prix_fcfa": 1500,
            "statut": Livraison.Statut.AFFECTEE,
            "livreur": self.livreur,
            **modifications,
        }

        return Livraison.objects.create(**donnees)

    def avancer(self, livraison, statut_attendu):
        """Soumet une transition depuis l'espace livreur."""
        return self.client.post(
            reverse(
                "avancer_course",
                args=[livraison.reference],
            ),
            {"statut_attendu": statut_attendu},
        )

    # Authentification

    def test_page_connexion_accessible(self):
        client = Client()

        response = client.get(
            reverse("connexion_livreur")
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Connexion livreur")

    def test_connexion_valide(self):
        client = Client()

        response = client.post(
            reverse("connexion_livreur"),
            {
                "username": "livreur_test",
                "password": "MotDePasseTest2026!",
            },
        )

        self.assertRedirects(response, self.url)

    def test_connexion_mot_de_passe_incorrect(self):
        client = Client()

        response = client.post(
            reverse("connexion_livreur"),
            {
                "username": "livreur_test",
                "password": "MotDePasseIncorrect",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors)

    def test_espace_livreur_accessible(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "espace_livreur.html",
        )

    def test_deconnexion(self):
        response = self.client.post(
            reverse("deconnexion_livreur")
        )

        self.assertRedirects(
            response,
            reverse("connexion_livreur"),
        )

        self.assertNotIn(
            "_auth_user_id",
            self.client.session,
        )

    # Affichage des courses

    def test_aucune_course_affectee(self):
        response = self.client.get(self.url)

        self.assertContains(
            response,
            "Aucune course",
        )

    def test_course_affectee_visible(self):
        livraison = self.creer_course()

        response = self.client.get(self.url)

        self.assertContains(
            response,
            str(livraison.reference),
        )

    def test_affichage_plusieurs_courses(self):
        premiere = self.creer_course()
        seconde = self.creer_course(
            depart="Moungali",
            arrivee="Ouenze",
        )

        response = self.client.get(self.url)

        self.assertContains(response, str(premiere.reference))
        self.assertContains(response, str(seconde.reference))

    def test_affichage_trajet(self):
        self.creer_course()

        response = self.client.get(self.url)

        self.assertContains(response, "Bacongo")
        self.assertContains(response, "Poto-Poto")

    def test_affichage_course_livree(self):
        livraison = self.creer_course(
            statut=Livraison.Statut.LIVREE,
        )

        response = self.client.get(self.url)

        self.assertContains(response, "Livrée")
        self.assertContains(response, str(livraison.reference))

    def test_courses_triees_par_date_decroissante(self):
        ancienne = self.creer_course()
        recente = self.creer_course()

        maintenant = timezone.now()

        # Définit deux dates distinctes pour garantir un ordre déterministe.
        Livraison.objects.filter(pk=ancienne.pk).update(
            creee_le=maintenant - timedelta(days=1),
        )

        Livraison.objects.filter(pk=recente.pk).update(
            creee_le=maintenant,
        )

        response = self.client.get(self.url)

        courses = response.context["courses"]

        self.assertEqual(
            courses[0]["livraison"].reference,
            recente.reference,
        )

        self.assertEqual(
            courses[1]["livraison"].reference,
            ancienne.reference,
        )

    # Progression des livraisons

    def test_action_recuperation_disponible(self):
        self.creer_course()

        response = self.client.get(self.url)

        self.assertContains(
            response,
            "Confirmer la récupération",
        )

    def test_confirmation_recuperation(self):
        livraison = self.creer_course()

        response = self.avancer(
            livraison,
            Livraison.Statut.AFFECTEE,
        )

        self.assertRedirects(response, self.url)

        livraison.refresh_from_db()

        self.assertEqual(
            livraison.statut,
            Livraison.Statut.RECUPEREE,
        )

    def test_action_demarrage_disponible(self):
        self.creer_course(
            statut=Livraison.Statut.RECUPEREE,
        )

        response = self.client.get(self.url)

        self.assertContains(
            response,
            "Démarrer la livraison",
        )

    def test_demarrage_livraison(self):
        livraison = self.creer_course(
            statut=Livraison.Statut.RECUPEREE,
        )

        response = self.avancer(
            livraison,
            Livraison.Statut.RECUPEREE,
        )

        self.assertRedirects(response, self.url)

        livraison.refresh_from_db()

        self.assertEqual(
            livraison.statut,
            Livraison.Statut.EN_LIVRAISON,
        )

    def test_message_succes_apres_progression(self):
        livraison = self.creer_course()

        response = self.client.post(
            reverse(
                "avancer_course",
                args=[livraison.reference],
            ),
            {"statut_attendu": Livraison.Statut.AFFECTEE},
            follow=True,
        )

        self.assertContains(
            response,
            "Le statut de la course a été mis à jour.",
        )

    def test_action_absente_apres_livraison(self):
        self.creer_course(
            statut=Livraison.Statut.LIVREE,
        )

        response = self.client.get(self.url)

        course = response.context["courses"][0]

        self.assertIsNone(course["action"])

    def test_formulaire_code_visible_en_livraison(self):
        self.creer_course(
            statut=Livraison.Statut.EN_LIVRAISON,
        )

        response = self.client.get(self.url)

        self.assertContains(response, "Code de remise")
        self.assertContains(response, "Confirmer la remise")

    def test_espace_livreur_non_mis_en_cache(self):
        response = self.client.get(self.url)

        self.assertIn(
            "no-store",
            response.headers.get("Cache-Control", ""),
        )