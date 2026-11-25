from django.test import TestCase
from django.urls import reverse

from livraisons.models import Livraison


class CommandesTests(TestCase):
    """Tests fonctionnels de création des commandes client."""

    def setUp(self):
        self.url = reverse("nouvelle_livraison")

        self.donnees_valides = {
            "service": Livraison.Service.COLIS,
            "depart": "Moungali",
            "arrivee": "Ouenze",
            "telephone": "+242060000000",
        }

    def commander(self, **modifications):
        """Envoie une demande de livraison avec des données fictives."""
        return self.client.post(
            self.url,
            {
                **self.donnees_valides,
                **modifications,
            },
        )

    def test_page_commande_accessible(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

        self.assertTemplateUsed(
            response,
            "nouvelle_livraison.html",
        )

    def test_formulaire_disponible(self):
        response = self.client.get(self.url)

        self.assertIn("form", response.context)
        self.assertIn("services", response.context)

    def test_service_initial_colis(self):
        response = self.client.get(self.url)

        self.assertEqual(
            response.context["form"].initial["service"],
            Livraison.Service.COLIS,
        )

    def test_consultation_page_sans_creation(self):
        self.client.get(self.url)

        self.assertEqual(Livraison.objects.count(), 0)

    def test_creation_commande_colis(self):
        self.commander()

        self.assertEqual(Livraison.objects.count(), 1)

        livraison = Livraison.objects.get()

        self.assertEqual(
            livraison.service,
            Livraison.Service.COLIS,
        )

        self.assertEqual(livraison.depart, "Moungali")
        self.assertEqual(livraison.arrivee, "Ouenze")
        self.assertEqual(livraison.telephone, "+242060000000")

    def test_creation_commande_documents(self):
        self.commander(
            service=Livraison.Service.DOCUMENTS,
        )

        livraison = Livraison.objects.get()

        self.assertEqual(
            livraison.service,
            Livraison.Service.DOCUMENTS,
        )

    def test_tarif_colis(self):
        self.commander(
            service=Livraison.Service.COLIS,
        )

        livraison = Livraison.objects.get()

        self.assertEqual(livraison.prix_fcfa, 1500)

    def test_tarif_documents(self):
        self.commander(
            service=Livraison.Service.DOCUMENTS,
        )

        livraison = Livraison.objects.get()

        self.assertEqual(livraison.prix_fcfa, 1000)

    def test_tarif_calcule_par_serveur(self):
        # Vérifie que le montant appliqué provient de la grille
        # tarifaire du serveur.
        self.commander()

        livraison = Livraison.objects.get()

        self.assertEqual(livraison.prix_fcfa, 1500)

    def test_statut_initial_commande(self):
        self.commander()

        livraison = Livraison.objects.get()

        self.assertEqual(
            livraison.statut,
            Livraison.Statut.RECUE,
        )

    def test_commande_initialement_sans_livreur(self):
        self.commander()

        livraison = Livraison.objects.get()

        self.assertIsNone(livraison.livreur)

    def test_compteur_code_initial(self):
        self.commander()

        livraison = Livraison.objects.get()

        self.assertEqual(
            livraison.tentatives_code_remise,
            0,
        )

    def test_redirection_apres_commande(self):
        response = self.commander()

        self.assertRedirects(
            response,
            reverse("confirmation_livraison"),
        )

    def test_reference_conservee_en_session(self):
        self.commander()

        livraison = Livraison.objects.get()

        session = self.client.session

        self.assertIn(
            "derniere_livraison",
            session,
        )

        self.assertEqual(
            session["derniere_livraison"]["reference"],
            str(livraison.reference),
        )

    def test_commande_invalide_non_enregistree(self):
        response = self.commander(depart="")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Livraison.objects.count(), 0)

        self.assertIn(
            "depart",
            response.context["form"].errors,
        )

    def test_telephone_invalide_non_enregistre(self):
        response = self.commander(telephone="123")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Livraison.objects.count(), 0)

        self.assertIn(
            "telephone",
            response.context["form"].errors,
        )

    def test_service_invalide_non_enregistre(self):
        response = self.commander(
            service="service_inconnu",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Livraison.objects.count(), 0)

        self.assertIn(
            "service",
            response.context["form"].errors,
        )

    def test_creation_plusieurs_commandes(self):
        self.commander()

        self.commander(
            service=Livraison.Service.DOCUMENTS,
            depart="Bacongo",
            arrivee="Poto-Poto",
        )

        self.assertEqual(Livraison.objects.count(), 2)

        references = list(
            Livraison.objects.values_list(
                "reference",
                flat=True,
            )
        )

        self.assertEqual(len(set(references)), 2)

    def test_session_actualisee_apres_nouvelle_commande(self):
        self.commander()

        premiere_reference = Livraison.objects.get().reference

        self.commander(
            service=Livraison.Service.DOCUMENTS,
        )

        seconde = Livraison.objects.exclude(
            reference=premiere_reference,
        ).get()

        self.assertEqual(
            self.client.session["derniere_livraison"]["reference"],
            str(seconde.reference),
        )

    def test_actualisation_confirmation_sans_doublon(self):
        self.commander()

        url_confirmation = reverse("confirmation_livraison")

        self.client.get(url_confirmation)
        self.client.get(url_confirmation)

        self.assertEqual(Livraison.objects.count(), 1)