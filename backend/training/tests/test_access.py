"""The security surface of the training module — the 5 mandatory tests.

Every denial must be a 404, never a 403: a 403 confirms the resource exists.
"""

import pytest

from training.models import (
    ExerciseSlot,
    ProgramAccess,
    ProgramRun,
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
        "/api/training/runs/",
        "/api/training/runs/active/",
        f"/api/training/exercises/{slot.exercise.pk}/history/",
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


def test_cannot_start_a_run_on_a_program_without_access(
    client, user, enabled_profile, challenge
):
    foreign_variant = ProgramVariant.objects.get(program=challenge)

    response = client.post(
        "/api/training/runs/",
        {"variant": foreign_variant.pk},
        format="json",
    )
    assert response.status_code == 404
    assert not ProgramRun.objects.filter(user=user).exists()


def test_user_cannot_read_another_users_runs(
    client, other_client, other_user, run, glute_coach
):
    """B has the module and even the same program access; the run is still A's."""
    TrainingProfile.objects.create(user=other_user, enabled=True)
    ProgramAccess.objects.create(user=other_user, program=glute_coach)

    assert other_client.get(f"/api/training/runs/{run.pk}/").status_code == 404
    assert (
        other_client.patch(
            f"/api/training/runs/{run.pk}/", {"status": "abandoned"}, format="json"
        ).status_code
        == 404
    )
    run.refresh_from_db()
    assert run.status == "active"

    assert other_client.get("/api/training/runs/").json() == []
    assert other_client.get("/api/training/runs/active/").status_code == 204


def test_exercise_history_never_shows_another_users_logs(
    client, other_client, other_user, glute_coach, session
):
    """The catalogue is global; what was lifted on it is not."""
    TrainingProfile.objects.create(user=other_user, enabled=True)
    ProgramAccess.objects.create(user=other_user, program=glute_coach)
    slot = ExerciseSlot.objects.get(day__week__phase__variant__program=glute_coach)
    SetLog.objects.create(
        session=session, performed_exercise=slot.exercise, set_number=1, reps=10
    )

    mine = client.get(f"/api/training/exercises/{slot.exercise.pk}/history/").json()
    assert len(mine["sessions"]) == 1

    theirs = other_client.get(
        f"/api/training/exercises/{slot.exercise.pk}/history/"
    ).json()
    assert theirs["sessions"] == []
