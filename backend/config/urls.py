"""Root routes: API under /api/ and, in production, the built SPA at /."""

from django.urls import include, path, re_path
from django.views.generic import TemplateView

urlpatterns = [
    path("api/", include("tracker.urls")),
    # SPA catch-all (frontend/dist/index.html). In development the frontend
    # runs on Vite (:5173) and this route is unused.
    re_path(r"^(?!api/|static/).*$", TemplateView.as_view(template_name="index.html")),
]
