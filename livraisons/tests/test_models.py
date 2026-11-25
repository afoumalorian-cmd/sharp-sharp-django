from django.core.exceptions import ValidationError
from django.db.models.deletion import ProtectedError
from django.test import TestCase

from livraisons.models import Livraison, Livreur


class LivreurModelTests(TestCase):
    """Tests du modèle Livreur."""

    def test_creation_livreur(self):
        livreur = Livreur.objects.create(nom="Livreur Test")

        self.assertIsNotNone(livreur.pk)
        self.assertEqual(livreur.nom, "Livreur Test")

    def test_representation_livreur(self):
        livreur = Livreur(nom="Livreur Test")

        self.assertEqual(str(livreur), "Livreur Test")


class LivraisonModelTests(TestCase):
    """Tests des modèles et des règles métier des livraisons."""

    @classmethod
    def setUpTestData(cls):
        cls.livreur = Livreur.objects.create(
            nom="Livreur Test"
        )

    def creer_livraison(self, **modifications):
        """Crée une livraison fictive avec des valeurs par défaut."""
        donnees = {
            "service": Livraison.Service.COLIS,
            "depart": "Bacongo",
            "arrivee": "Poto-Poto",
            "telephone": "060000000",
            "prix_fcfa": 1500,
            **modifications,
        }

        return Livraison.objects.create(**donnees)

    def test_creation_livraison(self):
        livraison = self.creer_livraison()

        self.assertIsNotNone(livraison.pk)
        self.assertEqual(livraison.depart, "Bacongo")
        self.assertEqual(livraison.arrivee, "Poto-Poto")
        self.assertEqual(livraison.prix_fcfa, 1500)

    def test_statut_initial(self):
        livraison = self.creer_livraison()

        self.assertEqual(
            livraison.statut,
            Livraison.Statut.RECUE,
        )

    def test_reference_unique(self):
        premiere = self.creer_livraison()
        seconde = self.creer_livraison()

        self.assertNotEqual(
            premiere.reference,
            seconde.reference,
        )

    def test_representation_livraison(self):
        livraison = self.creer_livraison()

        self.assertEqual(
            str(livraison),
            str(livraison.reference),
        )

    def test_date_creation(self):
        livraison = self.creer_livraison()

        self.assertIsNotNone(livraison.creee_le)

    def test_compteur_code_initial(self):
        livraison = self.creer_livraison()

        self.assertEqual(
            livraison.tentatives_code_remise,
            0,
        )

    def test_absence_incident_initial(self):
        livraison = self.creer_livraison()

        self.assertEqual(livraison.motif_incident, "")
        self.assertIsNone(livraison.incident_signale_le)

    def test_commande_recue_sans_livreur_valide(self):
        livraison = self.creer_livraison()

        livraison.full_clean()

        self.assertIsNone(livraison.livreur)

    def test_commande_recue_avec_livreur_invalide(self):
        livraison = self.creer_livraison(
            livreur=self.livreur,
        )

        with self.assertRaises(ValidationError) as erreur:
            livraison.full_clean()

        self.assertIn(
            "statut",
            erreur.exception.message_dict,
        )

    def test_affectation_sans_livreur_invalide(self):
        livraison = self.creer_livraison(
            statut=Livraison.Statut.AFFECTEE,
        )

        with self.assertRaises(ValidationError) as erreur:
            livraison.full_clean()

        self.assertIn(
            "livreur",
            erreur.exception.message_dict,
        )

    def test_affectation_avec_livreur_valide(self):
        livraison = self.creer_livraison(
            statut=Livraison.Statut.AFFECTEE,
            livreur=self.livreur,
        )

        livraison.full_clean()

        self.assertEqual(
            livraison.livreur,
            self.livreur,
        )

    def test_telephone_invalide(self):
        livraison = self.creer_livraison(
            telephone="123",
        )

        with self.assertRaises(ValidationError) as erreur:
            livraison.full_clean()

        self.assertIn(
            "telephone",
            erreur.exception.message_dict,
        )

    def test_incident_sans_motif_invalide(self):
        livraison = self.creer_livraison(
            statut=Livraison.Statut.INCIDENT,
            livreur=self.livreur,
        )

        with self.assertRaises(ValidationError) as erreur:
            livraison.full_clean()

        self.assertIn(
            "statut",
            erreur.exception.message_dict,
        )

    def test_incident_avec_motif_valide(self):
        livraison = self.creer_livraison(
            statut=Livraison.Statut.INCIDENT,
            livreur=self.livreur,
            motif_incident=Livraison.MotifIncident.ABSENT,
        )

        livraison.full_clean()

        self.assertEqual(
            livraison.motif_incident,
            Livraison.MotifIncident.ABSENT,
        )

    def test_motif_code_incorrect(self):
        livraison = self.creer_livraison(
            statut=Livraison.Statut.INCIDENT,
            livreur=self.livreur,
            motif_incident=Livraison.MotifIncident.CODE_INCORRECT,
        )

        livraison.full_clean()

        self.assertEqual(
            livraison.get_motif_incident_display(),
            "Code de livraison incorrect",
        )

    def test_suppression_livreur_affecte_interdite(self):
        self.creer_livraison(
            statut=Livraison.Statut.AFFECTEE,
            livreur=self.livreur,
        )

        with self.assertRaises(ProtectedError):
            self.livreur.delete()