import re
from hmac import compare_digest

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import F
from django.http import Http404
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST, require_safe

from .code_remise import code_pour_livraison
from .models import Livraison, Livreur


MAX_TENTATIVES = 5

ETAPES_SUIVANTES = {
    Livraison.Statut.AFFECTEE: (
        Livraison.Statut.RECUPEREE,
        "Confirmer la récupération",
    ),
    Livraison.Statut.RECUPEREE: (
        Livraison.Statut.EN_LIVRAISON,
        "Démarrer la livraison",
    ),
    Livraison.Statut.EN_LIVRAISON: (
        Livraison.Statut.LIVREE,
        "Confirmer la remise",
    ),
}


def courses_du_livreur(utilisateur):
    if not Livreur.objects.filter(compte=utilisateur).exists():
        raise PermissionDenied("Ce compte n’est associé à aucun livreur.")

    return Livraison.objects.filter(livreur__compte=utilisateur)


@never_cache
@login_required(login_url="connexion_livreur")
@require_safe
def mes_courses(request):
    livraisons = courses_du_livreur(request.user).order_by("-creee_le")
    courses = []

    for livraison in livraisons:
        remise = livraison.statut == Livraison.Statut.EN_LIVRAISON
        remise_bloquee = (
            remise and livraison.tentatives_code_remise >= MAX_TENTATIVES
        )
        courses.append({
            "livraison": livraison,
            "action": ETAPES_SUIVANTES.get(livraison.statut),
            "remise": remise,
            "remise_bloquee": remise_bloquee,
        })

    return render(request, "espace_livreur.html", {"courses": courses})


@never_cache
@login_required(login_url="connexion_livreur")
@require_POST
def avancer_course(request, reference):
    courses = courses_du_livreur(request.user).filter(reference=reference)
    if not courses.exists():
        raise Http404("Course introuvable.")

    statut_attendu = request.POST.get("statut_attendu")
    etape = ETAPES_SUIVANTES.get(statut_attendu)
    if etape is None:
        messages.warning(request, "Cette action n’est plus disponible.")
        return redirect("mes_courses")

    # Vérifie le statut et l’affectation au moment de l’écriture.
    course = courses.filter(statut=statut_attendu)

    if statut_attendu == Livraison.Statut.EN_LIVRAISON:
        code_saisi = request.POST.get("code_remise", "").strip()
        if not re.fullmatch(r"[0-9]{6}", code_saisi):
            messages.warning(request, "Saisis le code de remise à six chiffres.")
            return redirect("mes_courses")

        course = course.filter(tentatives_code_remise__lt=MAX_TENTATIVES)

        if not compare_digest(code_saisi, code_pour_livraison(reference)):
            tentative_comptee = course.update(
                tentatives_code_remise=F("tentatives_code_remise") + 1,
            )
            if tentative_comptee:
                messages.error(request, "Code de remise incorrect.")
            else:
                messages.warning(
                    request,
                    "La course a changé ou la validation est bloquée.",
                )
            return redirect("mes_courses")

    if course.update(statut=etape[0]):
        messages.success(request, "Le statut de la course a été mis à jour.")
    else:
        messages.warning(request, "La course a changé ou la validation est bloquée.")

    return redirect("mes_courses")