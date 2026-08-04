from rest_framework.exceptions import NotFound
from rest_framework.permissions import BasePermission


class TrainingEnabled(BasePermission):
    """Layer 1 of access control: the module gate.

    Raises 404 — not 403 — when the profile is missing or disabled: for
    someone without the module enabled, training does not exist, and a 403
    would confirm that it does.
    """

    def has_permission(self, request, view):
        profile = getattr(request.user, "training_profile", None)
        if profile is None or not profile.enabled:
            raise NotFound
        return True
