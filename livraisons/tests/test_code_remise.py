import uuid

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from livraisons.code_remise import code_pour_livraison
from livraisons.models import Livraison, Livreur


class GenerationCodeRemiseTests(SimpleTestCase):
    """Tests unitaires de génération des codes de remise."""

    def test_code_est_une_chaine(self):
        code = code_pour_livraison(uuid.uuid4())

        self.assertIsInstance(code, str)

    def test_code_contient_six_caracteres(self):
        code = code_pour_livraison(uuid.uuid4())

        self.assertEqual(len(code), 6)

    def test_code_uniquement_numerique(self):
        code = code_pour_livraison(uuid.uuid4())

        self.assertRegex(code, r"^[0-9]{6}$")

    def test_code_stable_pour_meme_reference(self):
        reference = uuid.uuid4()

        premier_code = code_pour_livraison(reference)
        second_code = code_pour_livraison(reference)

        self.assertEqual(premier_code, second_code)

    def test_reference_uuid_et_chaine_equivalentes(self):
        reference = uuid.uuid4()

        self.assertEqual(
            code_pour_livraison(reference),
            code_pour_livraison(str(reference)),
        )


class ValidationCodeRemiseTests(TestCase):
    """Tests fonctionnels de validation du code de remise."""

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
            depart="Bacongo",
            arrivee="Poto-Poto",
            telephone="+242060000000",
            prix_fcfa=1500,
            statut=Livraison.Statut.EN_LIVRAISON,
            livreur=self.livreur,
        )

        self.url = reverse(
            "avancer_course",
            args=[self.livraison.reference],
        )

        self.code_correct = code_pour_livraison(
            self.livraison.reference,
        )

        # Garantit que le code fictif est différent du code attendu.
        self.code_incorrect = (
            "000000"
            if self.code_correct != "000000"
            else "000001"
        )

    def soumettre_code(self, code, **modifications):
        """Soumet le code et recharge la livraison depuis la base."""

        response = self.client.post(
            self.url,
            {
                "statut_attendu": Livraison.Statut.EN_LIVRAISON,
                "code_remise": code,
                **modifications,
            },
            follow=True,
        )

        self.livraison.refresh_from_db()

        return response

    # Validation correcte du code

    def test_code_correct_confirme_livraison(self):
        self.soumettre_code(self.code_correct)

        self.assertEqual(
            self.livraison.statut,
            Livraison.Statut.LIVREE,
        )

    def test_message_succes_code_correct(self):
        response = self.soumettre_code(self.code_correct)

        self.assertContains(
            response,
            "Le statut de la course a été mis à jour.",
        )

    def test_code_correct_apres_une_erreur(self):
        self.soumettre_code(self.code_incorrect)
        self.soumettre_code(self.code_correct)

        self.assertEqual(
            self.livraison.statut,
            Livraison.Statut.LIVREE,
        )

    # Validation du format du code

    def test_code_vide_refuse(self):
        self.soumettre_code("")

        self.assertEqual(
            self.livraison.statut,
            Livraison.Statut.EN_LIVRAISON,
        )

    def test_code_trop_court_refuse(self):
        self.soumettre_code("123")

        self.assertEqual(
            self.livraison.statut,
            Livraison.Statut.EN_LIVRAISON,
        )

    def test_code_trop_long_refuse(self):
        self.soumettre_code("1234567")

        self.assertEqual(
            self.livraison.statut,
            Livraison.Statut.EN_LIVRAISON,
        )

    def test_code_alphabetique_refuse(self):
        self.soumettre_code("ABCDEF")

        self.assertEqual(
            self.livraison.statut,
            Livraison.Statut.EN_LIVRAISON,
        )

    def test_format_invalide_ne_compte_pas_comme_tentative(self):
        self.soumettre_code("ABCDEF")

        self.assertEqual(
            self.livraison.tentatives_code_remise,
            0,
        )

    # Gestion des tentatives incorrectes

    def test_code_incorrect_refuse(self):
        response = self.soumettre_code(self.code_incorrect)

        self.assertEqual(
            self.livraison.statut,
            Livraison.Statut.EN_LIVRAISON,
        )

        self.assertContains(
            response,
            "Code de remise incorrect.",
        )

    def test_code_incorrect_incremente_compteur(self):
        self.soumettre_code(self.code_incorrect)

        self.assertEqual(
            self.livraison.tentatives_code_remise,
            1,
        )

    def test_quatre_erreurs_sans_incident(self):
        for tentative in range(4):
            with self.subTest(tentative=tentative + 1):
                self.soumettre_code(self.code_incorrect)

                self.assertEqual(
                    self.livraison.statut,
                    Livraison.Statut.EN_LIVRAISON,
                )

                self.assertEqual(
                    self.livraison.tentatives_code_remise,
                    tentative + 1,
                )

    # Déclenchement automatique d'un incident

    def test_cinquieme_erreur_declenche_incident(self):
        for _ in range(5):
            self.soumettre_code(self.code_incorrect)

        self.assertEqual(
            self.livraison.statut,
            Livraison.Statut.INCIDENT,
        )

        self.assertEqual(
            self.livraison.tentatives_code_remise,
            5,
        )

    def test_motif_incident_code_incorrect(self):
        for _ in range(5):
            self.soumettre_code(self.code_incorrect)

        self.assertEqual(
            self.livraison.motif_incident,
            Livraison.MotifIncident.CODE_INCORRECT,
        )

    def test_date_incident_enregistree(self):
        for _ in range(5):
            self.soumettre_code(self.code_incorrect)

        self.assertIsNotNone(
            self.livraison.incident_signale_le,
        )

    def test_message_incident_automatique(self):
        for _ in range(4):
            self.soumettre_code(self.code_incorrect)

        response = self.soumettre_code(self.code_incorrect)

        self.assertContains(
            response,
            "Cinq codes incorrects.",
        )

    def test_formulaire_remise_absent_pendant_incident(self):
        for _ in range(5):
            self.soumettre_code(self.code_incorrect)

        response = self.client.get(reverse("mes_courses"))

        self.assertNotContains(
            response,
            "Confirmer la remise",
        )

        self.assertContains(
            response,
            "Code de livraison incorrect",
        )