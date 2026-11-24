from .code_remise import code_pour_livraison
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods, require_safe

from .forms import LivraisonForm
from .models import Livraison


TARIFS = {
    Livraison.Service.COLIS: 1500,
    Livraison.Service.DOCUMENTS: 1000,
}


def formater_prix(montant):
    return f"{montant:,}".replace(",", "\u202f")


@require_http_methods(["GET", "POST"])
def nouvelle_livraison(request):
    form = LivraisonForm(
        request.POST if request.method == "POST" else None,
        initial={"service": Livraison.Service.COLIS},
    )

    if request.method == "POST" and form.is_valid():
        # Le serveur fixe le tarif avant d’enregistrer la commande.
        livraison = form.save(commit=False)
        livraison.prix_fcfa = TARIFS[livraison.service]
        livraison.save()

        request.session["derniere_livraison"] = {
            "reference": str(livraison.reference),
        }
        return redirect("confirmation_livraison")

    services = [
        (valeur, libelle, formater_prix(TARIFS[valeur]))
        for valeur, libelle in Livraison.Service.choices
    ]
    return render(
        request,
        "nouvelle_livraison.html",
        {"form": form, "services": services},
    )


@never_cache
@require_safe
def confirmation_livraison(request):
    derniere_livraison = request.session.get("derniere_livraison", {})
    reference = derniere_livraison.get("reference")
    if not reference:
        return redirect("nouvelle_livraison")

    # Relit le statut en base à chaque actualisation du suivi.
    livraison = Livraison.objects.filter(reference=reference).first()
    if livraison is None:
        request.session.pop("derniere_livraison", None)
        return redirect("nouvelle_livraison")

    return render(
        request,
        "suivi_livraison.html",
        {
            "livraison": livraison,
            "prix_fcfa": formater_prix(livraison.prix_fcfa),
            "code_remise": (
                code_pour_livraison(livraison.reference)
                if livraison.statut == Livraison.Statut.EN_LIVRAISON
                else ""
            ),
        },
    )