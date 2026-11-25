from django.test import TestCase

from livraisons.forms import LivraisonForm
from livraisons.models import Livraison


class LivraisonFormTests(TestCase):
    """Tests de validation du formulaire de commande."""

    def setUp(self):
        self.donnees_valides = {
            "service": Livraison.Service.COLIS,
            "depart": "Bacongo",
            "arrivee": "Poto-Poto",
            "telephone": "+242060000000",
        }

    def creer_formulaire(self, **modifications):
        """Construit un formulaire avec des données de test."""
        return LivraisonForm(
            data={
                **self.donnees_valides,
                **modifications,
            }
        )

    def test_formulaire_colis_valide(self):
        formulaire = self.creer_formulaire()

        self.assertTrue(formulaire.is_valid(), formulaire.errors)

    def test_formulaire_documents_valide(self):
        formulaire = self.creer_formulaire(
            service=Livraison.Service.DOCUMENTS,
        )

        self.assertTrue(formulaire.is_valid(), formulaire.errors)

    def test_service_invalide(self):
        formulaire = self.creer_formulaire(
            service="service_inexistant",
        )

        self.assertFalse(formulaire.is_valid())
        self.assertIn("service", formulaire.errors)

    def test_service_obligatoire(self):
        formulaire = self.creer_formulaire(service="")

        self.assertFalse(formulaire.is_valid())
        self.assertIn("service", formulaire.errors)

    def test_depart_obligatoire(self):
        formulaire = self.creer_formulaire(depart="")

        self.assertFalse(formulaire.is_valid())
        self.assertIn("depart", formulaire.errors)

    def test_arrivee_obligatoire(self):
        formulaire = self.creer_formulaire(arrivee="")

        self.assertFalse(formulaire.is_valid())
        self.assertIn("arrivee", formulaire.errors)

    def test_telephone_obligatoire(self):
        formulaire = self.creer_formulaire(telephone="")

        self.assertFalse(formulaire.is_valid())
        self.assertIn("telephone", formulaire.errors)

    def test_telephone_local_valide(self):
        formulaire = self.creer_formulaire(
            telephone="060000000",
        )

        self.assertTrue(formulaire.is_valid(), formulaire.errors)

    def test_telephone_international_valide(self):
        formulaire = self.creer_formulaire(
            telephone="+242060000000",
        )

        self.assertTrue(formulaire.is_valid(), formulaire.errors)

    def test_telephone_avec_espaces_valide(self):
        formulaire = self.creer_formulaire(
            telephone="+242 06 000 00 00",
        )

        self.assertTrue(formulaire.is_valid(), formulaire.errors)

    def test_telephone_trop_court(self):
        formulaire = self.creer_formulaire(telephone="123")

        self.assertFalse(formulaire.is_valid())
        self.assertIn("telephone", formulaire.errors)

    def test_telephone_trop_long(self):
        formulaire = self.creer_formulaire(
            telephone="0600000000000",
        )

        self.assertFalse(formulaire.is_valid())
        self.assertIn("telephone", formulaire.errors)

    def test_telephone_avec_lettres_invalide(self):
        formulaire = self.creer_formulaire(
            telephone="ABCDEF123",
        )

        self.assertFalse(formulaire.is_valid())
        self.assertIn("telephone", formulaire.errors)

    def test_depart_trop_long(self):
        formulaire = self.creer_formulaire(
            depart="A" * 181,
        )

        self.assertFalse(formulaire.is_valid())
        self.assertIn("depart", formulaire.errors)

    def test_arrivee_trop_longue(self):
        formulaire = self.creer_formulaire(
            arrivee="A" * 181,
        )

        self.assertFalse(formulaire.is_valid())
        self.assertIn("arrivee", formulaire.errors)

    def test_depart_avec_espaces_uniquement(self):
        formulaire = self.creer_formulaire(depart="   ")

        self.assertFalse(formulaire.is_valid())
        self.assertIn("depart", formulaire.errors)

    def test_arrivee_avec_espaces_uniquement(self):
        formulaire = self.creer_formulaire(arrivee="   ")

        self.assertFalse(formulaire.is_valid())
        self.assertIn("arrivee", formulaire.errors)

    def test_nettoyage_des_espaces(self):
        formulaire = self.creer_formulaire(
            depart="  Bacongo  ",
            arrivee="  Poto-Poto  ",
        )

        self.assertTrue(formulaire.is_valid(), formulaire.errors)
        self.assertEqual(formulaire.cleaned_data["depart"], "Bacongo")
        self.assertEqual(formulaire.cleaned_data["arrivee"], "Poto-Poto")

    def test_champs_internes_absents_du_formulaire(self):
        formulaire = LivraisonForm()

        self.assertEqual(
            set(formulaire.fields),
            {"service", "depart", "arrivee", "telephone"},
        )

    def test_construction_livraison_depuis_formulaire(self):
        formulaire = self.creer_formulaire()

        self.assertTrue(formulaire.is_valid(), formulaire.errors)

        livraison = formulaire.save(commit=False)

        self.assertIsNone(livraison.pk)
        self.assertEqual(livraison.service, Livraison.Service.COLIS)
        self.assertEqual(livraison.depart, "Bacongo")
        self.assertEqual(livraison.arrivee, "Poto-Poto")
        self.assertEqual(livraison.statut, Livraison.Statut.RECUE)