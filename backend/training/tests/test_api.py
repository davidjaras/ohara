"""Happy-path behavior of the training endpoints."""

from datetime import date

import pytest

from training.models import (
    Exercise,
    ExerciseSlot,
    ProgramAccess,
    ProgramVariant,
    SetLog,
    WorkoutDay,
    WorkoutSession,
)

from .conftest import build_program, slot_at

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


def test_session_scoped_substitution_does_not_leak_into_another_session(
    client, enabled_profile, glute_coach, session
):
    """"Solo esta sesión" used to apply forever: scope was stored and then
    ignored when resolving, so one swap renamed the slot in every session."""
    slot = ExerciseSlot.objects.get(day__week__phase__variant__program=glute_coach)
    replacement = Exercise.objects.create(
        slug="db-lunge", name="DB Lunge", primary_muscle="quads", setting="home"
    )
    client.post(
        f"/api/training/slots/{slot.pk}/substitutions/",
        {"replacement": replacement.pk, "scope": "session", "session": session.pk},
        format="json",
    )

    inside = client.post(
        f"/api/training/sessions/{session.pk}/logs/",
        {"slot": slot.pk, "set_number": 1, "reps": 10},
        format="json",
    ).json()
    assert inside["performed_exercise"] == "DB Lunge"
    assert inside["was_substituted"] is True

    other = WorkoutSession.objects.create(
        user=session.user, day=slot.day, week_number=1, performed_on=date(2026, 8, 10)
    )
    outside = client.post(
        f"/api/training/sessions/{other.pk}/logs/",
        {"slot": slot.pk, "set_number": 1, "reps": 10},
        format="json",
    ).json()
    assert outside["performed_exercise"] == slot.exercise.name
    assert outside["was_substituted"] is False


def test_session_scoped_substitution_opens_the_session_it_needs(
    client, enabled_profile, glute_coach
):
    """Swapping before logging the first set is the normal order, so "solo
    esta sesión" with no session must not write a row scoped to nothing."""
    slot = ExerciseSlot.objects.get(day__week__phase__variant__program=glute_coach)
    replacement = Exercise.objects.create(
        slug="db-lunge", name="DB Lunge", primary_muscle="quads", setting="home"
    )
    assert not WorkoutSession.objects.filter(day=slot.day).exists()

    created = client.post(
        f"/api/training/slots/{slot.pk}/substitutions/",
        {"replacement": replacement.pk, "scope": "session"},
        format="json",
    )
    assert created.status_code == 201
    session = WorkoutSession.objects.get(day=slot.day)
    assert created.json()["session"] == session.pk

    # And it is actually in force: the day is titled by the substitute and a
    # logged set records it.
    body = client.get(f"/api/training/days/{slot.day_id}/").json()
    assert body["slots"][0]["substitution"]["replacement"]["name"] == "DB Lunge"
    log = client.post(
        f"/api/training/sessions/{session.pk}/logs/",
        {"slot": slot.pk, "set_number": 1, "reps": 10},
        format="json",
    ).json()
    assert log["performed_exercise"] == "DB Lunge"


def test_program_scoped_substitution_applies_to_every_session(
    client, enabled_profile, glute_coach, session
):
    slot = ExerciseSlot.objects.get(day__week__phase__variant__program=glute_coach)
    replacement = Exercise.objects.create(
        slug="db-lunge", name="DB Lunge", primary_muscle="quads", setting="home"
    )
    client.post(
        f"/api/training/slots/{slot.pk}/substitutions/",
        {"replacement": replacement.pk, "scope": "program"},
        format="json",
    )

    other = WorkoutSession.objects.create(
        user=session.user, day=slot.day, week_number=1, performed_on=date(2026, 8, 10)
    )
    for target in (session, other):
        body = client.post(
            f"/api/training/sessions/{target.pk}/logs/",
            {"slot": slot.pk, "set_number": 1, "reps": 10},
            format="json",
        ).json()
        assert body["performed_exercise"] == "DB Lunge"


def test_program_scoped_substitution_follows_the_slot_into_the_next_week(
    client, enabled_profile, multiweek_access
):
    """The bug this fixture exists for.

    A slot is per-week, so week 2 is a different row. Resolution used to be
    gated on the slot id, which made "todo el programa" mean "every session of
    this one week" — week after week the prescription came back.
    """
    first = slot_at(multiweek_access, phase=1, week=1)
    replacement = Exercise.objects.create(
        slug="db-lunge", name="DB Lunge", primary_muscle="quads", setting="home"
    )
    created = client.post(
        f"/api/training/slots/{first.pk}/substitutions/",
        {"replacement": replacement.pk, "scope": "program"},
        format="json",
    )
    assert created.status_code == 201

    for week in (1, 2, 3):
        slot = slot_at(multiweek_access, phase=1, week=week)
        body = client.get(f"/api/training/days/{slot.day_id}/").json()["slots"][0]
        assert body["substitution"]["replacement"]["name"] == "DB Lunge"
        # The prescription stays visible underneath: it is what "en lugar de"
        # reads, and on a later week it is not reachable through `slot`.
        assert body["substitution"]["original_exercise"]["name"] == first.exercise.name
        assert body["exercise"]["name"] == first.exercise.name


def test_program_scoped_substitution_stops_where_the_prescription_changes(
    client, enabled_profile, multiweek_access
):
    """Phase 2 reuses day 1 / slot 1 for a different lift. Matching on position
    alone would silently replace an exercise the user never touched."""
    first = slot_at(multiweek_access, phase=1, week=1)
    later = slot_at(multiweek_access, phase=2, week=1)
    assert first.exercise_id != later.exercise_id  # the fixture's whole point

    replacement = Exercise.objects.create(
        slug="db-lunge", name="DB Lunge", primary_muscle="quads", setting="home"
    )
    client.post(
        f"/api/training/slots/{first.pk}/substitutions/",
        {"replacement": replacement.pk, "scope": "program"},
        format="json",
    )

    body = client.get(f"/api/training/days/{later.day_id}/").json()["slots"][0]
    assert body["substitution"] is None
    assert body["exercise"]["name"] == later.exercise.name


def test_program_scoped_substitution_reaches_a_later_phase_prescribing_the_same(
    client, user, enabled_profile
):
    """The other half of the rule: where the program does prescribe the same
    exercise at the same position, the swap follows across the phase too."""
    program = build_program("challenge-3", phases=2, weeks=2)
    ProgramAccess.objects.create(user=user, program=program)
    first = slot_at(program, phase=1, week=1)
    later = slot_at(program, phase=2, week=2)
    assert first.exercise_id == later.exercise_id

    replacement = Exercise.objects.create(
        slug="db-lunge", name="DB Lunge", primary_muscle="quads", setting="home"
    )
    client.post(
        f"/api/training/slots/{first.pk}/substitutions/",
        {"replacement": replacement.pk, "scope": "program"},
        format="json",
    )

    body = client.get(f"/api/training/days/{later.day_id}/").json()["slots"][0]
    assert body["substitution"]["replacement"]["name"] == "DB Lunge"


def test_session_scoped_substitution_does_not_reach_the_next_week(
    client, enabled_profile, multiweek_access
):
    """Widening the program scope must not widen the session one: a one-off
    stays one-off, which is the promise of "solo esta sesión"."""
    first = slot_at(multiweek_access, phase=1, week=1)
    second = slot_at(multiweek_access, phase=1, week=2)
    replacement = Exercise.objects.create(
        slug="db-lunge", name="DB Lunge", primary_muscle="quads", setting="home"
    )
    created = client.post(
        f"/api/training/slots/{first.pk}/substitutions/",
        {"replacement": replacement.pk, "scope": "session"},
        format="json",
    )
    assert created.status_code == 201

    body = client.get(f"/api/training/days/{second.day_id}/").json()["slots"][0]
    assert body["substitution"] is None

    session = WorkoutSession.objects.create(
        user=enabled_profile.user, day=second.day, week_number=2,
        performed_on=date(2026, 8, 10),
    )
    log = client.post(
        f"/api/training/sessions/{session.pk}/logs/",
        {"slot": second.pk, "set_number": 1, "reps": 10},
        format="json",
    ).json()
    assert log["performed_exercise"] == second.exercise.name
    assert log["was_substituted"] is False


def test_reverting_a_substitution_restores_the_prescription_everywhere(
    client, enabled_profile, multiweek_access
):
    first = slot_at(multiweek_access, phase=1, week=1)
    second = slot_at(multiweek_access, phase=1, week=2)
    replacement = Exercise.objects.create(
        slug="db-lunge", name="DB Lunge", primary_muscle="quads", setting="home"
    )
    client.post(
        f"/api/training/slots/{first.pk}/substitutions/",
        {"replacement": replacement.pk, "scope": "program"},
        format="json",
    )

    # Undone from week 2, where the row does not even live: what you revert is
    # what you were looking at.
    assert client.delete(
        f"/api/training/slots/{second.pk}/substitutions/"
    ).status_code == 204
    for slot in (first, second):
        body = client.get(f"/api/training/days/{slot.day_id}/").json()["slots"][0]
        assert body["substitution"] is None
    # Nothing left in force.
    assert client.delete(
        f"/api/training/slots/{first.pk}/substitutions/"
    ).status_code == 404


def test_reverting_a_session_swap_uncovers_the_program_one(
    client, enabled_profile, multiweek_access
):
    """Both scopes can be in force at once. Undoing the one-off must leave the
    standing swap standing, not wipe both."""
    slot = slot_at(multiweek_access, phase=1, week=1)
    standing = Exercise.objects.create(
        slug="db-lunge", name="DB Lunge", primary_muscle="quads", setting="home"
    )
    one_off = Exercise.objects.create(
        slug="leg-press", name="Leg Press", primary_muscle="quads", setting="gym"
    )
    client.post(
        f"/api/training/slots/{slot.pk}/substitutions/",
        {"replacement": standing.pk, "scope": "program"},
        format="json",
    )
    created = client.post(
        f"/api/training/slots/{slot.pk}/substitutions/",
        {"replacement": one_off.pk, "scope": "session"},
        format="json",
    )
    session_id = created.json()["session"]

    url = f"/api/training/slots/{slot.pk}/substitutions/"
    assert client.get(f"{url}?session={session_id}").json()["active"]["replacement"][
        "name"
    ] == "Leg Press"
    assert client.delete(f"{url}?session={session_id}").status_code == 204
    assert client.get(f"{url}?session={session_id}").json()["active"]["replacement"][
        "name"
    ] == "DB Lunge"


def test_another_user_cannot_revert_a_substitution(
    client, other_client, enabled_profile, multiweek_access
):
    slot = slot_at(multiweek_access, phase=1, week=1)
    replacement = Exercise.objects.create(
        slug="db-lunge", name="DB Lunge", primary_muscle="quads", setting="home"
    )
    client.post(
        f"/api/training/slots/{slot.pk}/substitutions/",
        {"replacement": replacement.pk, "scope": "program"},
        format="json",
    )

    # No access to the program at all, so the slot itself is invisible.
    assert other_client.delete(
        f"/api/training/slots/{slot.pk}/substitutions/"
    ).status_code in (403, 404)
    assert (
        client.get(f"/api/training/days/{slot.day_id}/").json()["slots"][0][
            "substitution"
        ]
        is not None
    )


def test_last_performed_exercise_reports_what_you_actually_did_here(
    client, user, enabled_profile, multiweek_access
):
    """The hint for the swap you never recorded: a one-off you then repeated.
    It reads the position, so last week's log reaches this week's card."""
    first = slot_at(multiweek_access, phase=1, week=1)
    second = slot_at(multiweek_access, phase=1, week=2)
    replacement = Exercise.objects.create(
        slug="db-lunge", name="DB Lunge", primary_muscle="quads", setting="home"
    )
    session = WorkoutSession.objects.create(
        user=user, day=first.day, week_number=1, performed_on=date(2026, 8, 3)
    )
    client.post(
        f"/api/training/slots/{first.pk}/substitutions/",
        {"replacement": replacement.pk, "scope": "session", "session": session.pk},
        format="json",
    )
    client.post(
        f"/api/training/sessions/{session.pk}/logs/",
        {"slot": first.pk, "set_number": 1, "reps": 10},
        format="json",
    )

    body = client.get(f"/api/training/days/{second.day_id}/").json()["slots"][0]
    assert body["substitution"] is None  # the one-off correctly did not follow
    assert body["last_performed_exercise"]["exercise"]["name"] == "DB Lunge"
    assert body["last_performed_exercise"]["performed_on"] == "2026-08-03"


def test_last_performed_exercise_is_silent_when_it_agrees_with_the_card(
    client, user, enabled_profile, multiweek_access
):
    first = slot_at(multiweek_access, phase=1, week=1)
    second = slot_at(multiweek_access, phase=1, week=2)
    session = WorkoutSession.objects.create(
        user=user, day=first.day, week_number=1, performed_on=date(2026, 8, 3)
    )
    client.post(
        f"/api/training/sessions/{session.pk}/logs/",
        {"slot": first.pk, "set_number": 1, "reps": 10},
        format="json",
    )

    body = client.get(f"/api/training/days/{second.day_id}/").json()["slots"][0]
    assert body["last_performed_exercise"] is None


def test_day_detail_carries_the_substitution_and_the_substitutes_history(
    client, enabled_profile, glute_coach, session
):
    """The card is titled by the substitute, so the day has to say there is
    one — and "última vez" has to follow the substitute, not the prescription."""
    slot = ExerciseSlot.objects.get(day__week__phase__variant__program=glute_coach)
    replacement = Exercise.objects.create(
        slug="db-lunge", name="DB Lunge", primary_muscle="quads", setting="home"
    )
    client.post(
        f"/api/training/slots/{slot.pk}/substitutions/",
        {"replacement": replacement.pk, "scope": "program"},
        format="json",
    )
    older = WorkoutSession.objects.create(
        user=session.user, day=slot.day, week_number=1, performed_on=date(2026, 7, 20)
    )
    SetLog.objects.create(
        session=older, performed_exercise=replacement,
        set_number=1, weight="30.00", reps=11,
    )
    SetLog.objects.create(  # the prescription's own history must not surface
        session=older, performed_exercise=slot.exercise,
        set_number=1, weight="99.00", reps=1,
    )

    body = client.get(f"/api/training/days/{slot.day_id}/").json()
    slot_body = body["slots"][0]
    assert slot_body["exercise"]["name"] == slot.exercise.name
    assert slot_body["substitution"]["replacement"]["name"] == "DB Lunge"
    assert slot_body["last_performance"]["sets"][0]["reps"] == 11


def test_picker_only_counts_session_scoped_swaps_for_that_session(
    client, enabled_profile, glute_coach, session
):
    slot = ExerciseSlot.objects.get(day__week__phase__variant__program=glute_coach)
    replacement = Exercise.objects.create(
        slug="db-lunge", name="DB Lunge", primary_muscle="quads", setting="home"
    )
    client.post(
        f"/api/training/slots/{slot.pk}/substitutions/",
        {"replacement": replacement.pk, "scope": "session", "session": session.pk},
        format="json",
    )

    url = f"/api/training/slots/{slot.pk}/substitutions/"
    assert client.get(f"{url}?session={session.pk}").json()["active"] is not None
    # No session, or a different one: only program-scoped swaps are in force.
    assert client.get(url).json()["active"] is None


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
