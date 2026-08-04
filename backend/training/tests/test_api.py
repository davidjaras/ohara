"""Happy-path behavior of the training endpoints."""

import pytest

from training.models import ExerciseSlot, Exercise, ProgramVariant, SetLog, WorkoutDay

pytestmark = pytest.mark.django_db


def test_program_navigation_reaches_day_and_sets(client, enabled_profile, glute_coach):
    programs = client.get("/api/training/programs/").json()
    assert [p["slug"] for p in programs] == ["glute-coach"]

    detail = client.get(f"/api/training/programs/{glute_coach.slug}/").json()
    day_id = detail["variants"][0]["phases"][0]["weeks"][0]["days"][0]["id"]

    day = client.get(f"/api/training/days/{day_id}/").json()
    slot = day["slots"][0]
    assert slot["exercise"]["name"] == "glute-coach squat"
    assert slot["sets"][0]["target_reps_min"] == 8
    assert slot["sets"][0]["rest_role"] == "between_sets"


def test_set_active_variant_of_accessible_program(client, user, enabled_profile, glute_coach):
    variant = ProgramVariant.objects.get(program=glute_coach)
    response = client.put(
        "/api/training/profile/", {"active_variant": variant.pk}, format="json"
    )
    assert response.status_code == 200
    assert response.json()["active_program"] == "glute-coach"


def test_substitution_picker_groups_by_setting_and_logs_substituted(
    client, enabled_profile, glute_coach, session
):
    slot = ExerciseSlot.objects.get(day__week__phase__variant__program=glute_coach)
    home = Exercise.objects.create(
        slug="db-lunge", name="DB Lunge", primary_muscle="quads", setting="home"
    )
    Exercise.objects.create(
        slug="leg-press", name="Leg Press", primary_muscle="quads", setting="gym"
    )
    Exercise.objects.create(  # different muscle: must not appear
        slug="curl", name="Curl", primary_muscle="biceps", setting="home"
    )

    picker = client.get(f"/api/training/slots/{slot.pk}/substitutions/").json()
    assert [e["slug"] for e in picker["home"]] == ["db-lunge"]
    assert [e["slug"] for e in picker["gym"]] == ["leg-press"]

    created = client.post(
        f"/api/training/slots/{slot.pk}/substitutions/",
        {"replacement": home.pk, "scope": "program"},
        format="json",
    )
    assert created.status_code == 201

    log = client.post(
        f"/api/training/sessions/{session.pk}/logs/",
        {"slot": slot.pk, "set_number": 1, "weight": "20.00", "reps": 9},
        format="json",
    )
    assert log.status_code == 201
    assert log.json()["performed_exercise"] == "DB Lunge"
    assert log.json()["was_substituted"] is True


def test_create_session_and_log_against_prescription(client, enabled_profile, glute_coach):
    day = WorkoutDay.objects.get(week__phase__variant__program=glute_coach)
    created = client.post(
        "/api/training/sessions/",
        {"day": day.pk, "week_number": 1},
        format="json",
    )
    assert created.status_code == 201
    session_id = created.json()["id"]

    slot = ExerciseSlot.objects.get(day=day)
    log = client.post(
        f"/api/training/sessions/{session_id}/logs/",
        {"slot": slot.pk, "set_number": 1, "weight": "60.00", "reps": 10},
        format="json",
    )
    assert log.status_code == 201
    body = client.get(f"/api/training/sessions/{session_id}/").json()
    assert len(body["logs"]) == 1
    assert body["logs"][0]["prescription"] is not None


def test_unlog_set_deletes_the_log(client, enabled_profile, glute_coach, session):
    slot = ExerciseSlot.objects.get(day__week__phase__variant__program=glute_coach)
    log_id = client.post(
        f"/api/training/sessions/{session.pk}/logs/",
        {"slot": slot.pk, "set_number": 1, "reps": 10},
        format="json",
    ).json()["id"]

    response = client.delete(f"/api/training/sessions/{session.pk}/logs/{log_id}/")
    assert response.status_code == 204
    assert not SetLog.objects.filter(pk=log_id).exists()
    # A second delete of the same log no longer finds it.
    assert (
        client.delete(f"/api/training/sessions/{session.pk}/logs/{log_id}/").status_code
        == 404
    )


def test_complete_and_uncomplete_session(client, enabled_profile, session):
    assert session.completed_at is None

    body = client.patch(
        f"/api/training/sessions/{session.pk}/", {"completed": True}, format="json"
    ).json()
    assert body["completed_at"] is not None

    body = client.patch(
        f"/api/training/sessions/{session.pk}/", {"completed": False}, format="json"
    ).json()
    assert body["completed_at"] is None


def test_patch_session_notes(client, enabled_profile, session):
    body = client.patch(
        f"/api/training/sessions/{session.pk}/", {"notes": "felt strong"}, format="json"
    ).json()
    assert body["notes"] == "felt strong"
