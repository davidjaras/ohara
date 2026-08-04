"""The ProgramAccess admin grants several programs in one save."""

import pytest
from django.test import Client

from training.models import ProgramAccess

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin_client(django_user_model) -> Client:
    django_user_model.objects.create_superuser(username="root", password="pw12345")
    admin = Client()
    admin.login(username="root", password="pw12345")
    return admin


def test_add_view_grants_multiple_programs_at_once(
    admin_client, user, glute_coach, challenge
):
    response = admin_client.post(
        "/admin/training/programaccess/add/",
        {"user": user.pk, "programs": [glute_coach.pk, challenge.pk]},
    )
    assert response.status_code == 302
    granted = ProgramAccess.objects.filter(user=user)
    assert {a.program.slug for a in granted} == {"glute-coach", "challenge-2025"}


def test_add_view_regrant_does_not_duplicate(admin_client, user, glute_coach):
    ProgramAccess.objects.create(user=user, program=glute_coach)
    response = admin_client.post(
        "/admin/training/programaccess/add/",
        {"user": user.pk, "programs": [glute_coach.pk]},
    )
    assert response.status_code == 302
    assert ProgramAccess.objects.filter(user=user, program=glute_coach).count() == 1
