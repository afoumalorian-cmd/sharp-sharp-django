from django.contrib import admin
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path, reverse_lazy

from livraisons import views, views_livreur


urlpatterns = [
    path("", views.nouvelle_livraison, name="nouvelle_livraison"),
    path("confirmation/", views.confirmation_livraison, name="confirmation_livraison"),
    path(
        "livreur/connexion/",
        LoginView.as_view(
            template_name="espace_livreur.html",
            extra_context={"page_connexion": True},
            next_page=reverse_lazy("mes_courses"),
        ),
        name="connexion_livreur",
    ),
    path(
        "livreur/deconnexion/",
        LogoutView.as_view(next_page=reverse_lazy("connexion_livreur")),
        name="deconnexion_livreur",
    ),
    path("livreur/", views_livreur.mes_courses, name="mes_courses"),
    path(
        "livreur/course/<uuid:reference>/avancer/",
        views_livreur.avancer_course,
        name="avancer_course",
    ),
    path("admin/", admin.site.urls),
]