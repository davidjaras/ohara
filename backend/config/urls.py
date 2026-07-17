"""Rutas raíz: API bajo /api/ y, en producción, la SPA compilada en /."""

from django.urls import include, path, re_path
from django.views.generic import TemplateView

urlpatterns = [
    path("api/", include("tracker.urls")),
    # Catch-all para la SPA (frontend/dist/index.html). En desarrollo el
    # frontend corre en Vite (:5173) y esta ruta no se usa.
    re_path(r"^(?!api/|static/).*$", TemplateView.as_view(template_name="index.html")),
]
