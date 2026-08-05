"""Happy-path behavior of the training endpoints."""

from datetime import date

import pytest

from training.models import (
    Exercise,
    ExerciseSlot,
    ProgramVariant,
    SetLog,
    WorkoutDay,
    WorkoutSession,
)

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


def test_starting_a_run_makes_the_program_active(client, user, enabled_profile, glute_coach):
    variant = ProgramVariant.objects.get(program=glute_coach)
    response = client.post(
        "/api/training/runs/",
        {"variant": variant.pk, "started_on": "2026-08-05"},
        format="json",
    )
    assert response.status_code == 201
    # Wednesday snaps back to its Monday: weeks are real weeks.
    assert response.json()["started_on"] == "2026-08-03"

    profile = client.get("/api/training/profile/").json()
    assert profile["active_program"] == "glute-coach"
    assert profile["active_run"] == response.json()["id"]


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
    created = client.post("/api/training/sessions/", {"day": day.pk}, format="json")
    assert created.status_code == 201
    session_id = created.json()["id"]
    # The week is taken from the day, not from the client.
    assert created.json()["week_number"] == 1

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
    # The client keys its rows by slot: the log has to say which one.
    assert body["logs"][0]["slot"] == slot.pk


def test_opening_a_day_twice_reuses_one_session(client, enabled_profile, glute_coach):
    """The duplicate-session bug: reopening a workout used to fork a new one."""
    day = WorkoutDay.objects.get(week__phase__variant__program=glute_coach)

    first = client.post("/api/training/sessions/", {"day": day.pk}, format="json")
    second = client.post("/api/training/sessions/", {"day": day.pk}, format="json")

    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]
    assert WorkoutSession.objects.filter(day=day).count() == 1


def test_day_detail_carries_the_session_already_logged_on_it(
    client, enabled_profile, glute_coach
):
    """Reopening a finished day must not render a blank form."""
    day = WorkoutDay.objects.get(week__phase__variant__program=glute_coach)
    slot = ExerciseSlot.objects.get(day=day)
    session_id = client.post(
        "/api/training/sessions/", {"day": day.pk}, format="json"
    ).json()["id"]
    client.post(
        f"/api/training/sessions/{session_id}/logs/",
        {"slot": slot.pk, "set_number": 1, "weight": "42.50", "reps": 9},
        format="json",
    )
    client.patch(
        f"/api/training/sessions/{session_id}/", {"completed": True}, format="json"
    )

    body = client.get(f"/api/training/days/{day.pk}/").json()
    assert body["session"]["id"] == session_id
    assert body["session"]["completed_at"] is not None
    assert body["session"]["logs"][0]["slot"] == slot.pk
    assert body["session"]["logs"][0]["reps"] == 9
    # No plan running: the day is outside one, and says so.
    assert body["in_active_plan"] is False
    assert body["scheduled_on"] is None


def test_day_detail_dates_the_day_when_a_plan_is_running(client, user, run):
    day = WorkoutDay.objects.get(
        week__phase__variant=run.variant, week__phase__number=1,
        week__number=1, order=3,
    )
    body = client.get(f"/api/training/days/{day.pk}/").json()

    assert body["in_active_plan"] is True
    assert body["plan_week"] == 1
    assert body["scheduled_on"] == "2026-08-05"  # the Wednesday of week 1


def test_exercise_history_is_newest_first_and_honours_limit(
    client, enabled_profile, glute_coach, session
):
    day = WorkoutDay.objects.get(week__phase__variant__program=glute_coach)
    slot = ExerciseSlot.objects.get(day=day)
    older = WorkoutSession.objects.create(
        user=session.user, day=day, week_number=1, performed_on=date(2026, 7, 20)
    )
    for target, reps in ((older, 8), (session, 10)):
        SetLog.objects.create(
            session=target, performed_exercise=slot.exercise,
            set_number=1, weight="40.00", reps=reps,
        )

    body = client.get(f"/api/training/exercises/{slot.exercise.pk}/history/").json()
    assert [s["performed_on"] for s in body["sessions"]] == ["2026-08-03", "2026-07-20"]
    assert body["sessions"][0]["sets"] == [
        {
            "set_number": 1, "weight": "40.00", "weight_basis": "total",
            "reps": 10, "was_substituted": False,
        }
    ]

    limited = client.get(
        f"/api/training/exercises/{slot.exercise.pk}/history/?limit=1"
    ).json()
    assert len(limited["sessions"]) == 1


def test_undated_imported_sessions_never_outrank_a_real_one(
    client, enabled_profile, glute_coach, session
):
    """Imported rows carry no date, and Postgres sorts NULL first in DESC —
    so without nulls_last a 2023 import would read as "última vez"."""
    day = WorkoutDay.objects.get(week__phase__variant__program=glute_coach)
    slot = ExerciseSlot.objects.get(day=day)
    imported = WorkoutSession.objects.create(
        user=session.user, day=day, week_number=1,
        performed_on=None, imported_from="male-method-1-xlsx",
    )
    recent = WorkoutSession.objects.create(
        user=session.user, day=day, week_number=1, performed_on=date(2026, 7, 20)
    )
    for target, reps in ((imported, 5), (recent, 12)):
        SetLog.objects.create(
            session=target, performed_exercise=slot.exercise, set_number=1, reps=reps
        )

    body = client.get(f"/api/training/exercises/{slot.exercise.pk}/history/").json()
    assert [s["performed_on"] for s in body["sessions"]] == ["2026-07-20", None]

    day_body = client.get(f"/api/training/days/{day.pk}/").json()
    assert day_body["slots"][0]["last_performance"]["performed_on"] == "2026-07-20"


def test_day_detail_shows_the_last_time_the_exercise_was_done(
    client, enabled_profile, glute_coach, session
):
    """"Última vez" means the previous time, so the session being edited on
    the screen is excluded — otherwise the line just mirrors what was typed."""
    day = WorkoutDay.objects.get(week__phase__variant__program=glute_coach)
    slot = ExerciseSlot.objects.get(day=day)
    older = WorkoutSession.objects.create(
        user=session.user, day=day, week_number=1, performed_on=date(2026, 7, 20)
    )
    SetLog.objects.create(
        session=older, performed_exercise=slot.exercise,
        set_number=1, weight="35.00", reps=12,
    )
    SetLog.objects.create(
        session=session, performed_exercise=slot.exercise,
        set_number=1, weight="40.00", reps=10,
    )

    body = client.get(f"/api/training/days/{day.pk}/").json()
    last = body["slots"][0]["last_performance"]
    assert body["session"]["id"] == session.pk
    assert last["performed_on"] == "2026-07-20"
    assert last["sets"][0]["weight"] == "35.00"
    assert last["sets"][0]["reps"] == 12


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
