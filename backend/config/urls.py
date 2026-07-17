"""Root routes: API, admin, auth pages and, in production, the built SPA."""

from django.contrib import admin
from django.urls import include, path, re_path
from django.views.generic import TemplateView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),
    path("api/", include("tracker.urls")),
    # SPA catch-all (frontend/dist/index.html). In development the frontend
    # runs on Vite (:5173) and this route is unused.
    re_path(
        r"^(?!api/|admin/|accounts/|static/).*$",
        TemplateView.as_view(template_name="index.html"),
    ),
]
