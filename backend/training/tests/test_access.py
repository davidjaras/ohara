"""The security surface of the training module — the 5 mandatory tests.

Every denial must be a 404, never a 403: a 403 confirms the resource exists.
"""

import pytest

from training.models import (
    ExerciseSlot,
    ProgramVariant,
    SetLog,
    TrainingProfile,
    WorkoutDay,
)

pytestmark = pytest.mark.django_db


def training_endpoints(program, day, slot, session):
    return [
        "/api/training/profile/",
        "/api/training/programs/",
        f"/api/training/programs/{program.slug}/",
        f"/api/training/days/{day.pk}/",
        f"/api/training/slots/{slot.pk}/substitutions/",
        "/api/training/sessions/",
        f"/api/training/sessions/{session.pk}/",
    ]


@pytest.fixture
def endpoints(glute_coach, session):
    day = WorkoutDay.objects.get(week__phase__variant__program=glute_coach)
    slot = ExerciseSlot.objects.get(day=day)
    return training_endpoints(glute_coach, day, slot, session)


def test_user_without_training_profile_gets_404_everywhere(
    other_client, endpoints, session
):
    for url in endpoints:
        assert other_client.get(url).status_code == 404, url
    # Write operations hit the same module gate before any lookup.
    assert (
        other_client.delete(
            f"/api/training/sessions/{session.pk}/logs/999/"
        ).status_code
        == 404
    )
    assert (
        other_client.patch(
            f"/api/training/sessions/{session.pk}/", {"completed": True}, format="json"
        ).status_code
        == 404
    )


def test_user_with_disabled_profile_gets_404_everywhere(
    other_user, other_client, endpoints
):
    TrainingProfile.objects.create(user=other_user, enabled=False)
    for url in endpoints:
        assert other_client.get(url).status_code == 404, url


def test_program_without_access_is_404_by_direct_id(
    client, enabled_profile, challenge
):
    # `user` has access to Glute Coach only; Challenge 2025 must not exist
    # for them even when addressed directly.
    day = WorkoutDay.objects.get(week__phase__variant__program=challenge)
    slot = ExerciseSlot.objects.get(day=day)

    assert client.get(f"/api/training/programs/{challenge.slug}/").status_code == 404
    assert client.get(f"/api/training/days/{day.pk}/").status_code == 404
    assert client.get(f"/api/training/slots/{slot.pk}/substitutions/").status_code == 404
    # And the accessible listing never leaks it.
    slugs = [p["slug"] for p in client.get("/api/training/programs/").json()]
    assert challenge.slug not in slugs


def test_user_cannot_read_or_write_another_users_sessions_or_logs(
    other_user, other_client, session, glute_coach
):
    # Give B the module and the same program access as A: ownership, not
    # program access, is what must protect A's data.
    ProgramVariant.objects.get(program=glute_coach)
    from training.models import ProgramAccess

    TrainingProfile.objects.create(user=other_user, enabled=True)
    ProgramAccess.objects.create(user=other_user, program=glute_coach)
    slot = ExerciseSlot.objects.get(
        day__week__phase__variant__program=glute_coach
    )

    assert other_client.get(f"/api/training/sessions/{session.pk}/").status_code == 404
    response = other_client.post(
        f"/api/training/sessions/{session.pk}/logs/",
        {"slot": slot.pk, "set_number": 1, "reps": 10},
        format="json",
    )
    assert response.status_code == 404
    assert SetLog.objects.filter(session=session).count() == 0
    assert session.pk not in [
        s["id"] for s in other_client.get("/api/training/sessions/").json()
    ]

    # Nor delete A's logs or complete A's session.
    log = SetLog.objects.create(
        session=session, performed_exercise=slot.exercise, set_number=1
    )
    assert (
        other_client.delete(
            f"/api/training/sessions/{session.pk}/logs/{log.pk}/"
        ).status_code
        == 404
    )
    assert SetLog.objects.filter(pk=log.pk).exists()
    assert (
        other_client.patch(
            f"/api/training/sessions/{session.pk}/", {"completed": True}, format="json"
        ).status_code
        == 404
    )
    session.refresh_from_db()
    assert session.completed_at is None


def test_cannot_set_active_variant_of_program_without_access(
    client, user, enabled_profile, challenge
):
    foreign_variant = ProgramVariant.objects.get(program=challenge)

    response = client.put(
        "/api/training/profile/",
        {"active_variant": foreign_variant.pk},
        format="json",
    )
    assert response.status_code == 404
    user.training_profile.refresh_from_db()
    assert user.training_profile.active_variant is None
